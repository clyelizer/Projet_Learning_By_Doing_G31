#!/usr/bin/env python3
"""Entrainement rapide des modeles"""

import os, json, joblib, warnings, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report, mean_squared_error, r2_score
import xgboost as xgb

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR     = os.path.join(SCRIPT_DIR, '..')
DIR        = os.path.join(ML_DIR, '01_databases')
MODEL_DIR  = os.path.join(ML_DIR, "02_models")
FIG_DIR    = os.path.join(ML_DIR, "04_figures")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

print("Chargement des donnees...")
df = pd.read_csv(os.path.join(DIR, "dataset_preprocessed.csv"))

# Pour la classification: features = toutes les colonnes sauf culture
features_clf = [c for c in df.columns if c != "culture"]
X_clf = df[features_clf].values
y_clf = LabelEncoder().fit_transform(df["culture"])

X_train, X_test, y_train, y_test = train_test_split(X_clf, y_clf, test_size=0.2, random_state=42, stratify=y_clf)
scaler_clf = StandardScaler()
X_train = scaler_clf.fit_transform(X_train)
X_test = scaler_clf.transform(X_test)

print(f"Classification: {len(features_clf)} features, {len(np.unique(y_clf))} classes")

# RF Classifier
print("Entrainement Random Forest classifier...")
rf_clf = RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
rf_clf.fit(X_train, y_train)
y_pred_rf = rf_clf.predict(X_test)
acc_rf = accuracy_score(y_test, y_pred_rf)
f1_rf = f1_score(y_test, y_pred_rf, average="weighted")
print(f"  RF Accuracy: {acc_rf:.4f}, F1: {f1_rf:.4f}")

# XGBoost Classifier
print("Entrainement XGBoost classifier...")
xgb_clf = xgb.XGBClassifier(n_estimators=200, max_depth=8, learning_rate=0.1, random_state=42, n_jobs=-1, verbosity=0)
xgb_clf.fit(X_train, y_train)
y_pred_xgb = xgb_clf.predict(X_test)
acc_xgb = accuracy_score(y_test, y_pred_xgb)
f1_xgb = f1_score(y_test, y_pred_xgb, average="weighted")
print(f"  XGB Accuracy: {acc_xgb:.4f}, F1: {f1_xgb:.4f}")

# Meilleur modele
best_clf = rf_clf if acc_rf >= acc_xgb else xgb_clf
best_name = "RF" if acc_rf >= acc_xgb else "XGB"
# Matrice de confusion
cm = confusion_matrix(y_test, best_clf.predict(X_test))
labels = sorted(df["culture"].unique())
plt.figure(figsize=(12, 10))
sns.heatmap(cm, annot=True, fmt="d", xticklabels=labels, yticklabels=labels, cmap="Blues")
plt.title(f"Matrice de confusion - {best_name} (acc={max(acc_rf,acc_xgb):.3f})")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "confusion_matrix.png"))
plt.close()
print(f"  Matrice sauvegardee: confusion_matrix.png")

# Regression NPK
print("\nRegression NPK...")
features_reg = ["pH", "temperature", "humidite"]
X_reg = df[features_reg].values
targets = {"N": 0, "P": 1, "K": 2}
scaler_reg = StandardScaler()
X_reg = scaler_reg.fit_transform(X_reg)

reg_models = {}
for target_name, col_idx in targets.items():
    y_reg = df.iloc[:, col_idx].values
    Xr_train, Xr_test, yr_train, yr_test = train_test_split(X_reg, y_reg, test_size=0.2, random_state=42)
    
    rf_reg = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
    rf_reg.fit(Xr_train, yr_train)
    yp_reg = rf_reg.predict(Xr_test)
    r2 = r2_score(yr_test, yp_reg)
    rmse = np.sqrt(mean_squared_error(yr_test, yp_reg))
    print(f"  RF {target_name}: R2={r2:.3f}, RMSE={rmse:.2f}")
    
    # Figure
    plt.figure(figsize=(6, 6))
    plt.scatter(yr_test, yp_reg, alpha=0.5)
    plt.plot([yr_test.min(), yr_test.max()], [yr_test.min(), yr_test.max()], "r--")
    plt.xlabel("Reel"); plt.ylabel("Prediction"); plt.title(f"Regression {target_name} (R2={r2:.3f})")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, f"regression_{target_name}.png"))
    plt.close()
    
    reg_models[target_name] = {"model": rf_reg, "r2": r2, "rmse": rmse}

# Sauvegarder
le = LabelEncoder()
le.fit(df["culture"])
joblib.dump(rf_clf, os.path.join(MODEL_DIR, "random_forest.pkl"))
joblib.dump(xgb_clf, os.path.join(MODEL_DIR, "xgboost.pkl"))
joblib.dump(scaler_clf, os.path.join(MODEL_DIR, "scaler.pkl"))
joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.pkl"))
for target_name, info in reg_models.items():
    joblib.dump(info["model"], os.path.join(MODEL_DIR, f"regressor_{target_name}.pkl"))

# Metriques
with open(os.path.join(DIR, "metriques.txt"), "w") as f:
    f.write(f"=== Metriques ===\n")
    f.write(f"RF Classifier: accuracy={acc_rf:.4f}, F1={f1_rf:.4f}\n")
    f.write(f"XGB Classifier: accuracy={acc_xgb:.4f}, F1={f1_xgb:.4f}\n")
    f.write(f"Meilleur: {best_name} ({max(acc_rf,acc_xgb):.4f})\n\n")
    f.write("Regression NPK (features: pH, temperature, humidite):\n")
    for target_name, info in reg_models.items():
        f.write(f"  {target_name}: R2={info['r2']:.3f}, RMSE={info['rmse']:.2f}\n")

print(f"\nModeles sauvegardes dans {MODEL_DIR}/")
print("Metriques: metriques.txt")
print("DONE")
