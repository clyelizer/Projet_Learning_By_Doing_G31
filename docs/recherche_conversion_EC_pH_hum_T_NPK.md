# Synthese Recherche : Estimation N, P, K a partir de EC, pH, Humidite, Temperature
## Projet Robot Agricole - Juin 2026

================================================================================
## 1. FORMULES PEDOTRANSFERT EXISTANTES
================================================================================

### 1.1 EC -> Azote (N) : Relation Nitrate-N / Conductivite

**Source A** : Koumanov et al. (2001) - ICID Conference
- Titre : "The nitrate nitrogen – electrical conductivity relationship in non-saline soils under fertigation"
- URL : https://www.researchgate.net/publication/260157743
- Echantillons : 500 echantillons, 3 types de sol (Fluvisol, Luvisol, Vertisol)
- **Equation** : y = 84.801x² - 10.059x
  ou y = nitrate-N (mg/kg), x = EC (dS/m)
- **R = 0.88, R² = 0.78** (correlation forte)
- Limites : sols non-saline, fertigation goutte a goutte, sols bulgares

**Source B** : Mirzakhaninafchi et al. (2022) - Sensors journal
- Titre : "Development of Prediction Models for Soil Nitrogen Management Based on EC and Moisture Content"
- URL : https://www.mdpi.com/1424-8220/22/18/6728
- DOI : 10.3390/s22186728
- **Modeles N-based EC (y=EC en mS/m, x=N en kg/ha)** :

  * Sol argilo-limoneux (46% argile) : y = 0.0014x² - 0.0006x - 0.478   (R² = 0.983)
  * Sol sablo-limoneux (61% sable) : y = 0.006x - 0.322                (R² = 0.900)
  * Sol sablo-limoneux (41% limon) : y = 0.0007x² + 0.0107x + 0.208    (R² = 0.990)

- **Modeles Moisture-based EC (y=EC, x=humidite %)** :
  * Argilo-limoneux : y = -0.037x² + 0.362x - 0.306   (R² = 0.985)
  * Sablo-limoneux (61% sable) : y = -0.027x² + 0.308x - 0.264   (R² = 0.988)
  * Sablo-limoneux (41% limon) : y = -0.013x² + 0.130x - 0.11   (R² = 0.981)

- Resultats : EC augmente de 6.1% a 21.7% quand N passe de 50 a 200 kg/ha
- EC augmente de 83.87% a 111% quand humidite passe de 13% a 22%
- Gamme N testee : 0-200 kg/ha (uree 46% N)
- Limites : 3 types de sol seulement, pas de pH dans l'etude

**Source C** : Shin et al. (2026) - Agriculture MDPI
- Titre : "Evaluation of Sensor-Based Soil EC Responses to N and K Fertilization"
- URL : https://www.mdpi.com/2077-0472/16/2/137
- EC augmente LINEAIREMENT de 25% a 125% du taux de fertilisation
- Au-dela de 150% : modele de saturation non-lineaire mieux adapte
- Correlation forte EC avec NH4+-N (ion dominant de l'hydrolyse de l'uree)
- Capteur TEROS 12, sol sablo-limoneux (20.8% sable, 69.2% limon, 10% argile)

### 1.2 pH -> Phosphore (P) : Relation connue

- **Optimum disponibilite P : pH 6.0 - 7.0** (MSU, Cropnuts, MU Extension)
- Fixation maximale du P a pH 4.0 et 5.5 (precipitation avec Fe et Al)
- Fixation a pH 8.0+ (precipitation avec Ca)
- **Source** : https://www.canr.msu.edu/news/the_peaks_and_valleys_of_phosphorus_fixation
- Langmuir adsorption models : R² = 0.955-0.999 pour adsorption P (Tsegede study)
- Adsorption maxima : 357 a 2500 mg P/kg sol selon acidite
- **Source** : https://link.springer.com/article/10.1007/s44378-026-00190-4

### 1.3 ECe (sature) prediction from EC 1:5 (Pedotransfert Europeen)

- Titre : "Empirical estimation of saturated soil-paste EC in the EU using PTFs and Quantile Regression Forests"
- URL : https://www.sciencedirect.com/science/article/pii/S0016706125000370
- Dataset : LUCAS 2018, ~20,000 echantillons
- **R² = 0.302, RMSE = 0.265 dS/m** (modele Quantile Regression Forest)
- Utilise texture et carbone organique du sol en entree
- Limites : R² faible, specifique aux sols europeens

### 1.4 PTFs pour ECe en Tunisie (5 fonctions)

- Titre : "Predicting Soil EC of Saturated Paste Extract Using PTFs in NE Tunisia"
- URL : https://www.mdpi.com/2071-1050/17/20/9177
- **Performances** :
  * PTF1 (regression simple) : R² = 0.85
  * PTF2 (stepwise) : R² = 0.71
  * PTF3 : R² = 0.84
  * PTF4 (Lasso/Ridge) : **R² = 0.89**
  * PTF5 : R² = 0.83
- Entrees : texture, pH, carbone organique, N total, CEC, EC 1:5

================================================================================
## 2. MODELES ML SPECIFIQUES POUR ESTIMATION NPK
================================================================================

### 2.1 Random Forest Regressor + 4 autres modeles (Embedded Microsystem)

**Source** : Dattatreya et al. (2025) - Microsystem Technologies
- URL : https://link.springer.com/article/10.1007/s00542-025-05947-5
- **Entrees : EC, Temperature, pH, Humidite**
- **Sorties : N, P, K predits**
- **Dataset : 6,765 echantillons** (collecte terrain multi-sites)
- **Resultats** :
  * RFR (Random Forest Regressor) : **R² > 0.995**
  * GBR (Gradient Boosting Regressor) : **R² > 0.995**
  * SVM : **R² > 0.995**
  * KNN : **R² > 0.995**
  * Linear Regression : **R² > 0.995**
- Materiel : Raspberry Pi 5 + capteur multi-parametres
- Deploiement : FastAPI inference engine (edge, sans cloud)
- Dashboard : Node-RED pour visualisation temps reel
- Limites : Donnees non publiques (disponibles sur demande raisonnable)

### 2.2 Random Forest et Neural Network (solutions synthetiques)

**Source** : Kumar et al. (2025) - arXiv
- URL : https://arxiv.org/abs/2504.04138
- Dataset : solutions synthetiques avec conductivite et pH
- **Resultats** :
  * Random Forest : erreur P = **23.6%**, erreur K = **16%**
  * Neural Network : erreur P = **26.3%**, erreur K = **21.8%**
- Limites : solutions synthetiques, pas de sol reel, pas de N

### 2.3 XGBoost pour recommandation culture (NPK + pH + climat)

**Source** : Dey et al. (2024) - Heliyon
- URL : https://www.sciencedirect.com/science/article/pii/S2405844024011435
- Dataset : Kaggle, cultures agricoles + horticoles
- **Precision XGBoost** :
  * Cultures agricoles : **99.09%** (AUC 1.0)
  * Cultures horticoles : **99.3%** (AUC 1.0)
  * Combinaison : **98.51%** (AUC 0.99)
- Entrees : N, P, K, pH, temperature, humidite, rainfall
- Comparaison avec : SVM, Random Forest, KNN, Decision Tree

### 2.4 CatBoost et Random Forest pour NPK IoT

**Source** : Islam et al. (2023) - Journal of Agriculture and Food Research
- URL : https://www.sciencedirect.com/science/article/pii/S2666154323003873
- **Crop Recommendation (CatBoost)** : Precision **97.5%**, F1 **97.5%**
- **Fertilizer Prediction (RF + GridSearch)** : Precision **99.56%**, F1 **100%**
- Dataset : 2299 enregistrements, 22 cultures, 7 features
- Capteurs : JXBS-3001 (NPK), FC-28 (humidite), DHT11 (temp/humidite air)
- Protocole : MQTT vers cloud, app mobile Flutter
- Limites : pH elimine par test Chi-2 (score 74.88 vs autres >1000)

================================================================================
## 3. CORRELATIONS CONNUES
================================================================================

### 3.1 EC - Azote (correlations)

| Etude | Correlation | Details |
|-------|-------------|---------|
| Koumanov et al. 2001 | **R² = 0.78** (R=0.88) | 500 echant., 3 sols |
| Mirzakhaninafchi 2022 | **R² = 0.900-0.990** | N 0-200 kg/ha |
| USDA NRCS | EC correlee a nitrates, K, Na, Cl, sulfate, ammoniac | Guide educators |
| Shin et al. 2026 | Lineaire 25-125% taux, saturation >150% | TEROS 12 sensor |

### 3.2 pH - Phosphore (relation etablie)

- **Disponibilite P optimale : pH 6.0-7.0** (vallee de fixation minimale)
- pH < 5.5 : P precipite avec Fe et Al (fixation forte)
- pH > 8.0 : P precipite avec Ca (fixation moyenne)
- **Source multiple** : MSU Extension, Cropnuts, MU Extension
- **Conversion pH(salt) -> pH(water)** : pH(water) = 0.684 + 0.9573 x pH(salt) (MU Lab)

### 3.3 EC - Potassium

- Mazur et al. (2022) : EC vs K : **r = 0.8**
- Shin et al. (2026) : EC lineaire avec K applique (KCl) de 25-125%
- **Source** : https://www.mdpi.com/2077-0472/12/6/883 (Agriculture MDPI)

### 3.4 Humidite - Effet sur disponibilite nutriments

- **Azote** : Mineralisation nette N suit modele Q10 (double par +10°C)
  * Sensibilite maximale a 25°C
  * Humidite optimale : 80-100% de la capacite au champ
  * **Source** : Guntinas et al. (2012) - https://www.sciencedirect.com/science/article/abs/pii/S1164556311000732
  * Cite 518 fois

- **Effet general** :
  * Humidite adequate = distribution uniforme des nutriments
  * Secheresse = imbalances localises
  * Exces d'eau = lessivage (N surtout) et conditions anaerobiques
  * **Source** : https://www.internationalscholarsjournals.com/articles/soil-moisture-influence-on-nutrient-availability-in-the-soil.pdf

### 3.5 Temperature - Effet sur disponibilite N

- Mineralisation N : taux double par +10°C (Q10 model, Stanford & Smith 1972)
- Optimum : ~25-35°C pour activite microbienne
- Temperature > 35°C : activite microbienne decline
- Source : Guntinas et al. 2012

================================================================================
## 4. GUIDES FAO / IITA / CIRAD
================================================================================

### 4.1 FAO
- Guide FAO "Fertilizer and Plant Nutrition Bulletin" : https://www.fao.org/4/a0443e/a0443e.pdf
  * Approche Integrated Plant Nutrition System (IPNS)
  * Pas de formule directe EC->NPK

- FAO SoilFER Programme (MIR spectroscopy) : https://www.fao.org/americas/news/news-detail/new-technology-to-monitor-soil-fertility/en
  * Technologie MIR spectroscopie pour analyse rapide
  * Formations Ghana, Guatemala, Honduras, Kenya, Zambia en 2026

### 4.2 IITA
- **Open Soil Data** : Dataset 49,225 echantillons (iSDA Africa)
  * URL donnees : https://isdasoil.s3.us-west-2.amazonaws.com/soil_analysis_data/latest/iSDA_soil_data.csv
  * DOI : 10.17605/OSF.IO/A69R5
  * Proprietes : N.tot (g/kg), P (mg/kg), K (mg/kg), pH.H2O, etc.
  * Resolution spatiale : 30m pour toute l'Afrique
  * Reference : Hengl et al. (2021) Scientific Reports 11:6130
  * https://doi.org/10.1038/s41598-021-85639-y

- **Soil Information System for Africa (Soils4Africa)** : https://www.iita.org/iita-project/soil-information-system-for-africa-soils4africa/

- **IITA Soil analyses dataset** : https://data.iita.org/dataset/soil-analyses (Cameroun)

### 4.3 CIRAD / Autres
- Pas de guide specifique CIRAD trouve pour estimation NPK par capteurs
- Methodes conventionnelles recommandees : analyse chimique (Kjeldahl pour N, Olsen pour P)
- Approche conventionnelle toujours reference pour calibration

================================================================================
## 5. APPROCHES CAPTEURS (HARDWARE)
================================================================================

### 5.1 Capteurs 7-en-1 disponibles commercialement

| Capteur | Mesures | Prix | Interface |
|---------|---------|------|-----------|
| ComWinTop CWT-Soil | T, humidite, EC, pH, N, P, K | ~$49-110 | RS485, USB |
| DFRobot SEN0605 | N, P, K (0-199 mg/kg) | ~$40-60 | RS485 Modbus |
| Renkeer 7-in-1 | T, humidite, pH, EC, N, P, K | ~$80-120 | RS485 |
| Faranux COM12 | T, humidite, EC, pH, N, P, K | ~$30-50 | RS485 |

- **IMPORTANT** : Tous les fabricants precisent : "data is reference only, not professional-grade accurate"
  et "The existing electronic measuring method cannot accurately measure NPK, the error is big"
- **Precision** : ±2%, resolution 1 mg/kg (selon fabricants)
- **Protocole** : MODBUS-RTU sur RS485

### 5.2 Carte Kaggle "Crop Recommendation Dataset"
- URL : https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset
- **2200 enregistrements**, 22 cultures
- **Features** : N, P, K, temperature, humidite, pH, rainfall
- **Source** : https://github.com/nileshiq/Crop-Recommendation
- Egalement : https://www.kaggle.com/datasets/manikantasanjayv/crop-recommender-dataset-with-soil-nutrients
  avec EC en dS/m, S, Cu, Fe, Mn, Zn, B en plus

### 5.3 Carte Kaggle "crops-npk data set"
- URL : https://www.kaggle.com/datasets/javakhan/crops-npk-data-set
- **20,000 enregistrements** (simulation/sensor)
- Features : N, P, K, temperature, humidite, pH, rainfall, soil_type, variety
- License MIT

### 5.4 Systemes IoT existants
- **Terrafarms** (ESP32 + pH + humidite + TDS + NPK) : https://github.com/Terrafarms/bangkit-internet-of-things
- **MoniCrop** (RPi4 + NPK 7-en-1 + ultrason) : https://github.com/topics/npk-sensor
- **Real-Time Crop Prediction** (Arduino + NPK + DHT11) : https://link.springer.com/article/10.1007/s40009-025-01857-2

### 5.5 Schema d'architecture recommande pour le robot
```
Capteurs (EC, pH, T, humidite)
       |
   [ESP32 / Arduino / RPi5]
       |
   Modele ML entraine (RFR/GBR)  <-- iSDA + Kaggle datasets
       |
   Prediction N, P, K (mg/kg ou kg/ha)
       |
   Application / Dashboard
```

================================================================================
## 6. RECOMMENDATIONS PRATIQUES POUR LE PROJET
================================================================================

### 6.1 Approche recommandee
1. **Collecte donnees** : Capteur 7-en-1 (EC, pH, T, humidite) pour features d'entree
2. **Dataset entrainement** : Combiner iSDA Africa (~49K echantillons avec pH, K, N.tot, P)
   + Kaggle CropRec (2200 enreg avec N, P, K, T, humidite, pH, rainfall)
   + Kaggle crops-npk (20000 enreg)
3. **Modele ML** : Random Forest Regressor ou Gradient Boosting -- R² > 0.995 demontre
4. **Conversion kg/ha** : 1 ppm = 2 kg/ha (pour couche 0-15cm, densite 1.33 g/cm3)

### 6.2 Formules pedotransfert utilisables directement
- **N (mg/kg) a partir de EC (dS/m)** : y = 84.801x² - 10.059x (Koumanov)
  * ATTENTION : valable pour sols non-saline, R²=0.78
- **P a partir de pH** : regle qualitative (optimum pH 6.0-7.0)
- **K a partir de EC** : r=0.8 avec EC (Mazur et al.)

### 6.3 Points critiques
- Les capteurs NPK directs (sonde 5 broches) ont une **erreur importante** -- les fabricants le disent
- L'approche ML avec EC+pH+T+humidite comme features et NPK comme target est **mieux validee scientifiquement**
- R² > 0.995 demontre dans la litterature recente (Dattatreya 2025)
- Necessite **calibration locale** : les relations varient selon type de sol

### 6.4 Jeux de donnees disponibles
| Dataset | Taille | Features | URL |
|---------|--------|----------|-----|
| iSDA Africa | 49,225 | N.tot, P, K, pH, EC?, texture | https://isdasoil.s3.us-west-2.amazonaws.com/ (via DOI) |
| Kaggle CropRec | 2,200 | N, P, K, T, hum, pH, rain | https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset |
| Kaggle crops-npk | 20,000 | N, P, K, T, hum, pH, rain, soil | https://www.kaggle.com/datasets/javakhan/crops-npk-data-set |
| Kaggle SoilNutrients | ~620 | N, P, K, pH, EC, S, Cu, Fe, Mn, Zn, B | https://www.kaggle.com/datasets/manikantasanjayv/crop-recommender-dataset-with-soil-nutrients |
| LUCAS Europe | ~20,000 | EC, pH, texture, OC, N | LUCAS 2018 survey |
| Tunisie PTFs | ~200? | EC, pH, texture, OC, CEC, N | MDPI Sustainability 2025 |

================================================================================
## 7. REFERENCES CLES (avec DOI)
================================================================================

1. Hengl et al. (2021) - African soil properties at 30m - Sci Rep 11:6130
   DOI: 10.1038/s41598-021-85639-y

2. Mirzakhaninafchi et al. (2022) - EC-N models Sensors 22:6728
   DOI: 10.3390/s22186728

3. Dattatreya et al. (2025) - Embedded ML NPK prediction - Microsys Tech 31:3903
   DOI: 10.1007/s00542-025-05947-5

4. Koumanov et al. (2001) - Nitrate-N / EC relationship - ICID Conf.
   ResearchGate: 260157743

5. Shin et al. (2026) - EC sensors for N,K - Agriculture 16(2):137
   DOI: 10.3390/agriculture16020137

6. Kumar et al. (2025) - ML from synthetic solutions - arXiv:2504.04138

7. Dey et al. (2024) - XGBoost crop recommendation - Heliyon 10:e25112
   DOI: 10.1016/j.heliyon.2024.e25112

8. Islam et al. (2023) - ML IoT NPK system - J Agric Food Res 14:100880
   DOI: 10.1016/j.jafr.2023.100880

9. Guntinas et al. (2012) - Moisture/Temp on N mineralization - EJSoilBiol 48:73
   DOI: 10.1016/j.ejsobi.2011.07.007

10. Cheema & Pires (2025) - AIoT soil nutrient analysis - SmartAgriTech 11:100924
    DOI: 10.1016/j.atech.2025.100924
