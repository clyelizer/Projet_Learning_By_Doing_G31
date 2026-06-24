#!/usr/bin/env python3
"""
eda_preprocessing.py - Exploration et preprocessing pour robot agricole
===============================================================
Projet: Robot agricole - Base de reference sol/cultures africaines
Auteur: Agent Hermes

Ce script:
  1. Charge la base JSON (16 cultures africaines) et les datasets CSV
  2. Genere des stats descriptives -> rapport texte
  3. Cree des visualisations: histogrammes, boxplots, heatmap correlation, pairplot
  4. Normalise (StandardScaler) N, P, K, pH, temperature, humidite
  5. Cree les features croisees: pH*EC, ratios NPK
  6. Sauvegarde le dataset preprocesse
  7. Split train/test/val (70/15/15)
  8. Genere un rapport EDA en Markdown

Execution: python3 eda_preprocessing.py
"""

import json
import os
import warnings
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # mode non-interactif pour serveur/terminal
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
warnings.filterwarnings('ignore')
sns.set_theme(style='whitegrid', palette='muted', font_scale=0.9)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR     = os.path.join(SCRIPT_DIR, '..')
BASE_DIR   = os.path.join(ML_DIR, '01_databases')
DATA_DIR   = '/home/coulibaly/HERMES_wd/datasets'
FIGURES_DIR = os.path.join(ML_DIR, '04_figures')

JSON_PATH    = os.path.join(BASE_DIR, 'base_reference_agricole.json')
CSV_CROP     = os.path.join(DATA_DIR, 'Crop_recommendation.csv')
CSV_ISDA     = os.path.join(DATA_DIR, 'iSDA_soil_data.csv')

PREPROCESSED = os.path.join(BASE_DIR, 'dataset_preprocessed.csv')
RAPPORT_TXT  = os.path.join(SCRIPT_DIR, 'statistiques_descriptives.txt')
RAPPORT_MD   = os.path.join(SCRIPT_DIR, 'rapport_eda.md')

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# ---------------------------------------------------------------------------
# 1. CHARGEMENT DES DONNEES
# ---------------------------------------------------------------------------
print("=" * 60)
print("EDA & PREPROCESSING - Robot Agricole")
print("=" * 60)
print(f"[{datetime.now().strftime('%H:%M:%S')}] Chargement des donnees...")

# --- 1a. Base JSON de reference ---
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    base_ref = json.load(f)

print(f"  -> JSON: {base_ref['metadata']['titre']}")
print(f"  -> {base_ref['metadata']['cultures_count']} cultures de reference")

ref_records = []
for c in base_ref['cultures']:
    sol = c.get('sol', {})
    fert = c.get('fertilisation', {})
    record = {
        'culture': c['culture'],
        'nom_scientifique': c['nom_scientifique'],
        'pH_optimal': sol.get('pH', {}).get('optimal'),
        'pH_min': sol.get('pH', {}).get('min'),
        'pH_max': sol.get('pH', {}).get('max'),
        'temperature_min': sol.get('temperature', {}).get('min'),
        'temperature_max': sol.get('temperature', {}).get('max'),
        'precipitation_min': sol.get('precipitation', {}).get('min'),
        'precipitation_max': sol.get('precipitation', {}).get('max'),
        'N_min': sol.get('N', {}).get('min'),
        'N_max': sol.get('N', {}).get('max'),
        'N_optimal': sol.get('N', {}).get('optimal'),
        'P2O5_min': sol.get('P2O5', {}).get('min'),
        'P2O5_max': sol.get('P2O5', {}).get('max'),
        'P2O5_optimal': sol.get('P2O5', {}).get('optimal'),
        'K2O_min': sol.get('K2O', {}).get('min'),
        'K2O_max': sol.get('K2O', {}).get('max'),
        'K2O_optimal': sol.get('K2O', {}).get('optimal'),
        'humidite_min': sol.get('humidite', {}).get('min'),
        'humidite_max': sol.get('humidite', {}).get('max'),
        'humidite_optimal': sol.get('humidite', {}).get('optimal'),
        'NPK_recommandation': fert.get('NPK_recommandation', ''),
    }
    ref_records.append(record)

df_ref = pd.DataFrame(ref_records)
print(f"  -> DataFrame reference: {df_ref.shape[0]} cultures, {df_ref.shape[1]} colonnes")

# --- 1b. Dataset Crop_recommendation.csv ---
df_crop = pd.read_csv(CSV_CROP)
print(f"  -> Crop_recommendation: {df_crop.shape[0]} lignes, {df_crop.shape[1]} colonnes")
print(f"     Colonnes: {list(df_crop.columns)}")
print(f"     Cultures: {sorted(df_crop['label'].unique())}")

# Renommer pour coherence
df_crop.rename(columns={
    'label': 'culture',
    'humidity': 'humidite',
    'ph': 'pH',
    'rainfall': 'precipitation'
}, inplace=True)

# --- 1c. Dataset iSDA_soil_data.csv ---
usecols_isda = [
    'ph', 'electrical_conductivity', 'nitrogen_total',
    'phosphorus_extractable', 'potassium_extractable',
    'carbon_organic', 'latitude', 'longitude'
]
try:
    df_isda = pd.read_csv(CSV_ISDA, usecols=usecols_isda)
except ValueError:
    df_isda = pd.read_csv(CSV_ISDA)
    rename_map = {
        'ph': 'ph',
        'electrical_conductivity': 'EC',
        'nitrogen_total': 'N_total',
        'phosphorus_extractable': 'P_extractable',
        'potassium_extractable': 'K_extractable',
        'carbon_organic': 'C_organic',
    }
    df_isda.rename(columns={k: v for k, v in rename_map.items() if k in df_isda.columns}, inplace=True)
else:
    df_isda.rename(columns={
        'electrical_conductivity': 'EC',
        'nitrogen_total': 'N_total',
        'phosphorus_extractable': 'P_extractable',
        'potassium_extractable': 'K_extractable',
        'carbon_organic': 'C_organic',
    }, inplace=True)

print(f"  -> iSDA_soil_data: {df_isda.shape[0]} lignes, {df_isda.shape[1]} colonnes")
print(f"     Colonnes: {list(df_isda.columns)}")

ec_count = df_isda['EC'].notna().sum() if 'EC' in df_isda.columns else 0
print(f"     Echantillons iSDA avec EC: {ec_count} ({100*ec_count/len(df_isda):.1f}%)")

# ---------------------------------------------------------------------------
# 2. STATISTIQUES DESCRIPTIVES
# ---------------------------------------------------------------------------
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Generation des stats descriptives...")

desc_numeriques = df_crop.describe(include=[np.number]).round(3)
desc_categories = df_crop.describe(include=['object'])

with open(RAPPORT_TXT, 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("STATISTIQUES DESCRIPTIVES - Robot Agricole\n")
    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 70 + "\n\n")

    f.write("--- APERCU DU DATASET ---\n")
    f.write(f"Dimensions: {df_crop.shape[0]} lignes, {df_crop.shape[1]} colonnes\n")
    f.write(f"Types de cultures: {df_crop['culture'].nunique()}\n")
    f.write(f"Cultures presentes: {', '.join(sorted(df_crop['culture'].unique()))}\n\n")

    f.write("--- STATS NUMERIQUES ---\n")
    f.write(desc_numeriques.to_string())
    f.write("\n\n")

    f.write("--- STATS CATEGORIELLES ---\n")
    f.write(desc_categories.to_string())
    f.write("\n\n")

    f.write("--- VALEURS MANQUANTES ---\n")
    missing = df_crop.isnull().sum()
    missing_pct = 100 * missing / len(df_crop)
    missing_df = pd.DataFrame({'Valeurs manquantes': missing, 'Pourcentage (%)': missing_pct.round(2)})
    f.write(missing_df.to_string())
    f.write("\n\n")

    f.write("--- DISTRIBUTION PAR CULTURE ---\n")
    counts = df_crop['culture'].value_counts()
    f.write(f"{'Culture':<20} {'Effectif':<10} {'%':<10}\n")
    f.write("-" * 40 + "\n")
    for culture, cnt in counts.items():
        f.write(f"{culture:<20} {cnt:<10} {100*cnt/len(df_crop):.1f}%\n")
    f.write("\n")

    f.write("--- STATS DE LA BASE DE REFERENCE JSON ---\n")
    f.write(f"{'Culture':<20} {'pH_opt':<8} {'N_opt':<8} {'P2O5_opt':<10} {'K2O_opt':<10} {'T_min':<8} {'T_max':<8}\n")
    f.write("-" * 72 + "\n")
    for _, r in df_ref.iterrows():
        f.write(f"{r['culture']:<20} {str(r['pH_optimal']):<8} {str(r['N_optimal']):<8} "
                f"{str(r['P2O5_optimal']):<10} {str(r['K2O_optimal']):<10} "
                f"{str(r['temperature_min']):<8} {str(r['temperature_max']):<8}\n")

    f.write("\n--- STATS iSDA SOIL DATA ---\n")
    f.write(f"Total echantillons: {len(df_isda)}\n")
    if 'EC' in df_isda.columns:
        f.write(f"Colonne EC: {df_isda['EC'].notna().sum()} valeurs non-nulles\n")
        f.write(df_isda['EC'].describe().to_string())
    f.write("\n\n")
    f.write("=" * 70 + "\n")
    f.write("FIN DU RAPPORT\n")

print(f"  -> Rapport texte sauvegarde: {RAPPORT_TXT}")

# ---------------------------------------------------------------------------
# 3. VISUALISATIONS
# ---------------------------------------------------------------------------
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Creation des visualisations...")

num_cols = ['N', 'P', 'K', 'temperature', 'humidite', 'pH', 'precipitation']
num_cols_present = [c for c in num_cols if c in df_crop.columns]

# --- 3a. Histogrammes ---
fig, axes = plt.subplots(3, 3, figsize=(14, 10))
axes = axes.flatten()
for i, col in enumerate(num_cols_present):
    if i < len(axes):
        sns.histplot(df_crop[col].dropna(), kde=True, bins=30, ax=axes[i], color='steelblue')
        axes[i].set_title(f'Distribution de {col}', fontsize=11)
        axes[i].set_xlabel(col)
        axes[i].set_ylabel('Frequence')
for j in range(len(num_cols_present), len(axes)):
    axes[j].set_visible(False)
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'histogrammes.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  -> histogrammes.png")

# --- 3b. Boxplots par culture ---
fig, axes = plt.subplots(2, 4, figsize=(18, 10))
axes = axes.flatten()
for i, col in enumerate(num_cols_present):
    if i < len(axes):
        order = sorted(df_crop['culture'].unique())
        sns.boxplot(data=df_crop, x='culture', y=col, ax=axes[i],
                    order=order, palette='Set2')
        axes[i].set_title(f'{col} par culture', fontsize=11)
        axes[i].tick_params(axis='x', rotation=45)
for j in range(len(num_cols_present), len(axes)):
    axes[j].set_visible(False)
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'boxplots_par_culture.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  -> boxplots_par_culture.png")

# --- 3c. Heatmap de correlation ---
corr = df_crop[num_cols_present].corr()
mask = np.triu(np.ones_like(corr, dtype=bool))
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r',
            vmin=-1, vmax=1, center=0, square=True,
            linewidths=0.5, cbar_kws={'shrink': 0.8}, ax=ax)
ax.set_title('Matrice de correlation - Variables du sol', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'heatmap_correlation.png'), dpi=150, bbox_inches='tight')
plt.close()
print("  -> heatmap_correlation.png")

# --- 3d. Pairplot ---
if len(df_crop) > 1000:
    df_sample = df_crop.sample(n=1000, random_state=RANDOM_SEED)
else:
    df_sample = df_crop.copy()

pair_cols = [c for c in ['N', 'P', 'K', 'temperature', 'humidite', 'pH'] if c in df_sample.columns]
if len(pair_cols) >= 3:
    g = sns.pairplot(df_sample, vars=pair_cols, hue='culture', palette='tab10',
                     diag_kind='kde', plot_kws={'alpha': 0.5, 's': 15})
    g.fig.suptitle('Pairplot des variables numeriques (echantillon de 1000)', y=1.02, fontsize=13)
    plt.savefig(os.path.join(FIGURES_DIR, 'pairplot.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  -> pairplot.png")

# ---------------------------------------------------------------------------
# 4. NORMALISATION AVEC STANDARDSCALER
# ---------------------------------------------------------------------------
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Normalisation (StandardScaler)...")

cols_to_scale = ['N', 'P', 'K', 'pH', 'temperature', 'humidite']
cols_to_scale = [c for c in cols_to_scale if c in df_crop.columns]

scaler = StandardScaler()
df_scaled = df_crop.copy()
df_scaled[cols_to_scale] = scaler.fit_transform(df_crop[cols_to_scale])

print(f"  -> Colonnes normalisees: {cols_to_scale}")
print(f"  -> Moyennes apres normalisation: {df_scaled[cols_to_scale].mean().round(4).to_dict()}")
print(f"  -> Ecarts-types apres normalisation: {df_scaled[cols_to_scale].std().round(4).to_dict()}")

# ---------------------------------------------------------------------------
# 5. FEATURES CROISEES
# ---------------------------------------------------------------------------
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Creation des features croisees...")

df_feat = df_scaled.copy()

eps = 1e-10

# --- 5a. Ratios NPK ---
if 'N' in df_feat.columns and 'P' in df_feat.columns:
    df_feat['ratio_N_P'] = np.where(df_feat['P'] != 0, df_feat['N'] / df_feat['P'], np.nan)
    print("  -> ratio_N_P = N / P cree")

if 'N' in df_feat.columns and 'K' in df_feat.columns:
    df_feat['ratio_N_K'] = np.where(df_feat['K'] != 0, df_feat['N'] / df_feat['K'], np.nan)
    print("  -> ratio_N_K = N / K cree")

if 'P' in df_feat.columns and 'K' in df_feat.columns:
    df_feat['ratio_P_K'] = np.where(df_feat['K'] != 0, df_feat['P'] / df_feat['K'], np.nan)
    print("  -> ratio_P_K = P / K cree")

# Score de balance NPK
if all(c in df_feat.columns for c in ['N', 'P', 'K']):
    max_npk = df_feat[['N', 'P', 'K']].max(axis=1).abs() + eps
    df_feat['score_NPK_balance'] = 1 - (
        (df_feat['N'].abs() / max_npk - 0.5).abs() +
        (df_feat['P'].abs() / max_npk - 0.3).abs() +
        (df_feat['K'].abs() / max_npk - 0.2).abs()
    ) / 2
    print("  -> score_NPK_balance cree")

# --- 5b. pH * EC ---
if 'pH' in df_feat.columns and 'EC' in df_isda.columns:
    isda_ec_clean = df_isda[['ph', 'EC']].dropna(subset=['EC']).copy()
    isda_ec_clean.rename(columns={'ph': 'pH_isda'}, inplace=True)

    if len(isda_ec_clean) > 0:
        ph_crop = df_feat['pH'].values
        ph_isda = isda_ec_clean['pH_isda'].values
        ec_isda = isda_ec_clean['EC'].values

        nearest_ec = []
        for ph_val in ph_crop:
            idx = np.argmin(np.abs(ph_isda - ph_val))
            nearest_ec.append(ec_isda[idx])

        df_feat['EC_approx'] = nearest_ec
        df_feat['pH_times_EC'] = df_feat['pH'] * df_feat['EC_approx']
        print(f"  -> pH*EC cree (via plus proche pH iSDA, {len(nearest_ec)} valeurs assignees)")
    else:
        print("  -> WARNING: Pas de valeurs EC dans iSDA, pH*EC non cree")
else:
    print("  -> WARNING: Colonnes pH ou EC manquantes, pH*EC non cree")

print(f"\n  Dimensions finales: {df_feat.shape[0]} lignes, {df_feat.shape[1]} colonnes")
print(f"  Nouvelles colonnes: {[c for c in df_feat.columns if c not in df_crop.columns]}")

# ---------------------------------------------------------------------------
# 6. SAUVEGARDE DU DATASET PREPROCESSE
# ---------------------------------------------------------------------------
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sauvegarde du dataset preprocesse...")

df_feat.to_csv(PREPROCESSED, index=False)
print(f"  -> Sauvegarde: {PREPROCESSED} ({os.path.getsize(PREPROCESSED)/1024:.1f} KB)")

# ---------------------------------------------------------------------------
# 7. SPLIT TRAIN/TEST/VAL (70/15/15)
# ---------------------------------------------------------------------------
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Split train/test/val...")

target_col = 'culture'
feature_cols = [c for c in df_feat.columns if c != target_col]

X = df_feat[feature_cols]
y = df_feat[target_col]

# Split 1: 70% train, 30% temp
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.30, random_state=RANDOM_SEED, stratify=y
)

# Split 2: 15% val, 15% test (moitie de temp)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.50, random_state=RANDOM_SEED, stratify=y_temp
)

total = len(df_feat)
print(f"  -> Train: {len(X_train)} ({100*len(X_train)/total:.1f}%)")
print(f"  -> Val:   {len(X_val)} ({100*len(X_val)/total:.1f}%)")
print(f"  -> Test:  {len(X_test)} ({100*len(X_test)/total:.1f}%)")

splits_dir = os.path.join(SCRIPT_DIR, 'splits')
os.makedirs(splits_dir, exist_ok=True)

X_train.to_csv(os.path.join(splits_dir, 'X_train.csv'), index=False)
X_val.to_csv(os.path.join(splits_dir, 'X_val.csv'), index=False)
X_test.to_csv(os.path.join(splits_dir, 'X_test.csv'), index=False)

y_train.to_frame().reset_index(drop=False).to_csv(
    os.path.join(splits_dir, 'y_train.csv'), index=False)
y_val.to_frame().reset_index(drop=False).to_csv(
    os.path.join(splits_dir, 'y_val.csv'), index=False)
y_test.to_frame().reset_index(drop=False).to_csv(
    os.path.join(splits_dir, 'y_test.csv'), index=False)

print(f"  -> Splits sauvegardes dans {splits_dir}/")
print(f"     Fichiers: X_train.csv, X_val.csv, X_test.csv, y_train.csv, y_val.csv, y_test.csv")

# ---------------------------------------------------------------------------
# 8. RAPPORT EDA EN MARKDOWN
# ---------------------------------------------------------------------------
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Generation du rapport EDA Markdown...")

with open(RAPPORT_MD, 'w', encoding='utf-8') as f:
    f.write(f"# Rapport d Analyse Exploratoire (EDA)\n")
    f.write(f"## Projet Robot Agricole - Base de reference sol/cultures africaines\n\n")
    f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
    f.write(f"**Source:** 16 cultures africaines (FAO ECOCROP, IITA, iSDA, Kaggle)  \n\n")
    f.write("---\n\n")

    # 1. Introduction
    f.write("## 1. Introduction\n\n")
    f.write("Ce rapport presente l analyse exploratoire des donnees du projet de robot agricole. ")
    f.write("Le jeu de donnees combine:\n\n")
    f.write(f"- **Base de reference JSON:** {base_ref['metadata']['cultures_count']} cultures africaines avec ")
    f.write("plages optimales de pH, temperature, precipitation, N, P2O5, K2O et humidite\n")
    f.write(f"- **Crop_recommendation.csv:** {len(df_crop)} echantillons de sol avec N, P, K, temperature, humidite, pH, precipitation et culture associee\n")
    f.write(f"- **iSDA_soil_data.csv:** {len(df_isda):,} echantillons de sol africains reels avec proprietes chimiques (EC, N, P, K, pH, etc.)\n\n")

    # 2. Apercu
    f.write("## 2. Apercu des donnees\n\n")
    f.write(f"- **Nombre total d echantillons:** {len(df_crop)}\n")
    f.write(f"- **Nombre de caracteristiques:** {len(num_cols_present)}\n")
    f.write(f"- **Nombre de cultures:** {df_crop['culture'].nunique()}\n")
    f.write(f"- **Colonnes numeriques:** {', '.join(num_cols_present)}\n\n")

    f.write("### 2.1 Echantillons par culture\n\n")
    f.write("| Culture | Effectif | Pourcentage |\n")
    f.write("|---------|----------|-------------|\n")
    for culture, cnt in df_crop['culture'].value_counts().items():
        f.write(f"| {culture} | {cnt} | {100*cnt/len(df_crop):.1f}% |\n")

    f.write("\n### 2.2 Premieres lignes\n\n")
    f.write("```\n")
    f.write(df_crop.head().to_string())
    f.write("\n```\n\n")

    # 3. Statistiques descriptives
    f.write("## 3. Statistiques descriptives\n\n")
    f.write("### 3.1 Variables numeriques\n\n")
    f.write("```\n")
    f.write(desc_numeriques.to_string())
    f.write("\n```\n\n")

    f.write("### 3.2 Matrice de correlation\n\n")
    f.write("![Heatmap de correlation](figures/heatmap_correlation.png)\n\n")
    f.write("Interpretations:\n\n")
    corr_matrix = df_crop[num_cols_present].corr()
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            val = corr_matrix.iloc[i, j]
            col_i = corr_matrix.columns[i]
            col_j = corr_matrix.columns[j]
            if abs(val) > 0.5:
                f.write(f"- **{col_i}** et **{col_j}**: correlation de **{val:.2f}**\n")
    f.write("\n")

    # 4. Visualisations
    f.write("## 4. Visualisations\n\n")
    f.write("### 4.1 Distribution des variables\n\n")
    f.write("![Histogrammes](figures/histogrammes.png)\n\n")
    f.write("Les histogrammes montrent la distribution de chaque variable numerique avec courbe KDE.\n\n")
    f.write("### 4.2 Boxplots par culture\n\n")
    f.write("![Boxplots par culture](figures/boxplots_par_culture.png)\n\n")
    f.write("Les boxplots comparent la distribution de chaque variable entre cultures (identifie outliers et differences inter-cultures).\n\n")
    f.write("### 4.3 Pairplot\n\n")
    f.write("![Pairplot](figures/pairplot.png)\n\n")
    f.write("Relations bivariees entre variables, colorees par culture. Tendance et clusters visibles.\n\n")

    # 5. Pretraitement
    f.write("## 5. Pretraitement effectue\n\n")
    f.write("### 5.1 Normalisation (StandardScaler)\n\n")
    f.write("Colonnes normalisees: **{}**\n\n".format(', '.join(cols_to_scale)))
    f.write("- Moyenne ~ 0, ecart-type ~ 1 apres transformation\n\n")
    f.write("### 5.2 Features croisees creees\n\n")
    new_cols = [c for c in df_feat.columns if c not in df_crop.columns]
    for col in new_cols:
        if 'ratio' in col:
            parts = col.replace('ratio_', '').split('_')
            f.write(f"- **{col}**: Rapport {parts[0]}/{parts[1]}\\n")
        elif 'pH_times_EC' in col:
            f.write(f"- **{col}**: Interaction pH x Conductivite electrique\n")
        elif 'EC_approx' in col:
            f.write(f"- **{col}**: EC estimee par plus proche pH iSDA\n")
        elif 'score_NPK_balance' in col:
            f.write(f"- **{col}**: Score d equilibre NPK (0-1)\n")
        else:
            f.write(f"- **{col}**: Feature derivee\n")
    f.write("\n")

    f.write("### 5.3 Split train/test/validation\n\n")
    f.write(f"| Ensemble | Taille | Proportion |\n")
    f.write(f"|----------|--------|------------|\n")
    f.write(f"| Train | {len(X_train)} | {100*len(X_train)/total:.1f}% |\n")
    f.write(f"| Validation | {len(X_val)} | {100*len(X_val)/total:.1f}% |\n")
    f.write(f"| Test | {len(X_test)} | {100*len(X_test)/total:.1f}% |\n")
    f.write(f"| **Total** | **{total}** | **100%** |\n\n")
    f.write("Split stratifie par culture.\n\n")

    # 6. Base de reference
    f.write("## 6. Base de reference des 16 cultures africaines\n\n")
    f.write("| Culture | pH opt. | N opt. (kg/ha) | P2O5 opt. (kg/ha) | K2O opt. (kg/ha) | T min (C) | T max (C) |\n")
    f.write("|---------|---------|----------------|-------------------|-------------------|-----------|-----------|\n")
    for _, r in df_ref.iterrows():
        f.write(f"| {r['culture']} | {r['pH_optimal'] or '-'} | {r['N_optimal'] or '-'} | {r['P2O5_optimal'] or '-'} | {r['K2O_optimal'] or '-'} | {r['temperature_min'] or '-'} | {r['temperature_max'] or '-'} |\n")

    f.write("\n### Notes sur les unites\n\n")
    f.write("- P et K dans Crop_recommendation sont sous forme elementaire (P, K)\n")
    f.write("- P2O5 et K2O dans la base JSON sont sous forme oxyde (standard engrais)\n")
    f.write("- Conversion: P = P2O5 / 2.29, K = K2O / 1.205\n")
    f.write("- Les donnees iSDA sont des mesures reelles de sol africain\n\n")

    # 7. Conclusion
    f.write("## 7. Conclusion et fichiers generes\n\n")
    f.write(f"EDA portant sur {len(df_crop)} echantillons / {df_crop['culture'].nunique()} cultures. ")
    f.write(f"Dataset preprocesse: {df_feat.shape[1]} caracteristiques.\n\n")
    f.write("| Fichier | Description |\n")
    f.write("|---------|-------------|\n")
    f.write("| `dataset_preprocessed.csv` | Dataset complet features normalisees + croisees |\n")
    f.write("| `figures/histogrammes.png` | Histogrammes de toutes les variables |\n")
    f.write("| `figures/boxplots_par_culture.png` | Boxplots par culture |\n")
    f.write("| `figures/heatmap_correlation.png` | Matrice de correlation |\n")
    f.write("| `figures/pairplot.png` | Pairplot (echantillon) |\n")
    f.write("| `splits/X_train.csv` | Features train (70%) |\n")
    f.write("| `splits/X_val.csv` | Features validation (15%) |\n")
    f.write("| `splits/X_test.csv` | Features test (15%) |\n")
    f.write("| `splits/y_train.csv` | Cibles train |\n")
    f.write("| `splits/y_val.csv` | Cibles validation |\n")
    f.write("| `splits/y_test.csv` | Cibles test |\n")
    f.write("| `statistiques_descriptives.txt` | Stats descriptives detaillees |\n")
    f.write("| `rapport_eda.md` | Ce rapport |\n")

print(f"  -> Rapport EDA: {RAPPORT_MD}")

# ---------------------------------------------------------------------------
# FIN
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("EDA & PREPROCESSING TERMINE")
print(f"Sorties dans: {BASE_DIR}/")
print(f"Figures dans: {FIGURES_DIR}/")
print(f"Splits dans:  {os.path.join(SCRIPT_DIR, 'splits')}/")
print("=" * 60)
print("\nFichiers generes:")
print(f"  - {RAPPORT_TXT}")
print(f"  - {RAPPORT_MD}")
print(f"  - {PREPROCESSED}")
print(f"  - Figures (4): {FIGURES_DIR}/")
print(f"  - Splits (6): {os.path.join(SCRIPT_DIR, 'splits')}/")
print("\nExecution reussie.")
