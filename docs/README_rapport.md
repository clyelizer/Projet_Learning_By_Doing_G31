# Robot Agricole Intelligent - Projet

## Description
Systeme de recommandation de cultures agricoles base sur 4 mesures de sol (EC, pH, humidite, temperature) mesurees par un robot. Estimation de N, P, K via formules pedotransfert, puis classement des cultures adaptees avec SHAP.

## Etat actuel (2026-06-18)

### ✓ Fait
- [x] Base de reference agricole : **41 cultures** (16 africaines + 25 mondiales)
- [x] Formules pedotransfert sophistiquees (Mirzakhaninafchi R²=0.99, Koumanov R²=0.78, Mazur r=0.8)
- [x] Dashboard Streamlit 4 pages avec SHAP integre dans Recommandation
- [x] Classifieur simplifie 6 features (N,P,K,pH,T,humidite) — RF 100% accuracy
- [x] SHAP waterfall plot dans la page Recommandation pour expliquer la prediction
- [x] Modeles ML entrainés : Random Forest + XGBoost (classifieurs et regresseurs NPK)
- [x] Pipeline ML complet (EDA, preprocessing, entrainement, XAI)

### 🔄 En cours
- [ ] Deploiement ngrok pour acces mobile
- [ ] Capteur NPK direct (RS485 Modbus) pour validation croisee
- [ ] Integration temps reel Bluetooth/ESP32

### 📅 A faire
- [ ] Calibration terrain : comparer estimations avec analyses labo reelles
- [ ] Modele Dattatreya 2025 (R²>0.995) avec EC, pH, T, humidite -> N, P, K
- [ ] Schema electronique ESP32 + capteurs 7-en-1
- [ ] Code embarque pour le robot
- [ ] Export PDF des recommandations
- [ ] Capteur NPK direct (RS485 Modbus) pour validation croisee
- [ ] Integration temps reel Bluetooth/ESP32

## Structure des fichiers

```
/home/coulibaly/Bureau/rapport/
├── README.md                          <- Ce fichier
├── dashboard.py                       <- Dashboard Streamlit
├── base_reference_agricole.json       <- Base 41 cultures
├── dataset_preprocessed.csv           <- Dataset normalise
├── plan_pipeline_ML.md                <- Plan du pipeline
├── synthese_phase1_sources_agricoles.md  <- Sources FAO/ECOCROP
├── recherche_conversion_EC_pH_hum_T_NPK.md  <- Formules pedotransfert
├── eda_preprocessing.py               <- EDA + preprocessing
├── train_rapide.py                    <- Entrainement modeles
├── xai_simple.py                      <- Explicabilite (SHAP, arbre)
├── recommendation_ranking.py          <- Classement cultures
├── metriques.txt                      <- Metriques modeles
├── modeles/                           <- Modeles .pkl
│   ├── random_forest.pkl
│   ├── xgboost.pkl
│   ├── scaler.pkl / scaler_npk.pkl / scaler_classification.pkl
│   ├── label_encoder.pkl / label_encoder_culture.pkl
│   └── regressor_N.pkl / regressor_P.pkl / regressor_K.pkl
└── figures/                           <- Graphiques generes
    ├── confusion_matrix.png
    ├── feature_importance.png
    ├── decision_tree.png
    └── regression_N.png / P.png / K.png
```

## Mesures Robot -> Estimation NPK

| Mesure robot | Unite | -> | Parametre estime | Formule | Source | R² |
|---|---|---|---|---|---|---|
| EC | dS/m | -> | N (mg/kg) | N = 84.801×EC² - 10.059×EC | Koumanov 2001 | 0.78 |
| pH | - | -> | P (mg/kg) | Optimum pH 6.0-7.0, decroissance lineaire | MSU Extension | qualitatif |
| EC | dS/m | -> | K (mg/kg) | K = 15 + 80×EC | Mazur 2022 | r=0.8 |

Conversion : P2O5 = P×2.29, K2O = K×1.205 (formes engrais standard)

## Utilisation

```bash
# Lancer le dashboard
streamlit run /home/coulibaly/Bureau/rapport/dashboard.py

# Re-entrainer les modeles
python3 /home/coulibaly/Bureau/rapport/train_rapide.py
```

## References cles

1. Dattatreya et al. 2025 - Embedded ML NPK - Microsys Tech, DOI: 10.1007/s00542-025-05947-5
2. Mirzakhaninafchi et al. 2022 - EC-N models - Sensors 22:6728, DOI: 10.3390/s22186728
3. Koumanov et al. 2001 - Nitrate-N/EC - ICID Conf, ResearchGate: 260157743
4. Hengl et al. 2021 - African soil properties - Sci Rep 11:6130
5. Mazur et al. 2022 - EC vs K - Agriculture MDPI, DOI: 10.3390/agriculture12060883
