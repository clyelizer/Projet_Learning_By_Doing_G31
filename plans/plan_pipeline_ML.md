# Pipeline ML : De l exploration de la base a l explicabilite

## Contexte

Robot agricole mesurant EC, pH, humidite, temperature.
Base de reference construite : 16 cultures africaines avec pH, T, precip, N, P2O5, K2O, humidite.
Objectif : predire la culture recommandee et les besoins en fertilisation a partir des mesures.

---

## Phase 1 : Exploration des donnees (EDA)

### 1.1 Chargement et nettoyage

- Charger la base JSON (base_reference_agricole.json)
- Charger les datasets bruts :
  - Crop_recommendation.csv (Kaggle, 1700 enreg., 8 colonnes)
  - iSDA_soil_data.csv (49000 echantillons sol africains reels)
- Normaliser les colonnes : pH, temperature, humidite, precip, N, P, K
- Gerer les valeurs manquantes (EC, MO, humidite pour 8 cultures)

### 1.2 Statistiques descriptives

- Distributions de chaque variable (pH, N, P, K, temperature, humidite)
- Plages, moyennes, ecarts types par culture
- Matrice de correlation entre variables
- Detection des outliers

### 1.3 Visualisations

- Histogrammes par variable
- Boxplots par culture (pH, N, P, K pour chaque culture)
- Pairplot des variables continues
- Heatmap de correlation
- Distribution geographique (iSDA Africa)
- Carte de chaleur pH vs culture

### 1.4 Analyse des desequilibres

- Equilibre des classes (nombre d echantillons par culture)
- Sur-representation de certaines cultures
- Strategies de reechantillonnage si necessaire

### 1.5 Feature engineering

- A partir des 4 mesures robot (EC, pH, humidite, temperature) :
  - Estimer N, P, K via formules d approximation
  - Creer des features croisees (pH*EC, N/P, N/K, etc.)
  - Ratios NPK
- Normalisation/Standardisation des features

---

## Phase 2 : Modelisation

### 2.1 Preprocessing

- Split train/test/validation (70/15/15)
- StandardScaler ou MinMaxScaler
- Encodage des cultures (LabelEncoder ou OneHot)

### 2.2 Modeles de classification (recommander la culture)

| Modele | Justification |
|--------|--------------|
| **Random Forest** | Robuste, gere les non-linearites, importance des features |
| **XGBoost** | Performant, gestion des valeurs manquantes |
| **LightGBM** | Rapide, bonne precision |
| **KNN** | Simple, interpretable (basé sur similarité des sols) |
| **SVM** | Bon pour separations complexes |
| **Reseau de neurones** | Pour comparaison (si donnees suffisantes) |

### 2.3 Modeles de regression (estimer fertilisation N, P, K)

- Regression lineaire multiple
- Random Forest Regressor
- XGBoost Regressor
- SVR

### 2.4 Entrainement

- Validation croisee (5-fold)
- GridSearchCV / RandomizedSearchCV pour l optimisation des hyperparametres
- Early stopping pour XGBoost/LightGBM
- Suivi avec MLflow ou W&B (optionnel)

### 2.5 Metriques

**Classification :**
- Accuracy, Precision, Recall, F1-score
- Matrice de confusion
- Courbe ROC / AUC

**Regression :**
- RMSE, MAE, R2
- Erreur relative par culture

---

## Phase 3 : Explicabilite (XAI)

### 3.1 Importance des features

- **Random Forest/XGBoost** : feature_importances_ integrees
- **Permutation importance** : quel impact si on melange une variable ?
- **SHAP** : explications locales et globales

### 3.2 SHAP (SHapley Additive exPlanations)

- SHAP summary plot : quelles variables influencent le plus chaque culture ?
- SHAP dependence plot : comment le pH influence la prediction du mais ?
- SHAP waterfall : explication individuelle pour une mesure donnee
- SHAP force plot : visualisation interactive

### 3.3 LIME (Local Interpretable Model-agnostic Explanations)

- Explications locales : pourquoi cette mesure precise a donne cette recommandation ?
- Ideal pour l interface utilisateur du robot

### 3.4 Arbre de decision interpretable

- Entrainer un petit arbre de decision (profondeur 3-4)
- Visualisation graphique
- Regles comprehensibles : "Si pH entre 5 et 7 ET N > 80 alors Mais recommande"

### 3.5 Counterfactual explanations

- "Si le pH etait de 6.5 au lieu de 5.0, la culture recommandee serait le Coton"
- Utilite pour l agriculteur : que modifier pour changer de culture ?

### 3.6 Dashboard d explication

- Interface web simple (Streamlit ou Gradio)
- Inputs : EC, pH, humidite, temperature
- Outputs :
  - Culture recommandee (avec probabilites)
  - Fertilisation N, P, K recommandee
  - Explication SHAP/LIME (pourquoi cette recommendation)
  - Visualisation interactive

---

## Phase 4 : Integration robot

### 4.1 Pipeline de prediction

```python
mesures = {"EC": 0.5, "pH": 6.2, "humidite": 65, "temperature": 28}

# 1. Estimer N, P, K via ML
npk_predits = modele_npk.predict(mesures)

# 2. Recomposer le profil complet
profil = {**mesures, **npk_predits}

# 3. Predire la culture recommandee
culture = modele_culture.predict(profil)

# 4. Expliquer la decision
explication = explainer.shap_values(profil, culture)

# 5. Generer les recommandations
recommandations = generer_recommandations(culture, profil)
```

### 4.2 Format de sortie

```json
{
  "mesures_robot": {"EC": 0.5, "pH": 6.2, "humidite": 65, "temperature": 28},
  "estimation_NPK": {"N": 85, "P": 35, "K": 20},
  "culture_recommandee": {"nom": "Mais", "probabilite": 0.87},
  "autres_cultures_possibles": [
    {"nom": "Sorgho", "probabilite": 0.08},
    {"nom": "Mil", "probabilite": 0.04}
  ],
  "fertilisation": {
    "N": "80-120 kg/ha", "P2O5": "30-60 kg/ha", "K2O": "25-60 kg/ha"
  },
  "explication": {
    "facteurs_clefs": ["pH (6.2, optimal pour Mais)", "N (estime 85)"],
    "shap_values": {...}
  }
}
```

---

## Phase 5 : Deploiement

### 5.1 Sauvegarde des modeles

- joblib/pickle pour les modeles sklearn
- ONNX pour modele neuronal
- Enregistrement avec MLflow (optionnel)

### 5.2 API de prediction

- FastAPI ou Flask
- Endpoint /predict : input mesures robot, output recommandations
- Endpoint /explain : input mesures, output explication SHAP
- Endpoint /cultures : liste des cultures dans la base

### 5.3 Interface utilisateur

- Streamlit / Gradio / HTML simple
- Dashboard avec sliders pour les entrees
- Affichage des cartes de sol (geolocalisation optionnelle)
- Export PDF des recommandations

---

## Livrables finaux

| Livrable | Format | Description |
|----------|--------|-------------|
| Rapport EDA | HTML/PDF | Analyses et visualisations |
| Notebook EDA | .ipynb | Exploration interactive |
| Modeles entrainés | .pkl/.joblib | Random Forest, XGBoost, etc. |
| API de prediction | .py | FastAPI |
| Dashboard | .py | Streamlit |
| Documentation | .md | README, API docs |

---

## Technologies proposees

| Technologie | Usage |
|-------------|-------|
| Python 3.10+ | Langage principal |
| pandas, numpy | Manipulation donnees |
| matplotlib, seaborn, plotly | Visualisations |
| scikit-learn | Modeles, preprocessing, metriques |
| xgboost, lightgbm | Gradient boosting |
| shap, lime | Explicabilite |
| streamlit | Dashboard |
| fastapi | API |
| joblib | Sauvegarde modeles |

---

## Ordre d execution

1. EDA (exploration)
2. Preprocessing et feature engineering
3. Modeles classification
4. Modeles regression NPK
5. Explicabilite (SHAP, LIME)
6. Dashboard Streamlit
7. API FastAPI
8. Tests et validation finale
