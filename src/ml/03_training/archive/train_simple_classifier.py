#!/usr/bin/env python3
"""Entrainement classifieur simplifie + regresseurs NPK + SHAP"""
import os, json, joblib, warnings, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
import xgboost as xgb
import shap

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR     = os.path.join(SCRIPT_DIR, '..')
DIR        = os.path.join(ML_DIR, '01_databases')
MODEL_DIR  = os.path.join(ML_DIR, "02_models")
FIG_DIR    = os.path.join(ML_DIR, "04_figures")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# 1. Chargement dataset original Kaggle (valeurs brutes)
print("Chargement dataset Kaggle...")
df_kaggle = pd.read_csv(os.path.join(DIR, "dataset_preprocessed.csv"))
kaggle_cols = {'N': 'N', 'P': 'P', 'K': 'K', 'temperature': 'temperature', 
               'humidite': 'humidite', 'ph': 'pH', 'rainfall': 'precipitation'}

# En fait, utilisons le dataset preprocessed qui a deja les bonnes colonnes
# Features simplifiees : N, P, K, pH, temperature, humidite
FEATURES = ["N", "P", "K", "pH", "temperature", "humidite"]
TARGET = "culture"

print(f"Colonnes disponibles: {list(df_kaggle.columns)}")
print(f"Features: {FEATURES}")
print(f"Cultures: {sorted(df_kaggle[TARGET].unique())}")

X = df_kaggle[FEATURES].values
y = LabelEncoder().fit_transform(df_kaggle[TARGET])

# Split train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scaler
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# RF Classifier
print("\nEntrainement Random Forest (6 features)...")
rf = RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
rf.fit(X_train_scaled, y_train)
acc_rf = accuracy_score(y_test, rf.predict(X_test_scaled))
print(f"  RF Accuracy: {acc_rf:.4f}")

# XGBoost
print("Entrainement XGBoost (6 features)...")
xgb_clf = xgb.XGBClassifier(n_estimators=200, max_depth=8, learning_rate=0.1, 
                             random_state=42, n_jobs=-1, verbosity=0)
xgb_clf.fit(X_train_scaled, y_train)
acc_xgb = accuracy_score(y_test, xgb_clf.predict(X_test_scaled))
print(f"  XGB Accuracy: {acc_xgb:.4f}")

# Meilleur
best = rf if acc_rf >= acc_xgb else xgb_clf
best_name = "RF" if acc_rf >= acc_xgb else "XGB"
print(f"\nMeilleur modele: {best_name} (acc={max(acc_rf,acc_xgb):.4f})")

# Matrice confusion
cm = confusion_matrix(y_test, best.predict(X_test_scaled))
labels = sorted(df_kaggle[TARGET].unique())
plt.figure(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt="d", xticklabels=labels, yticklabels=labels, cmap="Blues")
plt.title(f"Matrice confusion - {best_name} 6 features (acc={max(acc_rf,acc_xgb):.3f})")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "confusion_matrix_simple.png"))
plt.close()

# SHAP explainer
print("\nPreparation SHAP...")
# Utiliser un echantillon representatif pour le background
background = X_train_scaled[np.random.choice(X_train_scaled.shape[0], 100, replace=False)]
explainer = shap.TreeExplainer(best, background)
joblib.dump(explainer, os.path.join(MODEL_DIR, "shap_explainer.pkl"))

# SHAP values pour 100 echantillons test
shap_values = explainer.shap_values(X_test_scaled[:100])

# SHAP 0.52+ retourne array (n_samples, n_features, n_classes)
# Calculer l'importance moyenne absolue toutes classes confondues
if isinstance(shap_values, list):
    # Ancien format (liste par classe)
    shap_mean_abs = np.mean([np.abs(sv) for sv in shap_values], axis=(0, 1))
else:
    # Nouveau format array (n_samples, n_features, n_classes)
    shap_mean_abs = np.mean(np.abs(shap_values), axis=(0, 2))

# Barplot SHAP mean absolute
plt.figure(figsize=(8, 5))
indices = np.argsort(shap_mean_abs)[::-1]
plt.barh(range(len(FEATURES)), shap_mean_abs[indices])
plt.yticks(range(len(FEATURES)), [FEATURES[i] for i in indices])
plt.xlabel("|SHAP value| moyen (toutes classes)")
plt.title("Impact des features sur la recommandation")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "shap_impact_simple.png"), bbox_inches='tight', dpi=150)
plt.close()

# Feature importance
importances = best.feature_importances_
indices = np.argsort(importances)[::-1]
plt.figure(figsize=(8, 5))
plt.bar(range(len(FEATURES)), importances[indices])
plt.xticks(range(len(FEATURES)), [FEATURES[i] for i in indices], rotation=45)
plt.title(f"Feature Importance - {best_name}")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "feature_importance_simple.png"))
plt.close()

# Sauvegarder
le = LabelEncoder()
le.fit(df_kaggle[TARGET])
joblib.dump(best, os.path.join(MODEL_DIR, "classifier_simple.pkl"))
joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler_simple.pkl"))
joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder_simple.pkl"))

print(f"\nModeles sauvegardes dans {MODEL_DIR}/")
print("Fichiers:")
for f in ["classifier_simple.pkl", "scaler_simple.pkl", "label_encoder_simple.pkl", "shap_explainer.pkl"]:
    p = os.path.join(MODEL_DIR, f)
    sz = os.path.getsize(p)
    print(f"  {f}: {sz} bytes")

print("\nDONE")
