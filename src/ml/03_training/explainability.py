#!/usr/bin/env python3
"""
explainability.py — Module d'explicabilite pour le robot agricole.

Ce module fournit:
  1. Chargement des modeles entrainés (Random Forest, XGBoost)
  2. Calcul et visualisation SHAP (summary, dependence plots)
  3. Explication locale via LIME
  4. Arbre de decision interpretable (profondeur 3-4)
  5. Contre-factuels : quel changement minimal modifierait la culture recommandee ?
  6. Fonction explain_prediction() pour l'integration robot

Utilisation:
    python explainability.py          # Execute le pipeline complet
    from explainability import ...    # Import comme module
"""

import os
import json
import pickle
import warnings
import itertools
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from copy import deepcopy
from typing import Dict, List, Tuple, Optional, Any

# ML
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier, plot_tree, export_text
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
warnings.filterwarnings('ignore', category=FutureWarning, module='seaborn')
warnings.filterwarnings('ignore', category=FutureWarning, module='shap')

# ──────────────────────────────────────────────
# Chemins
# ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR     = os.path.join(SCRIPT_DIR, '..')
BASE_DIR   = os.path.join(ML_DIR, '01_databases')
MODELES_DIR = os.path.join(ML_DIR, "02_models")
FIGURES_DIR = os.path.join(ML_DIR, "04_figures")
BASE_JSON   = os.path.join(BASE_DIR, "base_reference_agricole.json")

RF_PATH = os.path.join(MODELES_DIR, "random_forest.pkl")
XGB_PATH = os.path.join(MODELES_DIR, "xgboost.pkl")
LABEL_ENCODER_PATH = os.path.join(MODELES_DIR, "label_encoder.pkl")
SCALER_PATH = os.path.join(MODELES_DIR, "scaler.pkl")
TRAIN_DATA_PATH = os.path.join(MODELES_DIR, "training_data.npz")
DECISION_TREE_PATH = os.path.join(MODELES_DIR, "decision_tree_depth4.pkl")

SHAP_SUMMARY_PATH = os.path.join(FIGURES_DIR, "shap_summary.png")
SHAP_DEPENDENCE_DIR = os.path.join(FIGURES_DIR, "shap_dependence")
DECISION_TREE_PLOT_PATH = os.path.join(FIGURES_DIR, "decision_tree.png")

# Features utilisees par les modeles de recommandation culture
FEATURES_CULTURE = ["pH", "temperature", "humidite", "N", "P", "K"]

# Ordre alphabetique des cultures (pour le label encoder)
CULTURES_ORDERED = [
    "Arachide", "Banane plantain", "Cacao", "Cafe", "Coton",
    "Fonio", "Haricot", "Igname", "Mais", "Manioc",
    "Mil", "Niebe", "Patate douce", "Riz", "Sesame", "Sorgho"
]


# ════════════════════════════════════════════════
# 1. GENERATION DES DONNEES D'ENTRAINEMENT
# ════════════════════════════════════════════════

def load_reference_base(json_path: str = BASE_JSON) -> dict:
    """Charge la base de reference agricole."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_training_data(
    reference: dict,
    n_samples_per_crop: int = 500,
    random_state: int = 42
) -> Tuple[pd.DataFrame, np.ndarray, LabelEncoder]:
    """
    Genere un dataset synthetique a partir des plages de tolerance
    de la base de reference. Pour chaque culture, on echantillonne
    uniformement dans [min, max] pour chaque variable.

    Retourne:
        X_df, y_encoded, label_encoder
    """
    rng = np.random.RandomState(random_state)
    rows = []
    labels = []

    cultures = reference["cultures"]

    for culture_entry in cultures:
        name = culture_entry["culture"]
        sol = culture_entry["sol"]

        # Extraire les plages
        ph_range = sol.get("pH", {})
        temp_range = sol.get("temperature", {})
        hum_range = sol.get("humidite", {})

        # Valeurs par defaut si non renseignees
        ph_min = ph_range.get("min", 5.0)
        ph_max = ph_range.get("max", 7.5)
        ph_opt = ph_range.get("optimal", (ph_min + ph_max) / 2.0)

        temp_min = temp_range.get("min", 20)
        temp_max = temp_range.get("max", 35)

        hum_min = hum_range.get("min", 30.0)
        hum_max = hum_range.get("max", 85.0)
        hum_opt = hum_range.get("optimal", (hum_min + hum_max) / 2.0)

        # P2O5 -> P, K2O -> K
        n_range = sol.get("N", {})
        p2o5_range = sol.get("P2O5", {})
        k2o_range = sol.get("K2O", {})

        n_min = n_range.get("min", 10)
        n_max = n_range.get("max", 200)
        n_opt = n_range.get("optimal", (n_min + n_max) / 2.0)

        p2o5_min = p2o5_range.get("min", 10)
        p2o5_max = p2o5_range.get("max", 100)
        p_min = p2o5_min / 2.29
        p_max = p2o5_max / 2.29

        k2o_min = k2o_range.get("min", 10)
        k2o_max = k2o_range.get("max", 200)
        k_min = k2o_min / 1.205
        k_max = k2o_max / 1.205

        # Echantillonnage intelligent : concentre autour de l'optimal
        # Utiliser une distribution beta pour concentrer pres de l'optimum
        for _ in range(n_samples_per_crop):
            # pH: distribution centree sur l'optimal
            if ph_opt:
                ph = _sample_near_optimal(ph_min, ph_max, ph_opt, rng)
            else:
                ph = rng.uniform(ph_min, ph_max)

            # Temperature
            temp = rng.uniform(temp_min, temp_max)

            # Humidite: distribution centree sur l'optimal si disponible
            if hum_opt and hum_min is not None and hum_max is not None:
                hum = _sample_near_optimal(hum_min, hum_max, hum_opt, rng)
            else:
                hum = rng.uniform(hum_min, hum_max) if hum_min is not None and hum_max is not None else 50.0

            # NPK
            n_val = _sample_near_optimal(n_min, n_max, n_opt, rng)
            p_val = rng.uniform(p_min, p_max)
            k_val = rng.uniform(k_min, k_max)

            rows.append({
                "pH": round(ph, 2),
                "temperature": round(temp, 1),
                "humidite": round(hum, 1),
                "N": round(n_val, 1),
                "P": round(p_val, 1),
                "K": round(k_val, 1),
                "culture": name
            })

    df = pd.DataFrame(rows)
    le = LabelEncoder()
    le.fit(CULTURES_ORDERED)
    y_encoded = le.transform(df["culture"].values)

    X_df = df[FEATURES_CULTURE]

    return X_df, y_encoded, le, df


def _sample_near_optimal(vmin, vmax, optimal, rng, concentration=3.0):
    """
    Echantillonne une valeur selon une distribution beta centree
    sur l'optimal. concentration > 1 resserre autour de l'optimum.
    """
    if vmax <= vmin:
        return vmin
    # Normaliser l'optimal en [0, 1]
    t = (optimal - vmin) / (vmax - vmin)
    t = np.clip(t, 0.05, 0.95)
    # Parametres beta : moyenne = t, variance controlee par concentration
    alpha = concentration * t
    beta = concentration * (1 - t)
    sample = rng.beta(alpha, beta)
    return vmin + sample * (vmax - vmin)


# ════════════════════════════════════════════════
# 2. CHARGEMENT / ENTRAINEMENT DES MODELES
# ════════════════════════════════════════════════

def ensure_dirs():
    """Cree les repertoires necessaires s'ils n'existent pas."""
    for d in [MODELES_DIR, FIGURES_DIR, SHAP_DEPENDENCE_DIR]:
        os.makedirs(d, exist_ok=True)


def load_or_train_models(
    force_retrain: bool = False
) -> Tuple[Any, Any, LabelEncoder, Optional[Any], pd.DataFrame, np.ndarray]:
    """
    Charge les modeles depuis le disque ou les entraine si absents.

    Retourne:
        rf_model, xgb_model, label_encoder, scaler, X_df, y
    """
    ensure_dirs()

    # Generer les donnees d'entrainement
    reference = load_reference_base()
    X_df, y, le, full_df = generate_training_data(reference)
    print(f"[INFO] Dataset genere: {X_df.shape[0]} echantillons, {len(le.classes_)} cultures")

    # Tenter de charger les modeles existants
    rf_model = None
    xgb_model = None
    scaler = None

    if not force_retrain:
        if os.path.exists(RF_PATH):
            with open(RF_PATH, "rb") as f:
                rf_model = pickle.load(f)
            print(f"[INFO] Random Forest charge depuis {RF_PATH}")

        if os.path.exists(XGB_PATH):
            try:
                with open(XGB_PATH, "rb") as f:
                    xgb_model = pickle.load(f)
                print(f"[INFO] XGBoost charge depuis {XGB_PATH}")
            except Exception:
                xgb_model = None

        if os.path.exists(LABEL_ENCODER_PATH):
            with open(LABEL_ENCODER_PATH, "rb") as f:
                le_loaded = pickle.load(f)
                if hasattr(le_loaded, 'classes_'):
                    le = le_loaded

    # Entrainer les modeles si necessaire
    if rf_model is None:
        print("[INFO] Entrainement du Random Forest...")
        rf_model = RandomForestClassifier(
            n_estimators=300,
            max_depth=20,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced"
        )
        rf_model.fit(X_df.values, y)
        with open(RF_PATH, "wb") as f:
            pickle.dump(rf_model, f)
        print(f"[INFO] Random Forest entraine et sauvegarde dans {RF_PATH}")

    if xgb_model is None:
        print("[INFO] Entrainement du XGBoost...")
        try:
            import xgboost as xgb
            xgb_model = xgb.XGBClassifier(
                n_estimators=300,
                max_depth=10,
                learning_rate=0.1,
                random_state=42,
                n_jobs=-1,
                eval_metric="mlogloss",
                use_label_encoder=False
            )
            xgb_model.fit(X_df.values, y)
            with open(XGB_PATH, "wb") as f:
                pickle.dump(xgb_model, f)
            print(f"[INFO] XGBoost entraine et sauvegarde dans {XGB_PATH}")
        except ImportError:
            print("[WARN] xgboost non installe. Utilisation du Random Forest uniquement.")
            xgb_model = None

    # Sauvegarder le label encoder
    with open(LABEL_ENCODER_PATH, "wb") as f:
        pickle.dump(le, f)

    # Sauvegarder les donnees d'entrainement pour SHAP/LIME
    np.savez(TRAIN_DATA_PATH, X=X_df.values, y=y)

    return rf_model, xgb_model, le, scaler, X_df, y, full_df


def select_best_model(
    rf_model, xgb_model, X_df, y
) -> Tuple[Any, str]:
    """
    Selectionne le meilleur modele de classification
    (Random Forest vs XGBoost) base sur l'accuracy.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X_df.values, y, test_size=0.2, random_state=42, stratify=y
    )

    best_model = rf_model
    best_name = "Random Forest"
    best_score = 0.0

    models_to_eval = [("Random Forest", rf_model)]
    if xgb_model is not None:
        models_to_eval.append(("XGBoost", xgb_model))

    for name, model in models_to_eval:
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"  {name} accuracy: {acc:.4f}")
        if acc > best_score:
            best_score = acc
            best_model = model
            best_name = name

    print(f"  => Meilleur modele: {best_name} (accuracy: {best_score:.4f})")
    return best_model, best_name


# ════════════════════════════════════════════════
# 3. SHAP EXPLAINER
# ════════════════════════════════════════════════

def compute_shap_explanations(
    model, X_df: pd.DataFrame, le: LabelEncoder
) -> Any:
    """
    Calcule les valeurs SHAP pour le modele donne.
    Retourne l'objet explainer SHAP.
    """
    try:
        import shap
    except ImportError:
        print("[ERROR] SHAP n'est pas installe. Installez-le avec: pip install shap")
        return None

    print("[INFO] Calcul des valeurs SHAP (peut prendre quelques secondes)...")

    # Utiliser un sous-ensemble comme background (KMean summary)
    background = shap.kmeans(X_df.values, min(50, len(X_df)))
    explainer = shap.KernelExplainer(model.predict_proba, background)

    # Echantillonner pour le calcul SHAP (200 echantillons max)
    n_samples = min(200, len(X_df))
    X_sample = X_df.values[:n_samples]
    shap_values = explainer.shap_values(X_sample, nsamples=100)

    return explainer, shap_values, X_sample


def generate_shap_summary_plot(
    shap_values, X_sample, feature_names: List[str], le: LabelEncoder, save_path: str
):
    """
    Genere et sauvegarde le SHAP summary plot (beeswarm).
    """
    try:
        import shap
    except ImportError:
        return

    print(f"[INFO] Generation du SHAP summary plot -> {save_path}")

    # Pour les modeles multi-classes, shap_values est une liste par classe
    if isinstance(shap_values, list):
        # Moyenne des valeurs absolues sur toutes les classes pour le summary global
        n_classes = len(shap_values)
        if n_classes > 1:
            # Prendre la moyenne des |SHAP| sur toutes les classes
            mean_abs_shap = np.mean([np.abs(sv) for sv in shap_values], axis=0)
            # Feature importance globale
            feature_importance = np.mean(mean_abs_shap, axis=0)
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))

            # Bar plot des importances
            sorted_idx = np.argsort(feature_importance)
            axes[0].barh(range(len(sorted_idx)), feature_importance[sorted_idx])
            axes[0].set_yticks(range(len(sorted_idx)))
            axes[0].set_yticklabels([feature_names[i] for i in sorted_idx])
            axes[0].set_xlabel("Importance SHAP moyenne (toutes classes)")
            axes[0].set_title("Importance globale des features (SHAP)")

            # Summary plot pour les 3 premieres classes
            top_classes = min(3, n_classes)
            class_names = le.classes_
            for i in range(top_classes):
                shap.summary_plot(
                    shap_values[i], X_sample,
                    feature_names=feature_names,
                    show=False, max_display=6
                )
                plt.title(f"SHAP summary - {class_names[i]}")
                plt.tight_layout()
                class_path = save_path.replace(".png", f"_{class_names[i]}.png")
                plt.savefig(class_path, dpi=150, bbox_inches='tight')
                plt.close()

            # Summary global simplifie
            axes[1].axis('off')
            axes[1].text(0.1, 0.5,
                "Summary plots par classe sauvegardes:\n" +
                "\n".join([f"  - shap_summary_{name}.png" for name in class_names[:top_classes]]),
                fontsize=11, verticalalignment='center')
            plt.tight_layout()
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
        else:
            # Binaire
            shap.summary_plot(shap_values[0], X_sample, feature_names=feature_names, show=False)
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
    else:
        shap.summary_plot(shap_values, X_sample, feature_names=feature_names, show=False)
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()

    print(f"[OK] SHAP summary plot sauvegarde: {save_path}")


def generate_shap_dependence_plots(
    shap_values, X_sample, feature_names: List[str], le: LabelEncoder
):
    """
    Genere les SHAP dependence plots pour pH, temperature, humidite.
    """
    try:
        import shap
    except ImportError:
        return

    print(f"[INFO] Generation des SHAP dependence plots -> {SHAP_DEPENDENCE_DIR}/")

    target_features = ["pH", "temperature", "humidite"]
    for feat_name in target_features:
        if feat_name not in feature_names:
            continue
        feat_idx = feature_names.index(feat_name)

        fig, axes = plt.subplots(1, min(3, le.classes_.shape[0]), figsize=(18, 5))
        if le.classes_.shape[0] == 1:
            axes = [axes]

        class_names = le.classes_[:3]  # Top 3 cultures
        top_classes = min(3, len(class_names))

        for i in range(top_classes):
            ax = axes[i]
            if isinstance(shap_values, list) and len(shap_values) > i:
                sv_class = shap_values[i][:, feat_idx]
                # Dependence plot manuel
                ax.scatter(X_sample[:, feat_idx], sv_class,
                          alpha=0.5, s=20, c='steelblue', edgecolors='none')
                # Ligne de tendance
                sort_idx = np.argsort(X_sample[:, feat_idx])
                ax.plot(X_sample[sort_idx, feat_idx],
                       np.convolve(sv_class[sort_idx], np.ones(20)/20, mode='same'),
                       color='darkred', linewidth=2)
                ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
                ax.set_xlabel(feat_name)
                ax.set_ylabel(f"SHAP value ({class_names[i]})")
                ax.set_title(f"SHAP dependence: {feat_name} -> {class_names[i]}")
                ax.grid(True, alpha=0.3)
            else:
                ax.text(0.5, 0.5, "N/A", ha='center', va='center', fontsize=14)
                ax.set_title(f"{class_names[i] if i < len(class_names) else 'Class ' + str(i)}")

        plt.tight_layout()
        dep_path = os.path.join(SHAP_DEPENDENCE_DIR, f"shap_dependence_{feat_name}.png")
        plt.savefig(dep_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  [OK] {dep_path}")


# ════════════════════════════════════════════════
# 4. LIME EXPLAINER
# ════════════════════════════════════════════════

def build_lime_explainer(
    model, X_train: np.ndarray, feature_names: List[str], le: LabelEncoder
) -> Any:
    """
    Construit un explainer LIME pour des explications locales.
    """
    try:
        from lime.lime_tabular import LimeTabularExplainer
    except ImportError:
        print("[ERROR] LIME n'est pas installe. Installez-le avec: pip install lime")
        return None

    print("[INFO] Construction du LIME explainer...")
    explainer = LimeTabularExplainer(
        X_train,
        feature_names=feature_names,
        class_names=list(le.classes_),
        mode='classification',
        discretize_continuous=True,
        random_state=42
    )
    return explainer


def explain_with_lime(
    explainer, model, instance: np.ndarray, num_features: int = 6
) -> dict:
    """
    Explique une prediction locale avec LIME.
    Retourne un dictionnaire avec explication textuelle.
    """
    exp = explainer.explain_instance(
        instance, model.predict_proba, num_features=num_features
    )

    result = {
        "method": "LIME",
        "prediction": exp.predict_label,
        "probabilities": dict(exp.predict_proba),
        "features": []
    }

    for feat, weight in exp.as_list():
        result["features"].append({
            "feature": feat,
            "weight": round(weight, 4),
            "direction": "positif" if weight > 0 else "negatif"
        })

    return result


# ════════════════════════════════════════════════
# 5. ARBRE DE DECISION INTERPRETABLE
# ════════════════════════════════════════════════

def train_and_visualize_decision_tree(
    X_df: pd.DataFrame, y: np.ndarray, le: LabelEncoder, max_depth: int = 4
) -> DecisionTreeClassifier:
    """
    Entraine un petit arbre de decision interpretable (profondeur max_depth)
    et le visualise.
    """
    print(f"[INFO] Entrainement arbre de decision (profondeur max={max_depth})...")

    dt = DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=5,
        min_samples_split=10,
        random_state=42,
        class_weight="balanced"
    )
    dt.fit(X_df.values, y)

    # Sauvegarder le modele
    with open(DECISION_TREE_PATH, "wb") as f:
        pickle.dump(dt, f)

    # Evaluation
    y_pred = dt.predict(X_df.values)
    acc = accuracy_score(y, y_pred)
    print(f"  Arbre de decision - accuracy (train): {acc:.4f}")

    # Rules textuelles
    tree_rules = export_text(dt, feature_names=list(X_df.columns))
    print("  Regles de l'arbre:")
    for line in tree_rules.split("\n"):
        print(f"    {line}")

    # Visualisation graphique
    fig, ax = plt.subplots(figsize=(20, 12))
    plot_tree(
        dt,
        feature_names=list(X_df.columns),
        class_names=list(le.classes_),
        filled=True,
        rounded=True,
        fontsize=9,
        proportion=True,
        ax=ax
    )
    plt.title(f"Arbre de decision interpretable (profondeur {max_depth})", fontsize=14)
    plt.tight_layout()
    plt.savefig(DECISION_TREE_PLOT_PATH, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"[OK] Arbre de decision sauvegarde: {DECISION_TREE_PLOT_PATH}")

    return dt


# ════════════════════════════════════════════════
# 6. CONTRE-FACTUELS
# ════════════════════════════════════════════════

def find_counterfactual(
    model, instance: np.ndarray,
    original_prediction: int,
    le: LabelEncoder,
    feature_names: List[str],
    X_train: pd.DataFrame,
    max_iterations: int = 500
) -> List[Dict]:
    """
    Pour une prediction donnee, calcule quel changement minimal
    de pH/temperature/humidite changerait la culture recommandee.

    Cherche dans l'ordre:
      1) Chaque feature individuellement
      2) Paires de features
      3) Triplet (pH + temperature + humidite)

    Retourne une liste de contre-factuels tries par perturbation totale.
    """
    print(f"[INFO] Recherche de contre-factuels pour la prediction: {le.classes_[original_prediction]}...")

    instance = instance.flatten() if instance.ndim > 1 else instance
    cf_features_idx = [feature_names.index(f) for f in ["pH", "temperature", "humidite"]
                       if f in feature_names]

    counterfactuals = []

    # 1) Changer une seule feature
    for idx in cf_features_idx:
        fname = feature_names[idx]
        col_vals = X_train.iloc[:, idx].values
        # Tester des valeurs dans les extremes observees
        test_vals = np.linspace(col_vals.min(), col_vals.max(), 100)
        for val in test_vals:
            perturbed = instance.copy()
            perturbed[idx] = val
            pred = model.predict([perturbed])[0]
            if pred != original_prediction:
                delta = abs(val - instance[idx])
                counterfactuals.append({
                    "features_modifiees": {fname: round(val, 2)},
                    "valeur_initiale": {fname: round(instance[idx], 2)},
                    "delta": {fname: round(delta, 2)},
                    "delta_total": round(delta, 2),
                    "nouvelle_culture": le.classes_[pred],
                    "type": "1-feature"
                })
                break  # Premier changement qui fonctionne pour cette feature

    # 2) Paires de features
    for idx1, idx2 in itertools.combinations(cf_features_idx, 2):
        fname1, fname2 = feature_names[idx1], feature_names[idx2]
        col1_vals = X_train.iloc[:, idx1].values
        col2_vals = X_train.iloc[:, idx2].values

        # Echantillonner des combinaisons
        for val1 in np.linspace(col1_vals.min(), col1_vals.max(), 40):
            for val2 in np.linspace(col2_vals.min(), col2_vals.max(), 40):
                perturbed = instance.copy()
                perturbed[idx1] = val1
                perturbed[idx2] = val2
                pred = model.predict([perturbed])[0]
                if pred != original_prediction:
                    delta1 = abs(val1 - instance[idx1])
                    delta2 = abs(val2 - instance[idx2])
                    delta_total = delta1 + delta2
                    counterfactuals.append({
                        "features_modifiees": {
                            fname1: round(val1, 2),
                            fname2: round(val2, 2)
                        },
                        "valeur_initiale": {
                            fname1: round(instance[idx1], 2),
                            fname2: round(instance[idx2], 2)
                        },
                        "delta": {
                            fname1: round(delta1, 2),
                            fname2: round(delta2, 2)
                        },
                        "delta_total": round(delta_total, 2),
                        "nouvelle_culture": le.classes_[pred],
                        "type": "2-features"
                    })
                    break  # Premier pour cette paire
            if any(cf["type"] == "2-features" and
                   cf["features_modifiees"].get(fname1) is not None
                   for cf in counterfactuals[-10:]):
                break

    # 3) Triplet: toutes les 3 features modifiables
    if len(cf_features_idx) >= 3:
        idx1, idx2, idx3 = cf_features_idx[:3]
        fnames = [feature_names[i] for i in [idx1, idx2, idx3]]
        col_vals_list = [X_train.iloc[:, i].values for i in [idx1, idx2, idx3]]

        for val1 in np.linspace(col_vals_list[0].min(), col_vals_list[0].max(), 20):
            for val2 in np.linspace(col_vals_list[1].min(), col_vals_list[1].max(), 20):
                for val3 in np.linspace(col_vals_list[2].min(), col_vals_list[2].max(), 20):
                    perturbed = instance.copy()
                    perturbed[idx1] = val1
                    perturbed[idx2] = val2
                    perturbed[idx3] = val3
                    pred = model.predict([perturbed])[0]
                    if pred != original_prediction:
                        delta_total = (abs(val1 - instance[idx1]) +
                                       abs(val2 - instance[idx2]) +
                                       abs(val3 - instance[idx3]))
                        counterfactuals.append({
                            "features_modifiees": {
                                fnames[0]: round(val1, 2),
                                fnames[1]: round(val2, 2),
                                fnames[2]: round(val3, 2)
                            },
                            "valeur_initiale": {
                                fnames[0]: round(instance[idx1], 2),
                                fnames[1]: round(instance[idx2], 2),
                                fnames[2]: round(instance[idx3], 2)
                            },
                            "delta": {
                                fnames[0]: round(abs(val1 - instance[idx1]), 2),
                                fnames[1]: round(abs(val2 - instance[idx2]), 2),
                                fnames[2]: round(abs(val3 - instance[idx3]), 2)
                            },
                            "delta_total": round(delta_total, 2),
                            "nouvelle_culture": le.classes_[pred],
                            "type": "3-features"
                        })
                        break
                if any(cf.get("type") == "3-features" for cf in counterfactuals[-5:]):
                    break
            if any(cf.get("type") == "3-features" for cf in counterfactuals[-5:]):
                break

    # Trier par delta_total
    counterfactuals.sort(key=lambda x: x["delta_total"])

    return counterfactuals[:10]  # Top 10


# ════════════════════════════════════════════════
# 7. FONCTION PRINCIPALE D'EXPLICATION
# ════════════════════════════════════════════════

# Variables globales pour le module
_MODEL = None
_MODEL_NAME = None
_LE = None
_X_TRAIN = None
_X_DF = None
_SHAP_EXPLAINER = None
_SHAP_VALUES = None
_SHAP_SAMPLE = None
_LIME_EXPLAINER = None
_DT_MODEL = None


def initialize():
    """
    Initialise le module : charge les modeles, entraine SI necessaire,
    calcule SHAP et LIME, entraine l'arbre de decision.
    """
    global _MODEL, _MODEL_NAME, _LE, _X_TRAIN, _X_DF
    global _SHAP_EXPLAINER, _SHAP_VALUES, _SHAP_SAMPLE
    global _LIME_EXPLAINER, _DT_MODEL

    print("=" * 60)
    print("EXPLAINABILITY MODULE - Robot Agricole XAI")
    print("=" * 60)

    # 1. Charger/entrainer les modeles
    rf, xgb, le, scaler, X_df, y, full_df = load_or_train_models()

    # 2. Selectionner le meilleur modele
    best_model, best_name = select_best_model(rf, xgb, X_df, y)
    _MODEL = best_model
    _MODEL_NAME = best_name
    _LE = le
    _X_DF = X_df
    _X_TRAIN = X_df.values

    # 3. SHAP
    shap_result = compute_shap_explanations(best_model, X_df, le)
    if shap_result is not None:
        _SHAP_EXPLAINER, _SHAP_VALUES, _SHAP_SAMPLE = shap_result

        # Summary plot
        generate_shap_summary_plot(
            _SHAP_VALUES, _SHAP_SAMPLE,
            FEATURES_CULTURE, le, SHAP_SUMMARY_PATH
        )

        # Dependence plots
        generate_shap_dependence_plots(
            _SHAP_VALUES, _SHAP_SAMPLE,
            FEATURES_CULTURE, le
        )

    # 4. LIME
    _LIME_EXPLAINER = build_lime_explainer(
        best_model, _X_TRAIN, FEATURES_CULTURE, le
    )

    # 5. Arbre de decision
    _DT_MODEL = train_and_visualize_decision_tree(X_df, y, le, max_depth=4)

    print("\n[OK] Initialisation terminee. Module pret a l'emploi.")
    print("=" * 60)

    return {
        "model": _MODEL,
        "model_name": _MODEL_NAME,
        "label_encoder": _LE,
        "decision_tree": _DT_MODEL
    }


def explain_prediction(mesures: Dict[str, float]) -> Dict[str, Any]:
    """
    Prend un dictionnaire de mesures robot et retourne
    une explication textuelle et graphique.

    Args:
        mesures: dict avec au minimum pH, temperature, humidite
                 et optionnellement N, P, K (estimes par ailleurs)

    Returns:
        dict avec prediction, probabilites, SHAP, LIME, contre-factuels
    """
    global _MODEL, _MODEL_NAME, _LE, _X_DF
    global _SHAP_EXPLAINER, _SHAP_VALUES, _SHAP_SAMPLE
    global _LIME_EXPLAINER

    if _MODEL is None:
        initialize()

    # Construire le vecteur d'entree
    instance = np.array([mesures.get(f, 0.0) for f in FEATURES_CULTURE])

    # Prediction
    pred_class = _MODEL.predict([instance])[0]
    pred_proba = _MODEL.predict_proba([instance])[0]

    # Top 3 predictions
    top3_idx = np.argsort(pred_proba)[::-1][:3]
    top3 = [
        {"culture": _LE.classes_[i], "probabilite": round(float(pred_proba[i]), 4)}
        for i in top3_idx
    ]

    result = {
        "mesures": mesures,
        "prediction": _LE.classes_[pred_class],
        "probabilite": round(float(pred_proba[pred_class]), 4),
        "top_3_cultures": top3,
        "modele": _MODEL_NAME
    }

    # Explication SHAP locale
    if _SHAP_EXPLAINER is not None and _SHAP_VALUES is not None:
        try:
            import shap
            # Waterfall plot pour l'explication locale
            if isinstance(_SHAP_VALUES, list) and pred_class < len(_SHAP_VALUES):
                sv_instance = _SHAP_VALUES[pred_class][0]  # Reference
                # Calculer SHAP pour cette instance
                sv = _SHAP_EXPLAINER.shap_values(instance.reshape(1, -1))
                if isinstance(sv, list) and pred_class < len(sv):
                    sv_local = sv[pred_class][0]
                else:
                    sv_local = sv[0] if isinstance(sv, list) else sv[0]

                # Features les plus influentes
                feat_importance = [
                    {"feature": FEATURES_CULTURE[i],
                     "valeur": round(float(instance[i]), 2),
                     "shap_value": round(float(sv_local[i]), 4)}
                    for i in range(len(FEATURES_CULTURE))
                ]
                feat_importance.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

                result["shap_explication"] = {
                    "facteurs_clefs": feat_importance[:5],
                    "interpretation": _format_shap_interpretation(
                        feat_importance[:3], mesures, _LE.classes_[pred_class]
                    )
                }

                # Waterfall plot
                fig, ax = plt.subplots(figsize=(10, 6))
                try:
                    shap.waterfall_plot(
                        shap.Explanation(
                            values=sv_local,
                            base_values=0,
                            data=instance,
                            feature_names=FEATURES_CULTURE
                        ),
                        max_display=8,
                        show=False
                    )
                    plt.title(f"SHAP Waterfall: {_LE.classes_[pred_class]} "
                              f"(p={pred_proba[pred_class]:.2f})", fontsize=12)
                    plt.tight_layout()
                    waterfall_path = os.path.join(FIGURES_DIR, "shap_waterfall_local.png")
                    plt.savefig(waterfall_path, dpi=150, bbox_inches='tight')
                    plt.close()
                    result["shap_waterfall_path"] = waterfall_path
                except Exception:
                    plt.close()
        except Exception as e:
            result["shap_explication"] = {"erreur": str(e)}

    # Explication LIME
    if _LIME_EXPLAINER is not None:
        try:
            lime_exp = explain_with_lime(_LIME_EXPLAINER, _MODEL, instance)
            result["lime_explication"] = lime_exp

            # Visualisation LIME
            fig, ax = plt.subplots(figsize=(10, 5))
            features_lime = lime_exp["features"]
            feat_names = [f["feature"] for f in features_lime]
            feat_weights = [f["weight"] for f in features_lime]
            colors = ['green' if w > 0 else 'red' for w in feat_weights]
            ax.barh(range(len(feat_names)), feat_weights, color=colors, alpha=0.7)
            ax.set_yticks(range(len(feat_names)))
            ax.set_yticklabels(feat_names, fontsize=10)
            ax.axvline(x=0, color='gray', linestyle='-', linewidth=0.5)
            ax.set_xlabel("Poids LIME")
            ax.set_title(f"Explication LIME locale: {_LE.classes_[pred_class]}", fontsize=12)
            plt.tight_layout()
            lime_path = os.path.join(FIGURES_DIR, "lime_explication.png")
            plt.savefig(lime_path, dpi=150, bbox_inches='tight')
            plt.close()
            result["lime_plot_path"] = lime_path
        except Exception as e:
            result["lime_explication"] = {"erreur": str(e)}

    # Contre-factuels
    try:
        cfs = find_counterfactual(
            _MODEL, instance, pred_class, _LE,
            FEATURES_CULTURE, _X_DF, max_iterations=300
        )
        result["contre_factuels"] = cfs
        if cfs:
            result["contre_factuel_plus_accessible"] = cfs[0]
    except Exception as e:
        result["contre_factuels"] = {"erreur": str(e)}

    return result


def _format_shap_interpretation(
    top_features: List[dict], mesures: dict, predicted_culture: str
) -> str:
    """Cree une interpretation textuelle lisible des resultats SHAP."""
    lines = [
        f"Prediction: {predicted_culture}",
        "Facteurs determinants:"
    ]
    for f in top_features:
        fname = f["feature"]
        val = f["valeur"]
        sv = f["shap_value"]
        if sv > 0:
            direction = "favorise"
        else:
            direction = "defavorise"
        lines.append(f"  - {fname}={val} ({direction}, SHAP={sv:.3f})")
    return "\n".join(lines)


# ════════════════════════════════════════════════
# 8. FONCTION D'EXEMPLE / DEMO
# ════════════════════════════════════════════════

def demo():
    """Execute une demonstration du module d'explicabilite."""
    print("\n" + "=" * 60)
    print("DEMONSTRATION DU MODULE D'EXPLICABILITE")
    print("=" * 60)

    # Initialisation
    initialize()

    # Exemple 1: Sol pour Mais
    mesures_mais = {
        "pH": 6.0,
        "temperature": 28.0,
        "humidite": 65.0,
        "N": 100.0,
        "P": 45.0 / 2.29,  # P2O5 -> P
        "K": 42.0 / 1.205  # K2O -> K
    }

    print("\n--- Exemple 1: Mesures typiques Mais ---")
    exp1 = explain_prediction(mesures_mais)
    print(f"Prediction: {exp1['prediction']} (p={exp1['probabilite']:.2f})")
    print(f"Top 3: {[c['culture'] + '(' + str(c['probabilite']) + ')' for c in exp1['top_3_cultures']]}")

    if "shap_explication" in exp1:
        print(f"\nSHAP interpretation:\n{exp1['shap_explication']['interpretation']}")

    if "contre_factuels" in exp1 and exp1["contre_factuels"]:
        cf = exp1["contre_factuels"][0]
        print(f"\nContre-factuel le plus simple:")
        print(f"  Si {cf['features_modifiees']} -> {cf['nouvelle_culture']}")
        print(f"  Delta total: {cf['delta_total']}")

    # Exemple 2: Sol pour Riz
    mesures_riz = {
        "pH": 6.5,
        "temperature": 30.0,
        "humidite": 82.0,
        "N": 90.0,
        "P": 45.0 / 2.29,
        "K": 45.0 / 1.205
    }

    print("\n--- Exemple 2: Mesures typiques Riz ---")
    exp2 = explain_prediction(mesures_riz)
    print(f"Prediction: {exp2['prediction']} (p={exp2['probabilite']:.2f})")
    print(f"Top 3: {[c['culture'] + '(' + str(c['probabilite']) + ')' for c in exp2['top_3_cultures']]}")

    if "shap_explication" in exp2:
        print(f"\nSHAP interpretation:\n{exp2['shap_explication']['interpretation']}")

    print("\n[OK] Demonstration terminee.")
    print(f"\nFigures generees dans: {FIGURES_DIR}/")
    print(f"  - SHAP summary: {SHAP_SUMMARY_PATH}")
    print(f"  - SHAP dependence: {SHAP_DEPENDENCE_DIR}/")
    print(f"  - Arbre decision: {DECISION_TREE_PLOT_PATH}")
    print(f"  - Waterfall: {os.path.join(FIGURES_DIR, 'shap_waterfall_local.png')}")
    print(f"  - LIME: {os.path.join(FIGURES_DIR, 'lime_explication.png')}")
    print(f"\nModeles sauvegardes dans: {MODELES_DIR}/")

    return exp1, exp2


# ════════════════════════════════════════════════
# POINT D'ENTREE
# ════════════════════════════════════════════════

if __name__ == "__main__":
    demo()
