# Rapport d Analyse Exploratoire (EDA)
## Projet Robot Agricole - Base de reference sol/cultures africaines

**Date:** 2026-06-18 00:06:49  
**Source:** 16 cultures africaines (FAO ECOCROP, IITA, iSDA, Kaggle)  

---

## 1. Introduction

Ce rapport presente l analyse exploratoire des donnees du projet de robot agricole. Le jeu de donnees combine:

- **Base de reference JSON:** 16 cultures africaines avec plages optimales de pH, temperature, precipitation, N, P2O5, K2O et humidite
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

