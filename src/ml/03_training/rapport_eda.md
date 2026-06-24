# Rapport d Analyse Exploratoire (EDA)
## Projet Robot Agricole - Base de reference sol/cultures africaines

**Date:** 2026-06-18 06:57:54  
**Source:** 16 cultures africaines (FAO ECOCROP, IITA, iSDA, Kaggle)  

---

## 1. Introduction

Ce rapport presente l analyse exploratoire des donnees du projet de robot agricole. Le jeu de donnees combine:

- **Base de reference JSON:** 41 cultures africaines avec plages optimales de pH, temperature, precipitation, N, P2O5, K2O et humidite
- **Crop_recommendation.csv:** 1697 echantillons de sol avec N, P, K, temperature, humidite, pH, precipitation et culture associee
- **iSDA_soil_data.csv:** 49,225 echantillons de sol africains reels avec proprietes chimiques (EC, N, P, K, pH, etc.)

## 2. Apercu des donnees

- **Nombre total d echantillons:** 1697
- **Nombre de caracteristiques:** 7
- **Nombre de cultures:** 15
- **Colonnes numeriques:** N, P, K, temperature, humidite, pH, precipitation

### 2.1 Echantillons par culture

| Culture | Effectif | Pourcentage |
|---------|----------|-------------|
| rice | 139 | 8.2% |
| Soyabeans | 130 | 7.7% |
| banana | 130 | 7.7% |
| beans | 125 | 7.4% |
| cowpeas | 122 | 7.2% |
| orange | 122 | 7.2% |
| maize | 119 | 7.0% |
| coffee | 110 | 6.5% |
| peas | 100 | 5.9% |
| groundnuts | 100 | 5.9% |
| mango | 100 | 5.9% |
| grapes | 100 | 5.9% |
| watermelon | 100 | 5.9% |
| apple | 100 | 5.9% |
| cotton | 100 | 5.9% |

### 2.2 Premieres lignes

```
    N   P   K  temperature   humidite        pH  precipitation culture
0  90  42  43    20.879744  82.002744  6.502985     202.935536    rice
1  85  58  41    21.770462  80.319644  7.038096     226.655537    rice
2  60  55  44    23.004459  82.320763  7.840207     263.964248    rice
3  74  35  40    26.491096  80.158363  6.980401     242.864034    rice
4  78  42  42    20.130175  81.604873  7.628473     262.717340    rice
```

## 3. Statistiques descriptives

### 3.1 Variables numeriques

```
              N         P         K  temperature  humidite        pH  precipitation
count  1697.000  1697.000  1697.000     1697.000  1697.000  1697.000       1697.000
mean     52.647    58.126    52.031       24.712    65.849     6.439         99.365
std      38.537    34.164    57.069        4.910    24.433     0.870         50.436
min       0.000     5.000     5.000        8.826    14.258     3.505          5.315
25%      21.000    36.000    19.000       21.631    51.279     5.861         66.839
50%      37.000    54.000    27.000       24.910    77.906     6.354         93.123
75%      90.000    72.000    52.000       27.835    83.856     6.933        115.356
max     140.000   145.000   205.000       41.949    94.964     9.935        298.560
```

### 3.2 Matrice de correlation

![Heatmap de correlation](figures/heatmap_correlation.png)

Interpretations:

- **P** et **K**: correlation de **0.82**

## 4. Visualisations

### 4.1 Distribution des variables

![Histogrammes](figures/histogrammes.png)

Les histogrammes montrent la distribution de chaque variable numerique avec courbe KDE.

### 4.2 Boxplots par culture

![Boxplots par culture](figures/boxplots_par_culture.png)

Les boxplots comparent la distribution de chaque variable entre cultures (identifie outliers et differences inter-cultures).

### 4.3 Pairplot

![Pairplot](figures/pairplot.png)

Relations bivariees entre variables, colorees par culture. Tendance et clusters visibles.

## 5. Pretraitement effectue

### 5.1 Normalisation (StandardScaler)

Colonnes normalisees: **N, P, K, pH, temperature, humidite**

- Moyenne ~ 0, ecart-type ~ 1 apres transformation

### 5.2 Features croisees creees

- **ratio_N_P**: Rapport N/P\n- **ratio_N_K**: Rapport N/K\n- **ratio_P_K**: Rapport P/K\n- **score_NPK_balance**: Score d equilibre NPK (0-1)
- **EC_approx**: EC estimee par plus proche pH iSDA
- **pH_times_EC**: Interaction pH x Conductivite electrique

### 5.3 Split train/test/validation

| Ensemble | Taille | Proportion |
|----------|--------|------------|
| Train | 1187 | 69.9% |
| Validation | 255 | 15.0% |
| Test | 255 | 15.0% |
| **Total** | **1697** | **100%** |

Split stratifie par culture.

## 6. Base de reference des 16 cultures africaines

| Culture | pH opt. | N opt. (kg/ha) | P2O5 opt. (kg/ha) | K2O opt. (kg/ha) | T min (C) | T max (C) |
|---------|---------|----------------|-------------------|-------------------|-----------|-----------|
| Arachide | 6.0 | 22 | 40 | 42 | 22.0 | 32 |
| Banane plantain | 6.2 | 300 | 50 | 400 | 20.0 | 35 |
| Cacao | 5.8 | 90 | 25 | 75 | 21.0 | 32 |
| Cafe | 6.2 | 200 | 60 | 185 | 14.0 | 28 |
| Coton | 6.3 | 105 | 35 | 65 | 22.0 | 36 |
| Fonio | 6.0 | 20 | 15 | 10 | 22.0 | 27 |
| Haricot | 6.5 | 45 | 50 | 30 | 16.0 | 25 |
| Igname | 6.1 | 95 | 35 | 110 | 18.0 | 32 |
| Mais | 6.0 | 100 | 45 | 42 | 16.0 | 33 |
| Manioc | 6.8 | 104 | 45 | 105 | 20.0 | 29 |
| Mil | 5.8 | 45 | 22 | 22 | 25.0 | 35 |
| Niebe | 6.5 | 25 | 38 | 25 | 20.0 | 35 |
| Patate douce | 6.0 | 90 | 80 | 160 | 18.0 | 28 |
| Riz | 6.5 | 90 | 45 | 45 | 20.0 | 35 |
| Sesame | 6.5 | 52 | 42 | 30 | 20.0 | 30 |
| Sorgho | 6.5 | 105 | 40 | 35 | 22.0 | 35 |
| Soja | 7.43 | 40 | 155 | 96 | 17.0 | 21 |
| Pomme | 6.0 | 20 | 304 | 241 | 21.0 | 24 |
| Raisin | 6.0 | 20 | 304 | 241 | 8.8 | 42 |
| Mangue | 5.74 | 20 | 63 | 36 | 27.0 | 36 |
| Orange | 7.0 | 20 | 40 | 12 | 10.0 | 35 |
| Pois | 6.0 | 20 | 155 | 24 | 18.0 | 37 |
| Pasteque | 6.48 | 100 | 40 | 60 | 24.0 | 27 |
| Banane dessert | 5.5 | 100 | 189 | 60 | 25.0 | 30 |
| Ble | 6.8 | 115 | 65 | 60 | 15.0 | 24 |
| Tomate | 6.2 | 140 | 80 | 200 | 18.0 | 28 |
| Oignon | 6.4 | 90 | 60 | 115 | 13.0 | 24 |
| Carotte | 6.0 | 80 | 65 | 140 | 15.0 | 22 |
| Chou | 6.5 | 160 | 80 | 150 | 15.0 | 20 |
| Canne a sucre | 6.5 | 225 | 90 | 185 | 25.0 | 35 |
| Palmier a huile | 5.5 | 150 | 75 | 275 | 24.0 | 30 |
| Ananas | 5.0 | 150 | 60 | 225 | 22.0 | 30 |
| Papaye | 6.2 | 200 | 80 | 200 | 22.0 | 30 |
| Avocat | 6.2 | 150 | 65 | 150 | 20.0 | 28 |
| Poivron | 6.2 | 125 | 65 | 175 | 20.0 | 28 |
| Concombre | 6.2 | 100 | 65 | 125 | 20.0 | 28 |
| Aubergine | 6.0 | 140 | 80 | 200 | 22.0 | 30 |
| Laitue | 6.5 | 80 | 50 | 125 | 10.0 | 20 |
| Fraise | 6.0 | 100 | 65 | 150 | 15.0 | 22 |
| Haricot vert | 6.5 | 30 | 50 | 60 | 18.0 | 25 |
| Gombo | 6.4 | 100 | 60 | 115 | 24.0 | 30 |

### Notes sur les unites

- P et K dans Crop_recommendation sont sous forme elementaire (P, K)
- P2O5 et K2O dans la base JSON sont sous forme oxyde (standard engrais)
- Conversion: P = P2O5 / 2.29, K = K2O / 1.205
- Les donnees iSDA sont des mesures reelles de sol africain

## 7. Conclusion et fichiers generes

EDA portant sur 1697 echantillons / 15 cultures. Dataset preprocesse: 14 caracteristiques.

| Fichier | Description |
|---------|-------------|
| `dataset_preprocessed.csv` | Dataset complet features normalisees + croisees |
| `figures/histogrammes.png` | Histogrammes de toutes les variables |
| `figures/boxplots_par_culture.png` | Boxplots par culture |
| `figures/heatmap_correlation.png` | Matrice de correlation |
| `figures/pairplot.png` | Pairplot (echantillon) |
| `splits/X_train.csv` | Features train (70%) |
| `splits/X_val.csv` | Features validation (15%) |
| `splits/X_test.csv` | Features test (15%) |
| `splits/y_train.csv` | Cibles train |
| `splits/y_val.csv` | Cibles validation |
| `splits/y_test.csv` | Cibles test |
| `statistiques_descriptives.txt` | Stats descriptives detaillees |
| `rapport_eda.md` | Ce rapport |
