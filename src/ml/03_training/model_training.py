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
    mean_squared_error, mean_absolute_error, r2_score
)
import joblib

import xgboost as xgb

# ── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR     = os.path.join(SCRIPT_DIR, '..')
DATA_DIR   = os.path.join(ML_DIR, '01_databases')
DATA_PATH  = os.path.join(DATA_DIR, 'dataset_preprocessed.csv')
MODEL_DIR   = os.path.join(ML_DIR, '02_models')
METRICS_PATH = os.path.join(SCRIPT_DIR, 'metriques.txt')
FIGURES_DIR  = os.path.join(ML_DIR, '04_figures')
RANDOM_STATE = 42
TEST_SIZE = 0.20
VAL_SIZE = 0.15
CV_FOLDS = 5

warnings.filterwarnings('ignore')
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
def train_classifier(model, param_grid, model_name, X_train, y_train, X_val, y_val):
    """Entraine un classifieur avec GridSearchCV."""
    logger.info(f'=== Entrainement classifieur : {model_name} ===')

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    grid = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=cv,
        scoring='f1_weighted',
        n_jobs=-1,
        verbose=0
    )

    grid.fit(X_train, y_train)
    best_model = grid.best_estimator_

    logger.info(f'Meilleurs hyperparametres [{model_name}] : {grid.best_params_}')
    logger.info(f'Meilleur score F1 (CV) : {grid.best_score_:.4f}')

    # Validation
    y_pred = best_model.predict(X_val)
    acc = accuracy_score(y_val, y_pred)
    f1 = f1_score(y_val, y_pred, average='weighted')
    logger.info(f'Accuracy (validation) : {acc:.4f}')
    logger.info(f'F1-score (validation)  : {f1:.4f}')

    return best_model, y_pred, {'accuracy': acc, 'f1_score': f1, 'best_params': grid.best_params_, 'cv_score': grid.best_score_}


def train_regressor(model, param_grid, model_name, X_train, y_train, X_val, y_val, target_name):
    """Entraine un regresseur avec GridSearchCV."""
    logger.info(f'=== Entrainement regresseur : {model_name} [{target_name}] ===')

    cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    grid = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=cv,
        scoring='neg_root_mean_squared_error',
        n_jobs=-1,
        verbose=0
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
                f.write(f'    Accuracy          : {m.get("accuracy", "N/A"):.4f}\n')
                f.write(f'    F1-score (weighted): {m.get("f1_score", "N/A"):.4f}\n')
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
                    f.write(f'      RMSE : {m.get("rmse", "N/A"):.4f}\n')
                    f.write(f'      MAE  : {m.get("mae", "N/A"):.4f}\n')
                    f.write(f'      R²   : {m.get("r2", "N/A"):.4f}\n')
                    f.write(f'      CV RMSE : {m.get("cv_rmse", "N/A"):.4f}\n')
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

    # ── Chargement ──────────────────────────────────────────────────────
    df = load_data(DATA_PATH)

    # ── Classification ──────────────────────────────────────────────────
    X_clf, y_clf, label_encoder, clf_features = prepare_classification_data(df)

    # Train/val split (pas de test separe, on garde val pour evaluation)
    X_clf_train, X_clf_val, y_clf_train, y_clf_val = train_test_split(
        X_clf, y_clf, test_size=VAL_SIZE, random_state=RANDOM_STATE, stratify=y_clf
    )

    # Standardisation
    scaler_clf = StandardScaler()
    X_clf_train_scaled = scaler_clf.fit_transform(X_clf_train)
    X_clf_val_scaled = scaler_clf.transform(X_clf_val)

    # Sauvegarder le scaler et le label encoder pour inference
    joblib.dump(scaler_clf, os.path.join(MODEL_DIR, 'scaler_classification.pkl'))
    joblib.dump(label_encoder, os.path.join(MODEL_DIR, 'label_encoder_culture.pkl'))
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
            X_clf_train_scaled, y_clf_train, X_clf_val_scaled, y_clf_val
        )
        all_metrics['RandomForest'] = rf_clf_metrics

        # Sauvegarde
        joblib.dump(rf_clf_best, os.path.join(MODEL_DIR, 'random_forest_classifier.pkl'))
        logger.info('Modele RandomForest classifier sauvegarde.')

        # Matrice de confusion
        cm_path = os.path.join(FIGURES_DIR, 'confusion_matrix_RandomForest.png')
        plot_confusion_matrix(
            y_clf_val, rf_clf_pred,
            label_encoder.classes_,
            'Matrice de confusion - Random Forest (validation)',
            cm_path
        )
    except Exception as e:
        logger.error(f'Erreur RandomForest classifier : {e}')

    # ─── XGBoost Classifier ─────────────────────────────────────────────
    xgb_clf = xgb.XGBClassifier(
        random_state=RANDOM_STATE,
        eval_metric='mlogloss',
        use_label_encoder=False
    )
    xgb_param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [3, 6],
        'learning_rate': [0.1, 0.2],
        'subsample': [0.8],
        'colsample_bytree': [0.8]
    }

    logger.info('--- XGBoost Classifier ---')
    try:
        xgb_clf_best, xgb_clf_pred, xgb_clf_metrics = train_classifier(
            xgb_clf, xgb_param_grid, 'XGBoost',
            X_clf_train_scaled, y_clf_train, X_clf_val_scaled, y_clf_val
        )
        all_metrics['XGBoost'] = xgb_clf_metrics

        # Sauvegarde
        joblib.dump(xgb_clf_best, os.path.join(MODEL_DIR, 'xgboost_classifier.pkl'))
        logger.info('Modele XGBoost classifier sauvegarde.')

        # Matrice de confusion
        cm_path = os.path.join(FIGURES_DIR, 'confusion_matrix_XGBoost.png')
        plot_confusion_matrix(
            y_clf_val, xgb_clf_pred,
            label_encoder.classes_,
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

        X_reg, y_reg = prepare_regression_data(df, target, reg_features)

        # Split
        X_reg_train, X_reg_val, y_reg_train, y_reg_val = train_test_split(
            X_reg, y_reg, test_size=VAL_SIZE, random_state=RANDOM_STATE
        )

        # Standardisation
        scaler_reg = StandardScaler()
        X_reg_train_scaled = scaler_reg.fit_transform(X_reg_train)
        X_reg_val_scaled = scaler_reg.transform(X_reg_val)

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

            # Scatter plot
            scatter_path = os.path.join(FIGURES_DIR, f'regression_{target}_RF.png')
            plot_regression_scatter(y_reg_val, rf_reg_pred, target, scatter_path)
        except Exception as e:
            logger.error(f'Erreur RandomForest regressor [{target}] : {e}')

        # ─── XGBoost Regressor ──────────────────────────────────────────
        xgb_reg = xgb.XGBRegressor(random_state=RANDOM_STATE)
        xgb_reg_param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [3, 6, 9],
            'learning_rate': [0.01, 0.1, 0.2],
            'subsample': [0.8, 1.0],
            'colsample_bytree': [0.8, 1.0]
        }

        try:
            xgb_reg_best, xgb_reg_pred, xgb_reg_metrics = train_regressor(
                xgb_reg, xgb_reg_param_grid, 'XGBoost',
                X_reg_train_scaled, y_reg_train, X_reg_val_scaled, y_reg_val,
                target
            )
            all_metrics[f'XGBoost_{target}'] = xgb_reg_metrics

            joblib.dump(xgb_reg_best, os.path.join(MODEL_DIR, f'xgboost_regressor_{target}.pkl'))
            logger.info(f'Modele XGBoost regressor [{target}] sauvegarde.')

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
        print(f'  RandomForest Classifier - Acc: {m["accuracy"]:.4f}, F1: {m["f1_score"]:.4f}')
    if 'XGBoost' in all_metrics:
        m = all_metrics['XGBoost']
        print(f'  XGBoost Classifier      - Acc: {m["accuracy"]:.4f}, F1: {m["f1_score"]:.4f}')

    for target in regression_targets:
        for model_name in ['RandomForest', 'XGBoost']:
            key = f'{model_name}_{target}'
            if key in all_metrics:
                m = all_metrics[key]
                print(f'  {model_name} Regressor [{target}] - RMSE: {m["rmse"]:.2f}, R²: {m["r2"]:.4f}')

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
