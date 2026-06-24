#!/usr/bin/env python3
"""
model_training.py
=================
Pipeline d'entraînement pour le robot agricole.

1. Charge le dataset preprocesse (dataset_preprocessed.csv)
2. Entraîne des classifieurs (Random Forest, XGBoost) pour prédire la culture recommandée
3. Entraîne des régresseurs (Random Forest, XGBoost) pour estimer N, P, K à partir de pH, température, humidité
4. Optimise les hyperparamètres avec GridSearchCV
5. Sauvegarde les modèles (joblib) dans src/ml/02_models/
6. Calcule et affiche les métriques (accuracy, F1, matrice de confusion, RMSE, R²)
7. Sauvegarde les métriques dans src/ml/03_training/metriques.txt
8. Génère la matrice de confusion en PNG dans src/ml/04_figures/

Usage :
    python model_training.py
"""

import os
import sys
import json
import warnings
import logging
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold, KFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix, classification_report,
    mean_squared_error, mean_absolute_error, r2_score,
    precision_recall_fscore_support
)
import joblib

import xgboost as xgb

# ── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR     = os.path.join(SCRIPT_DIR, '..')
DATA_DIR   = os.path.join(ML_DIR, '01_databases')
DATA_PATH  = os.path.join(DATA_DIR, 'dataset_preprocessed.csv')
MODEL_DIR   = os.path.join(ML_DIR, '02_models')
SPLITS_DIR  = os.path.join(SCRIPT_DIR, 'splits')
METRICS_PATH = os.path.join(SCRIPT_DIR, 'metriques.txt')
FIGURES_DIR  = os.path.join(ML_DIR, '04_figures')
RANDOM_STATE = 42
CV_FOLDS = 5

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
warnings.filterwarnings('ignore', category=FutureWarning, module='seaborn')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BEST_DIR     = os.path.join(MODEL_DIR, 'best')
os.makedirs(BEST_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)


# ── 1. Chargement ──────────────────────────────────────────────────────────
def load_data(path):
    """Charge le dataset preprocesse."""
    logger.info(f'Chargement du dataset : {path}')
    if not os.path.exists(path):
        logger.error(f'Fichier introuvable : {path}')
        sys.exit(1)

    df = pd.read_csv(path)
    logger.info(f'Dataset charge : {df.shape[0]} lignes, {df.shape[1]} colonnes')
    logger.info(f'Colonnes : {list(df.columns)}')
    logger.info(f'Valeurs manquantes :\n{df.isnull().sum()[df.isnull().sum() > 0].to_dict() or "Aucune"}')
    return df


def load_splits(splits_dir=SPLITS_DIR):
    """
    Charge les splits pre-calcules (train/val/test) par l'EDA.
    Ces splits sont creates par eda_preprocessing.py avec stratify.
    Evite de re-partitionner et garantit que le test set n'est jamais vu
    pendant l'entrainement ou la selection d'hyperparametres.
    """
    logger.info(f'Chargement des splits depuis : {splits_dir}')

    required = ['X_train.csv', 'X_val.csv', 'X_test.csv', 'y_train.csv', 'y_val.csv', 'y_test.csv']
    for fname in required:
        fpath = os.path.join(splits_dir, fname)
        if not os.path.exists(fpath):
            logger.error(f'Split introuvable : {fpath}')
            logger.info('Lancez d\'abord eda_preprocessing.py pour generer les splits.')
            sys.exit(1)

    X_train = pd.read_csv(os.path.join(splits_dir, 'X_train.csv'))
    X_val   = pd.read_csv(os.path.join(splits_dir, 'X_val.csv'))
    X_test  = pd.read_csv(os.path.join(splits_dir, 'X_test.csv'))
    y_train = pd.read_csv(os.path.join(splits_dir, 'y_train.csv'))['culture']
    y_val   = pd.read_csv(os.path.join(splits_dir, 'y_val.csv'))['culture']
    y_test  = pd.read_csv(os.path.join(splits_dir, 'y_test.csv'))['culture']

    logger.info(f'Splits charges — train: {len(X_train)}, val: {len(X_val)}, test: {len(X_test)}')
    return X_train, X_val, X_test, y_train, y_val, y_test


# ── 2. Preparation des donnees ─────────────────────────────────────────────
def prepare_classification_data(df):
    """
    Prepare les donnees pour la classification multi-classe (culture).
    Retourne X_clf, y_clf, label_encoder, feature_names.
    """
    logger.info('Preparation des donnees de classification...')

    # La cible est 'culture' (nom de la colonne)
    target_col = 'culture'

    if target_col not in df.columns:
        logger.error(f"Colonne cible '{target_col}' introuvable dans le dataset.")
        logger.info(f"Colonnes disponibles : {list(df.columns)}")
        sys.exit(1)

    # Liste des colonnes a exclure (cible et autres colonnes non numeriques)
    exclude_cols = [target_col]
    # Colonnes possibles non predictives
    for col in ['id', 'index', 'Unnamed: 0', 'echantillon_id', 'sample_id']:
        if col in df.columns:
            exclude_cols.append(col)

    # Caracteristiques : toutes les colonnes numeriques sauf la cible
    feature_cols = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]

    if len(feature_cols) == 0:
        logger.error('Aucune caracteristique numerique trouvee pour la classification.')
        sys.exit(1)

    logger.info(f'Caracteristiques de classification ({len(feature_cols)}) : {feature_cols}')

    X = df[feature_cols].copy()
    y_raw = df[target_col].values

    # Encodage des labels
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    n_classes = len(le.classes_)
    logger.info(f'Nombre de classes : {n_classes}')
    logger.info(f'Cultures : {list(le.classes_)}')

    # Distribution des classes
    class_counts = pd.Series(y_raw).value_counts()
    logger.info(f'Distribution des classes :\n{class_counts.to_string()}')

    return X, y, le, feature_cols


def prepare_regression_data(df, target_col, feature_cols):
    """
    Prepare les donnees de regression pour estimer N, P ou K.
    Utilise pH, temperature, humidite comme predicteurs.
    """
    logger.info(f'Preparation des donnees de regression pour {target_col}...')

    # Verifier que les colonnes existent
    for col in feature_cols + [target_col]:
        if col not in df.columns:
            logger.error(f"Colonne '{col}' introuvable dans le dataset.")
            sys.exit(1)

    X = df[feature_cols].copy()
    y = df[target_col].values

    # Supprimer les lignes avec NaN dans la cible
    mask = ~np.isnan(y)
    X = X[mask]
    y = y[mask]

    logger.info(f'Regression [{target_col}] : {X.shape[0]} echantillons, {len(feature_cols)} caracteristiques')

    return X, y


# ── 3. Entrainement avec GridSearchCV ──────────────────────────────────────
def train_classifier(model, param_grid, model_name, X_train, y_train, X_val, y_val, cv_n_jobs=-1):
    """Entraine un classifieur avec GridSearchCV."""
    logger.info(f'=== Entrainement classifieur : {model_name} ===')

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    grid = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=cv,
        scoring='f1_weighted',
        n_jobs=cv_n_jobs,
        verbose=0,
    )

    grid.fit(X_train, y_train)
    best_model = grid.best_estimator_

    logger.info(f'Meilleurs hyperparametres [{model_name}] : {grid.best_params_}')
    logger.info(f'Meilleur score F1 (CV) : {grid.best_score_:.4f}')

    y_pred = best_model.predict(X_val)
    acc = accuracy_score(y_val, y_pred)
    f1_w = f1_score(y_val, y_pred, average='weighted')
    f1_m = f1_score(y_val, y_pred, average='macro')
    prec, rec, f1_per, supp = precision_recall_fscore_support(y_val, y_pred, average=None, zero_division=0)
    logger.info(f'Accuracy (validation) : {acc:.4f}')
    logger.info(f'F1-weight (validation): {f1_w:.4f}')
    logger.info(f'F1-macro  (validation): {f1_m:.4f}')

    return best_model, y_pred, {
        'accuracy': acc,
        'f1_score': f1_w,
        'f1_macro': f1_m,
        'precision_per_class': prec.tolist(),
        'recall_per_class': rec.tolist(),
        'f1_per_class': f1_per.tolist(),
        'best_params': grid.best_params_,
        'cv_score': grid.best_score_,
    }


def evaluate_on_test(model, scaler, le, X_test, y_test, task='classification', target_name=None):
    """
    Evaluation finale sur le test set (jamais vu pendant l'entrainement).
    Retourne un dict de metriques.
    """
    num_cols = X_test.select_dtypes(include=[np.number]).columns
    X_test_scaled = scaler.transform(X_test[num_cols])

    if task == 'classification':
        y_pred = model.predict(X_test_scaled)
        acc = accuracy_score(y_test, y_pred)
        f1_w = f1_score(y_test, y_pred, average='weighted')
        f1_m = f1_score(y_test, y_pred, average='macro')
        report = classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0)
        logger.info(f'=== Evaluation TEST [{target_name or "clf"}] ===')
        logger.info(f'Accuracy  : {acc:.4f}')
        logger.info(f'F1-weight : {f1_w:.4f}')
        logger.info(f'F1-macro  : {f1_m:.4f}')
        logger.info(f'\n{report}')
        return {
            'test_accuracy': acc, 'test_f1_weighted': f1_w, 'test_f1_macro': f1_m,
            'test_classification_report': report,
        }
    else:
        y_pred = model.predict(X_test_scaled)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        logger.info(f'=== Evaluation TEST [{target_name}] ===')
        logger.info(f'RMSE : {rmse:.4f}  MAE : {mae:.4f}  R² : {r2:.4f}')
        return {'test_rmse': rmse, 'test_mae': mae, 'test_r2': r2}


def train_regressor(model, param_grid, model_name, X_train, y_train, X_val, y_val, target_name, cv_n_jobs=-1):
    """Entraine un regresseur avec GridSearchCV."""
    logger.info(f'=== Entrainement regresseur : {model_name} [{target_name}] ===')

    cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    grid = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=cv,
        scoring='neg_root_mean_squared_error',
        n_jobs=cv_n_jobs,
        verbose=0,
    )

    grid.fit(X_train, y_train)
    best_model = grid.best_estimator_

    logger.info(f'Meilleurs hyperparametres [{model_name} - {target_name}] : {grid.best_params_}')
    logger.info(f'Meilleur RMSE (CV) : {-grid.best_score_:.4f}')

    # Validation
    y_pred = best_model.predict(X_val)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    logger.info(f'RMSE (validation) : {rmse:.4f}')
    logger.info(f'MAE  (validation) : {mae:.4f}')
    logger.info(f'R²   (validation) : {r2:.4f}')

    return best_model, y_pred, {'rmse': rmse, 'mae': mae, 'r2': r2, 'best_params': grid.best_params_, 'cv_rmse': -grid.best_score_}


# ── 4. Visualisation ───────────────────────────────────────────────────────
def plot_confusion_matrix(y_true, y_pred, class_names, title, save_path):
    """Genere et sauvegarde la matrice de confusion."""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(14, 12))
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='Blues',
        xticklabels=class_names, yticklabels=class_names,
        cbar=True, square=True
    )
    plt.title(title, fontsize=16, fontweight='bold')
    plt.xlabel('Prediction', fontsize=13)
    plt.ylabel('Reel', fontsize=13)
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f'Matrice de confusion sauvegardee : {save_path}')


def plot_regression_scatter(y_true, y_pred, target_name, save_path):
    """Nuage de points valeurs reelles vs predites pour la regression."""
    plt.figure(figsize=(8, 6))
    plt.scatter(y_true, y_pred, alpha=0.5, edgecolors='k', linewidth=0.5)
    plt.plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
    plt.xlabel(f'{target_name} reel', fontsize=12)
    plt.ylabel(f'{target_name} predit', fontsize=12)
    plt.title(f'Regression {target_name} : Reel vs Predit', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f'Nuage de points regression sauvegarde : {save_path}')


# ── 5. Sauvegarde des metriques ────────────────────────────────────────────
def save_metrics(all_metrics, path):
    """Sauvegarde toutes les metriques dans un fichier texte."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write('=' * 65 + '\n')
        f.write('  METRIQUES DES MODELES - Robot Agricole\n')
        f.write(f'  Date : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write('=' * 65 + '\n\n')

        # Classification
        f.write('─' * 65 + '\n')
        f.write('  CLASSIFICATION - Prediction de la culture recommandee\n')
        f.write('─' * 65 + '\n\n')
        for model_name in ['RandomForest', 'XGBoost']:
            if model_name in all_metrics:
                m = all_metrics[model_name]
                f.write(f'  [{model_name}]\n')
                f.write(f'    Accuracy           : {m.get("accuracy", "N/A"):.4f}\n')
                f.write(f'    F1-weight (val)    : {m.get("f1_score", "N/A"):.4f}\n')
                f.write(f'    F1-macro  (val)    : {m.get("f1_macro", "N/A"):.4f}\n')
                f.write(f'    Accuracy  (TEST)   : {m.get("test_accuracy", "N/A"):.4f}\n')
                f.write(f'    F1-weight (TEST)   : {m.get("test_f1_weighted", "N/A"):.4f}\n')
                f.write(f'    F1-macro  (TEST)   : {m.get("test_f1_macro", "N/A"):.4f}\n')
                f.write(f'    CV F1-score (moyen): {m.get("cv_score", "N/A"):.4f}\n')
                f.write(f'    Meilleurs params   : {m.get("best_params", "N/A")}\n')
                f.write('\n')

        # Regression
        f.write('─' * 65 + '\n')
        f.write('  REGRESSION - Estimation N, P, K\n')
        f.write('─' * 65 + '\n\n')
        for target in ['N', 'P', 'K']:
            f.write(f'  Cible : {target}\n')
            for model_name in ['RandomForest', 'XGBoost']:
                key = f'{model_name}_{target}'
                if key in all_metrics:
                    m = all_metrics[key]
                    f.write(f'    [{model_name}]\n')
                    f.write(f'      RMSE (val)  : {m.get("rmse", "N/A"):.4f}\n')
                    f.write(f'      MAE  (val)  : {m.get("mae", "N/A"):.4f}\n')
                    f.write(f'      R²   (val)  : {m.get("r2", "N/A"):.4f}\n')
                    if 'test_rmse' in m:
                        f.write(f'      RMSE (TEST) : {m.get("test_rmse", "N/A"):.4f}\n')
                        f.write(f'      MAE  (TEST) : {m.get("test_mae", "N/A"):.4f}\n')
                        f.write(f'      R²   (TEST) : {m.get("test_r2", "N/A"):.4f}\n')
                    f.write(f'      CV RMSE     : {m.get("cv_rmse", "N/A"):.4f}\n')
                    f.write(f'      Meilleurs params : {m.get("best_params", "N/A")}\n')
            f.write('\n')

        f.write('=' * 65 + '\n')
        f.write('  FIN DU RAPPORT\n')
        f.write('=' * 65 + '\n')

    logger.info(f'Metriques sauvegardees : {path}')


# ── 6. Pipeline principal ──────────────────────────────────────────────────
def main():
    logger.info('=' * 60)
    logger.info('DEBUT DE L\'ENTRAINEMENT DES MODELES')
    logger.info('=' * 60)

    # ── Chargement du dataset complet (features brutes, non normalisees) ──
    df = load_data(DATA_PATH)

    # ── Chargement des splits pre-calcules par eda_preprocessing.py ───────
    #   Garantit que le test set n'est jamais vu pendant l'entrainement.
    X_clf_train, X_clf_val, X_clf_test, y_clf_train, y_clf_val, y_clf_test = load_splits()

    # S'assurer que les colonnes sont numeriques uniquement
    numeric_cols = X_clf_train.select_dtypes(include=[np.number]).columns.tolist()
    X_clf_train = X_clf_train[numeric_cols]
    X_clf_val   = X_clf_val[numeric_cols]
    X_clf_test  = X_clf_test[numeric_cols]

    # Label encoder
    all_labels = pd.concat([y_clf_train, y_clf_val, y_clf_test]).unique()
    le = LabelEncoder()
    le.fit(sorted(all_labels))
    y_clf_train_enc = le.transform(y_clf_train)
    y_clf_val_enc   = le.transform(y_clf_val)
    y_clf_test_enc  = le.transform(y_clf_test)

    # Standardisation APRES le split (pas de data leakage)
    scaler_clf = StandardScaler()
    X_clf_train_scaled = scaler_clf.fit_transform(X_clf_train)
    X_clf_val_scaled   = scaler_clf.transform(X_clf_val)
    X_clf_test_scaled  = scaler_clf.transform(X_clf_test)

    joblib.dump(scaler_clf, os.path.join(MODEL_DIR, 'scaler_classification.pkl'))
    joblib.dump(le, os.path.join(MODEL_DIR, 'label_encoder_culture.pkl'))
    logger.info('Scaler et LabelEncoder de classification sauvegardes.')

    all_metrics = {}

    # ─── Random Forest Classifier ───────────────────────────────────────
    rf_clf = RandomForestClassifier(random_state=RANDOM_STATE)
    rf_param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['sqrt', 'log2']
    }
    # Grid plus leger pour ne pas exploser le temps de calcul
    rf_param_grid_light = {
        'n_estimators': [100, 200],
        'max_depth': [None, 20],
        'min_samples_split': [2, 5],
        'min_samples_leaf': [1, 2]
    }

    logger.info('--- Random Forest Classifier ---')
    try:
        rf_clf_best, rf_clf_pred, rf_clf_metrics = train_classifier(
            rf_clf, rf_param_grid_light, 'RandomForest',
            X_clf_train_scaled, y_clf_train_enc, X_clf_val_scaled, y_clf_val_enc
        )
        all_metrics['RandomForest'] = rf_clf_metrics

        # Sauvegarde
        joblib.dump(rf_clf_best, os.path.join(MODEL_DIR, 'random_forest_classifier.pkl'))
        joblib.dump(scaler_clf, os.path.join(BEST_DIR, 'scaler_classification.pkl'))
        joblib.dump(le, os.path.join(BEST_DIR, 'label_encoder_culture.pkl'))
        logger.info('Modele RandomForest classifier sauvegarde.')

        # Evaluation test set
        test_metrics = evaluate_on_test(rf_clf_best, scaler_clf, le, X_clf_test, y_clf_test_enc,
                                         task='classification', target_name='RandomForest')
        all_metrics['RandomForest'].update(test_metrics)

        # Matrice de confusion
        cm_path = os.path.join(FIGURES_DIR, 'confusion_matrix_RandomForest.png')
        plot_confusion_matrix(
            y_clf_val_enc, rf_clf_pred,
            le.classes_,
            'Matrice de confusion - Random Forest (validation)',
            cm_path
        )
    except Exception as e:
        logger.error(f'Erreur RandomForest classifier : {e}')

    # ─── XGBoost Classifier ─────────────────────────────────────────────
    xgb_clf = xgb.XGBClassifier(
        random_state=RANDOM_STATE,
        eval_metric='mlogloss',
        enable_categorical=False,
        n_jobs=1,
    )
    xgb_param_grid = {
        'n_estimators': [100],
        'max_depth': [6],
        'learning_rate': [0.1],
    }
    # XGBoost GridSearchCV: use 2 parallel jobs (XGBoost uses its own thread pool)
    xgb_cv_n_jobs = 2

    logger.info('--- XGBoost Classifier ---')
    try:
        xgb_clf_best, xgb_clf_pred, xgb_clf_metrics = train_classifier(
            xgb_clf, xgb_param_grid, 'XGBoost',
            X_clf_train_scaled, y_clf_train_enc, X_clf_val_scaled, y_clf_val_enc,
            cv_n_jobs=xgb_cv_n_jobs,
        )
        all_metrics['XGBoost'] = xgb_clf_metrics

        # Sauvegarde
        joblib.dump(xgb_clf_best, os.path.join(MODEL_DIR, 'xgboost_classifier.pkl'))
        logger.info('Modele XGBoost classifier sauvegarde.')

        # Evaluation test set
        test_metrics = evaluate_on_test(xgb_clf_best, scaler_clf, le, X_clf_test, y_clf_test_enc,
                                         task='classification', target_name='XGBoost')
        all_metrics['XGBoost'].update(test_metrics)

        # Matrice de confusion
        cm_path = os.path.join(FIGURES_DIR, 'confusion_matrix_XGBoost.png')
        plot_confusion_matrix(
            y_clf_val_enc, xgb_clf_pred,
            le.classes_,
            'Matrice de confusion - XGBoost (validation)',
            cm_path
        )
    except Exception as e:
        logger.error(f'Erreur XGBoost classifier : {e}')

    # ── Regression N, P, K ──────────────────────────────────────────────
    reg_features = ['pH', 'temperature', 'humidite']
    regression_targets = ['N', 'P', 'K']

    for target in regression_targets:
        logger.info(f'=== Regression : {target} ===')

        X_reg = df[reg_features].copy()
        y_reg = df[target].values

        mask = ~np.isnan(y_reg)
        X_reg = X_reg[mask]
        y_reg = y_reg[mask]

        # Split train/val/test (70/15/15) stratifie impossible pour regression
        X_reg_train, X_reg_temp, y_reg_train, y_reg_temp = train_test_split(
            X_reg, y_reg, test_size=0.30, random_state=RANDOM_STATE
        )
        X_reg_val, X_reg_test, y_reg_val, y_reg_test = train_test_split(
            X_reg_temp, y_reg_temp, test_size=0.50, random_state=RANDOM_STATE
        )

        scaler_reg = StandardScaler()
        X_reg_train_scaled = scaler_reg.fit_transform(X_reg_train)
        X_reg_val_scaled   = scaler_reg.transform(X_reg_val)
        X_reg_test_scaled  = scaler_reg.transform(X_reg_test)

        # Sauvegarder le scaler pour ce target
        joblib.dump(scaler_reg, os.path.join(MODEL_DIR, f'scaler_regression_{target}.pkl'))

        # ─── Random Forest Regressor ────────────────────────────────────
        rf_reg = RandomForestRegressor(random_state=RANDOM_STATE)
        rf_reg_param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [None, 15, 30],
            'min_samples_split': [2, 5],
            'min_samples_leaf': [1, 2]
        }

        try:
            rf_reg_best, rf_reg_pred, rf_reg_metrics = train_regressor(
                rf_reg, rf_reg_param_grid, 'RandomForest',
                X_reg_train_scaled, y_reg_train, X_reg_val_scaled, y_reg_val,
                target
            )
            all_metrics[f'RandomForest_{target}'] = rf_reg_metrics

            joblib.dump(rf_reg_best, os.path.join(MODEL_DIR, f'random_forest_regressor_{target}.pkl'))
            logger.info(f'Modele RandomForest regressor [{target}] sauvegarde.')

            # Evaluation test set
            if X_reg_test_scaled is not None:
                test_m = evaluate_on_test(rf_reg_best, scaler_reg, None, X_reg_test, y_reg_test,
                                          task='regression', target_name=f'RF_{target}')
                rf_reg_metrics.update(test_m)

            # Scatter plot
            scatter_path = os.path.join(FIGURES_DIR, f'regression_{target}_RF.png')
            plot_regression_scatter(y_reg_val, rf_reg_pred, target, scatter_path)
        except Exception as e:
            logger.error(f'Erreur RandomForest regressor [{target}] : {e}')

        # ─── XGBoost Regressor ──────────────────────────────────────────
        xgb_reg = xgb.XGBRegressor(random_state=RANDOM_STATE, n_jobs=1)
        xgb_reg_param_grid = {
            'n_estimators': [150],
            'max_depth': [4, 6],
            'learning_rate': [0.1],
        }
        xgb_cv_n_jobs_reg = 2

        try:
            xgb_reg_best, xgb_reg_pred, xgb_reg_metrics = train_regressor(
                xgb_reg, xgb_reg_param_grid, 'XGBoost',
                X_reg_train_scaled, y_reg_train, X_reg_val_scaled, y_reg_val,
                target, cv_n_jobs=xgb_cv_n_jobs_reg,
            )
            all_metrics[f'XGBoost_{target}'] = xgb_reg_metrics

            joblib.dump(xgb_reg_best, os.path.join(MODEL_DIR, f'xgboost_regressor_{target}.pkl'))
            logger.info(f'Modele XGBoost regressor [{target}] sauvegarde.')

            # Evaluation test set
            if X_reg_test_scaled is not None:
                test_m = evaluate_on_test(xgb_reg_best, scaler_reg, None, X_reg_test, y_reg_test,
                                          task='regression', target_name=f'XGB_{target}')
                xgb_reg_metrics.update(test_m)

            # Scatter plot
            scatter_path = os.path.join(FIGURES_DIR, f'regression_{target}_XGB.png')
            plot_regression_scatter(y_reg_val, xgb_reg_pred, target, scatter_path)
        except Exception as e:
            logger.error(f'Erreur XGBoost regressor [{target}] : {e}')

    # ── Sauvegarde des metriques ────────────────────────────────────────
    save_metrics(all_metrics, METRICS_PATH)

    # ── Affichage console ───────────────────────────────────────────────
    print('\n' + '=' * 65)
    print('  RESUME DES PERFORMANCES')
    print('=' * 65)

    if 'RandomForest' in all_metrics:
        m = all_metrics['RandomForest']
        print(f'  RandomForest Classifier')
        print(f'    Val : Acc={m["accuracy"]:.4f}, F1w={m["f1_score"]:.4f}, F1m={m["f1_macro"]:.4f}')
        if 'test_accuracy' in m:
            print(f'    Test: Acc={m["test_accuracy"]:.4f}, F1w={m["test_f1_weighted"]:.4f}, F1m={m["test_f1_macro"]:.4f}')
    if 'XGBoost' in all_metrics:
        m = all_metrics['XGBoost']
        print(f'  XGBoost Classifier')
        print(f'    Val : Acc={m["accuracy"]:.4f}, F1w={m["f1_score"]:.4f}, F1m={m["f1_macro"]:.4f}')
        if 'test_accuracy' in m:
            print(f'    Test: Acc={m["test_accuracy"]:.4f}, F1w={m["test_f1_weighted"]:.4f}, F1m={m["test_f1_macro"]:.4f}')

    for target in regression_targets:
        for model_name in ['RandomForest', 'XGBoost']:
            key = f'{model_name}_{target}'
            if key in all_metrics:
                m = all_metrics[key]
                test_info = ''
                if 'test_r2' in m:
                    test_info = f', Test R²={m["test_r2"]:.4f}'
                print(f'  {model_name} Regressor [{target}] - Val R²: {m["r2"]:.4f}{test_info}')

    print('=' * 65)
    print(f'  Modeles sauvegardes dans : {MODEL_DIR}')
    print(f'  Metriques sauvegardees   : {METRICS_PATH}')
    print(f'  Figures sauvegardees     : {FIGURES_DIR}')
    print('=' * 65)

    # ── Copie automatique du meilleur modele dans best/ ──────────────
    import shutil
    logger.info('--- Copie des meilleurs modeles dans best/ ---')

    # Classifieur : comparer F1-score
    best_clf_name = None
    best_clf_f1 = -1
    for model_name in ['RandomForest', 'XGBoost']:
        if model_name in all_metrics:
            f1 = all_metrics[model_name]['f1_score']
            if f1 > best_clf_f1:
                best_clf_f1 = f1
                best_clf_name = model_name

    clf_map = {
        'RandomForest': ('random_forest_classifier.pkl', 'classifier_rf.pkl'),
        'XGBoost': ('xgboost_classifier.pkl', 'classifier_xgb.pkl'),
    }
    if best_clf_name and best_clf_name in clf_map:
        src_name, dst_name = clf_map[best_clf_name]
        src = os.path.join(MODEL_DIR, src_name)
        dst = os.path.join(BEST_DIR, 'classifier.pkl')
        if os.path.exists(src):
            shutil.copy2(src, dst)
            logger.info(f'  ✅ Classifieur: {best_clf_name} (F1={best_clf_f1:.4f}) → best/classifier.pkl')

        # Copier aussi dans best/ avec le nom du modele pour reference
        shutil.copy2(src, os.path.join(BEST_DIR, dst_name))
        logger.info(f'     Backup: {dst_name}')

    # Regresseurs N, P, K : comparer R²
    for target in ['N', 'P', 'K']:
        best_reg_name = None
        best_reg_r2 = -999
        for model_name in ['RandomForest', 'XGBoost']:
            key = f'{model_name}_{target}'
            if key in all_metrics:
                r2 = all_metrics[key]['r2']
                if r2 > best_reg_r2:
                    best_reg_r2 = r2
                    best_reg_name = model_name

        reg_map = {
            'RandomForest': f'random_forest_regressor_{target}.pkl',
            'XGBoost': f'xgboost_regressor_{target}.pkl',
        }
        if best_reg_name and best_reg_name in reg_map:
            src_name = reg_map[best_reg_name]
            src = os.path.join(MODEL_DIR, src_name)
            dst = os.path.join(BEST_DIR, f'regressor_{target}.pkl')
            if os.path.exists(src):
                shutil.copy2(src, dst)
                logger.info(f'  ✅ Regresseur {target}: {best_reg_name} (R²={best_reg_r2:.4f}) → best/regressor_{target}.pkl')

    # Copier aussi les scalers et label_encoder dans best/
    for fname in ['scaler_classification.pkl', 'label_encoder_culture.pkl',
                  'scaler_regression_N.pkl', 'scaler_regression_P.pkl', 'scaler_regression_K.pkl']:
        src = os.path.join(MODEL_DIR, fname)
        dst = os.path.join(BEST_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    # Copier les metriques
    shutil.copy2(METRICS_PATH, os.path.join(BEST_DIR, 'metriques.txt'))
    logger.info(f'  📊 Metriques copiees dans best/')
    logger.info(f'--- Copie terminee ---')

    logger.info('ENTRAINEMENT TERMINE AVEC SUCCES.')


if __name__ == '__main__':
    main()
