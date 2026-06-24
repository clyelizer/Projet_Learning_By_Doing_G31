# PHASE 1 : Cartographie des sources de donnees sol/cultures
## Synthese de la deep research

---

## SOURCES INSTITUTIONNELLES (hautement recommandees)

| Source | URL | Type donnees | Cultures | Format |
|--------|-----|-------------|----------|--------|
| **FAO ECOCROP** | gaez.fao.org/pages/ecocrop | pH, T°C, precip, altitude | 2568 especes | Web/MySQL |
| **FAO GAEZ v5** | data.apps.fao.org/gaez/ | suitability, rendements | 51 cultures | Raster 5min |
| **FAOSTAT Nutrients** | zenodo.org/records/8000435 | bilans N,P,K par pays | 205 pays | CSV |
| **iSDA Africa (open soil)** | github.com/iSDA-Africa/open-soil-data | 20+ proprietes sol | Toute Afrique | CSV (49000 echantillons) |
| **AfSIS / iSDAsoil** | isda-africa.com/isdasoil | pH,N,P,K,MO,texture | Afrique entiere | API/Carte 30m |
| **ISRIC SoilGrids** | soilgrids.org | proprietes sol mondiales | Monde | Raster 250m |
| **ISRIC Africa Profiles** | africasis.isric.org | profils sol | 38 pays Afrique | CSV/GeoPackage |
| **HWSD v1.2** | iiasa.ac.at/models-tools-data/hwsd | 16000 unites sol | Monde | Raster 30s |
| **NPKGRIDS** | nature.com/articles/s41597-024-04030-4 | engrais N,P,K | 173 cultures | Raster 5.6km |

## DATASETS CULTURES AFRICAINES

| Dataset | URL | Cultures | Enreg. | Format |
|---------|-----|----------|--------|--------|
| **Crop Suitability Africa (Nature)** | springernature.figshare.com/23896887 | 23 cultures africaines | Raster 0.5° | NetCDF/GeoTIFF |
| **Mendeley Ethiopia Crops** | data.mendeley.com/datasets/8v757rr4st/1 | mais,ble,teff,sorgho,mil | CSV | CC BY-NC-ND |
| **Kaggle Crop Recommendation** | kaggle.com/datasets/atharvaingle/crop-recommendation-dataset | 22 cultures (Inde) | 2200 | CSV Apache 2.0 |
| **Kaggle Crop NPK** | kaggle.com/datasets/javakhan/crops-npk-data-set | ble,riz,mais | 20000 | CSV MIT |
| **Global Crop Nutrient Removal** | cropnutrientdata.net | N,P,K par culture | Monde | Web gratuit |

---

## DONNEES EXTRAITES : BESOINS SOL PAR CULTURE AFRICAINE

### Cereales
(NB : valeurs originales en P2O5 et K2O, formes engrais standard. A reconvertir en P/K elementaires si besoin.)

| Culture | pH | EC (dS/m) | N (kg/ha) | P2O5 (kg/ha) | K2O (kg/ha) | T°C sol |
|---------|----|-----------|-----------|-------------|-------------|---------|
| **Mais (Zea mays)** | 5.5-6.5 | <1.5 | 100-200 | 30-90 | 20-70 | 18-32 |
| **Riz (Oryza sativa)** | 5.0-6.5 | <2.0 | 80-120 | 30-60 | 40-80 | 20-35 |
| **Mil (P. glaucum)** | 5.0-7.5 | <1.5 | 40-60 | 20-30 | 0-20 | 25-35 |
| **Sorgho (S. bicolor)** | 5.5-6.5 | <1.5 | 60-120 | 20-60 | 20-40 | 20-35 |
| **Fonio (D. exilis)** | 5.5-7.5 | <1.0 | 10-30 | 10-20 | 0-20 | 25-35 |

### Racines et tubercules

| Culture | pH | EC (dS/m) | N (kg/ha) | P2O5 (kg/ha) | K2O (kg/ha) | T°C sol |
|---------|----|-----------|-----------|-------------|-------------|---------|
| **Manioc (M. esculenta)** | 5.5-6.5 | <1.0 | 48-90 | 10-44 | 50-75 | 25-30 |
| **Igname (Dioscorea)** | 5.5-6.5 | <1.0 | 30-160 | 10-60 | 40-180 | 25-30 |
| **Patate douce (I. batatas)** | 5.8-6.0 | <1.0 | 60-90 | 30-60 | 120-200 | 20-30 |

### Legumineuses

| Culture | pH | EC (dS/m) | N (kg/ha) | P2O5 (kg/ha) | K2O (kg/ha) | T°C sol |
|---------|----|-----------|-----------|-------------|-------------|---------|
| **Niebe (V. unguiculata)** | 5.5-6.5 | <1.5 | 20-30 | 30-45 | 20-30 | 20-35 |
| **Arachide (A. hypogaea)** | 6.0-6.5 | <1.0 | 20-25 | 40-60 | 40-75 | 25-30 |
| **Haricot (P. vulgaris)** | 5.5-6.5 | <1.2 | 30-60 | 40-60 | 20-40 | 15-25 |

### Cultures de rente

| Culture | pH | EC (dS/m) | N (kg/ha) | P2O5 (kg/ha) | K2O (kg/ha) | T°C sol |
|---------|----|-----------|-----------|-------------|-------------|---------|
| **Coton (Gossypium)** | 5.5-7.5 | <2.0 | 60-150 | 20-50 | 30-100 | 20-30 |
| **Cafe (Coffea arabica)** | 5.5-6.5 | <1.0 | 150-250 | 30-80 | 120-250 | 15-24 |
| **Cacao (T. cacao)** | 6.0-7.5 | <0.8 | 60-120 | 20-30 | 50-100 | 22-30 |
| **Banane plantain (Musa)** | 5.5-7.0 | <0.8 | 200-400 | 40-60 | 200-600 | 25-30 |
| **Sesame (S. indicum)** | 5.5-8.0 | <1.0 | 40-64 | 23-46 | 20-40 | 25-35 |

---

## PLAN POUR LA SUITE (Phase 2)

### Sources prioritaires a exploiter :

1. **FAO ECOCROP** → API/dump pour les 2568 especes (pH, T°C, precip)
2. **iSDA Africa** → CSV direct : isdasoil.s3.us-west-2.amazonaws.com/soil_analysis_data/latest/iSDA_soil_data.csv
3. **Nature Crop Suitability Africa** → Figshare 23896887 (23 cultures africaines)
4. **Kaggle Crop Recommendation** → 22 cultures (a filtrer et completer)
5. **Mendeley Ethiopia** → donnees sol ethiopiennes (mais, ble, teff)
6. **FAOSTAT NPK budgets** → bilans par pays (contexte macro)

### Ce qui manque :
- EC (conductivite) optimale par culture : tres peu documentee
- Humidite optimale du sol (% volume) par culture
- Seuils de fertilisation specifiques aux sols africains (pauvres)
- Donnees pour cultures africaines mineures (fonio, niebe, etc.)

### Prochaine etape :
Phase 2 : Extraire les donnees de la FAO ECOCROP en priorite (2568 especes, c'est la source la plus complete en un coup), puis completer avec les articles scientifiques culture par culture.
