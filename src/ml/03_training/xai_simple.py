#!/usr/bin/env python3
"""Explicabilite simplifiee pour le robot agricole"""

import os, json, joblib, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import shap
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.preprocessing import StandardScaler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR     = os.path.join(SCRIPT_DIR, '..')
DIR        = os.path.join(ML_DIR, '01_databases')
MODEL_DIR  = os.path.join(ML_DIR, "02_models")
FIG_DIR    = os.path.join(ML_DIR, "04_figures")
os.makedirs(FIG_DIR, exist_ok=True)

print("Chargement des modeles et donnees...")
model = joblib.load(os.path.join(MODEL_DIR, "random_forest.pkl"))
scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
le = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
df = pd.read_csv(os.path.join(DIR, "dataset_preprocessed.csv"))
features = [c for c in df.columns if c != "culture"]
X = scaler.transform(df[features].values)
y = df["culture"].values

print(f"Model: Random Forest, {len(features)} features, {len(le.classes_)} classes")
print(f"Features: {features}")
print()

# 1. Feature importance integree
print("1. Importance des features...")
importances = model.feature_importances_
indices = np.argsort(importances)[::-1]
plt.figure(figsize=(10, 6))
plt.bar(range(len(importances)), importances[indices])
plt.xticks(range(len(importances)), [features[i] for i in indices], rotation=45, ha="right")
plt.title("Importance des features (Random Forest)")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "feature_importance.png"))
plt.close()
print("   feature_importance.png sauvegarde")

# 2. SHAP (echantillon reduit pour rapidite)
print("2. Calcul SHAP (150 echantillons)...")
X_sample = X[np.random.choice(X.shape[0], min(150, X.shape[0]), replace=False)]
try:
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    # SHAP summary plot (moyenne toutes classes)
    if isinstance(shap_values, list):
        sv = np.abs(shap_values).mean(axis=0)
    else:
        sv = np.abs(shap_values)
    shap.summary_plot(shap_values, X_sample, feature_names=features, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "shap_summary.png"), bbox_inches="tight")
    plt.close()
    print("   shap_summary.png sauvegarde")
    
    # SHAP dependence pour pH
    shap.dependence_plot("pH", shap_values, X_sample, feature_names=features, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "shap_dependence_pH.png"), bbox_inches="tight")
    plt.close()
    print("   shap_dependence_pH.png sauvegarde")
except Exception as e:
    print(f"   SHAP skippe: {e}")

# 3. Arbre de decision interpretable
print("3. Arbre de decision (profondeur 4)...")
tree = DecisionTreeClassifier(max_depth=4, random_state=42, min_samples_leaf=5)
tree.fit(X, le.transform(y))
plt.figure(figsize=(24, 12))
plot_tree(tree, feature_names=features, class_names=le.classes_, filled=True, fontsize=8)
plt.title("Arbre de decision interpretable (profondeur 4)")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "decision_tree.png"), dpi=150)
plt.close()
print("   decision_tree.png sauvegarde")

# 4. Fonction d'explication pour une prediction
print("4. Demonstration explication d une prediction...")
test_measures = {"pH": 6.5, "temperature": 28.0, "humidite": 65.0, "precipitation": 1000,
                 "N": 90, "P": 30, "K": 40, "ratio_N_P": 3.0, "ratio_N_K": 2.25,
                 "ratio_P_K": 0.75, "score_NPK_balance": 0.5, "EC_approx": 0.3, "pH_times_EC": 1.95}

X_test_point = np.array([[test_measures[f] for f in features]])
X_test_scaled = scaler.transform(X_test_point)
pred = model.predict(X_test_scaled)[0]
pred_name = le.inverse_transform([pred])[0]
probas = model.predict_proba(X_test_scaled)[0]
top3 = np.argsort(probas)[::-1][:3]

print(f"\n   Mesures: pH={test_measures['pH']}, T={test_measures['temperature']}C, hum={test_measures['humidite']}%")
print(f"   Prediction: {pred_name} (probabilite: {probas[pred]:.1%})")
print(f"   Top 3:")
for i, idx in enumerate(top3):
    print(f"      {i+1}. {le.classes_[idx]}: {probas[idx]:.1%}")

# 5. Contre-factuels
print("\n5. Contre-factuels: quel changement changerait la culture ?")
original_pred = pred_name
for feat_name, step in [("pH", 0.2), ("temperature", 1.0), ("humidite", 5.0)]:
    for direction in [1, -1]:
        test_vals = test_measures.copy()
        for n in range(1, 20):
            test_vals[feat_name] = test_measures[feat_name] + direction * step * n
            X_new = np.array([[test_vals[f] for f in features]])
            X_new_scaled = scaler.transform(X_new)
            new_pred = model.predict(X_new_scaled)[0]
            new_name = le.inverse_transform([new_pred])[0]
            if new_name != original_pred:
                change = direction * step * n
                print(f"   {feat_name} {change:+.1f} -> {new_name}")
                break

print("\nFichiers generes dans figures/:")
for f in sorted(os.listdir(FIG_DIR)):
    print(f"  - {f}")
print("\nDONE")
