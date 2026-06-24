#!/usr/bin/env python3
"""
explain.py — Module d'explicabilite pour le robot agricole.

Ce module peut etre importe directement:
    from explain import initialize, explain_prediction, find_counterfactual

Il delegue le gros du travail a explainability.py mais offre
une interface propre et documentee pour l'integration robot.

Usage:
    from explain import explain_prediction

    mesures = {"pH": 6.2, "temperature": 28, "humidite": 65, "N": 100, "P": 19.7, "K": 34.9}
    explication = explain_prediction(mesures)
    print(explication["prediction"])
    print(explication["shap_explication"]["interpretation"])
"""

# Re-exporter les fonctions principales depuis le module principal
from explainability import (
    initialize,
    explain_prediction,
    find_counterfactual,
    explain_with_lime,
    load_or_train_models,
    generate_training_data,
    train_and_visualize_decision_tree,
    compute_shap_explanations,
    generate_shap_summary_plot,
    generate_shap_dependence_plots,
    _MODEL, _MODEL_NAME, _LE, _X_DF, _DT_MODEL,
    FEATURES_CULTURE, CULTURES_ORDERED,
    BASE_DIR, MODELES_DIR, FIGURES_DIR,
    SHAP_SUMMARY_PATH, DECISION_TREE_PLOT_PATH
)

__all__ = [
    'initialize',
    'explain_prediction',
    'find_counterfactual',
    'explain_with_lime',
    'load_or_train_models',
    'generate_training_data',
    'train_and_visualize_decision_tree',
    'compute_shap_explanations',
    'generate_shap_summary_plot',
    'generate_shap_dependence_plots',
    'FEATURES_CULTURE',
    'CULTURES_ORDERED',
]

__version__ = "1.0.0"
__author__ = "Robot Agricole XAI Team"
