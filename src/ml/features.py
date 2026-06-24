#!/usr/bin/env python3
"""
features.py — Schema canonique des features pour le pipeline ML AgroScan.

Single source of truth pour :
  - La liste des features utilisees par chaque modele
  - Les colonnes cibles (N, P, K, culture)
  - Les features derivees creees par eda_preprocessing.py

Tous les scripts (training, inference, XAI) doivent importer depuis ce module.
"""

# ── Features brutes du dataset Crop_recommendation ─────────────────────
RAW_FEATURES = [
    'N', 'P', 'K',
    'temperature',
    'humidite',
    'pH',
    'precipitation',
]

# ── Target pour la classification ─────────────────────────────────────
CLASSIFICATION_TARGET = 'culture'

# ── Targets pour la regression NPK ───────────────────────────────────
REGRESSION_TARGETS = ['N', 'P', 'K']

# ── Features de regression (entree des estimateurs NPK) ──────────────
REGRESSION_FEATURES = ['pH', 'temperature', 'humidite']

# ── Features de classification (inclut engineered) ────────────────────
# Les 7 raw features + les features derivees creees par eda_preprocessing.py
CLASSIFICATION_FEATURES = RAW_FEATURES + [
    'ratio_N_P',
    'ratio_N_K',
    'ratio_P_K',
    'score_NPK_balance',
    'EC_approx',
    'pH_times_EC',
]

# ── Features utilisees par le module XAI (explicabilite) ─────────────
# Correspond aux features attendues par les modeles entrainés sur le
# dataset Kaggle (version simplifiee 6 features).
XAI_FEATURES = ['N', 'P', 'K', 'pH', 'temperature', 'humidite']

# ── Features attendues par reco_engine.py (pour validation) ────────────
RECO_FEATURES = ['EC', 'pH', 'humidite', 'temperature']

# ── Colonnes non-features a exclure lors de la construction de X ──────
NON_FEATURE_COLS = [
    CLASSIFICATION_TARGET,
    'id', 'index', 'Unnamed: 0',
    'echantillon_id', 'sample_id',
    'label',
]

# ── Mapping unites pour le rapport EDA ────────────────────────────────
UNITES = {
    'N': 'kg/ha',
    'P': 'kg/ha',
    'K': 'kg/ha',
    'temperature': '°C',
    'humidite': '%',
    'pH': 'pH',
    'precipitation': 'mm/an',
    'EC': 'dS/m',
    'P2O5': 'kg/ha',
    'K2O': 'kg/ha',
}

# ── Metriques a sauvegarder par type de tache ─────────────────────────
CLASSIFICATION_METRICS = [
    'accuracy', 'f1_score', 'f1_macro',
    'precision_per_class', 'recall_per_class', 'f1_per_class',
    'cv_score', 'best_params',
    'test_accuracy', 'test_f1_weighted', 'test_f1_macro',
    'test_classification_report',
]

REGRESSION_METRICS = [
    'rmse', 'mae', 'r2',
    'cv_rmse', 'best_params',
    'test_rmse', 'test_mae', 'test_r2',
]
