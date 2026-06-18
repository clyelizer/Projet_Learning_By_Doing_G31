# Soils4Africa Field Survey

Soils4Africa est la DB choisie

## Informations générales

| Champ | Détail |
|-------|--------|
| **Nom complet** | Soils4Africa Field Survey (Soil Information System - SIS) |
| **Fournisseur** | ISRIC (Wageningen University) – Projet EU-H2020 Soils4Africa |
| **Couverture** | Terres agricoles d'Afrique (continent entier) |
| **Taille** | ~20 000 points de sol échantillonnés uniformément |
| **Profondeurs** | 0–20 cm et 20–50 cm (2 horizons) |
| **Période de collecte** | 2022–2024 |
| **Accès** | Portail SIS (WMS/WFS) ou téléchargement via « Open Dashboard » |
| **Licence** | CC BY 4.0 (données ouvertes du projet H2020, usage commercial permis sous attribution) |
| **Coût** | Gratuit |

## Variables mesurées

Variables chimiques du sol (analyse en laboratoire unique pour garantir l'homogénéité) :

- pH (H₂O)
- Carbone organique (C org., g/kg)
- Azote total (N, g/kg)
- Phosphore extractible (P, mg/kg)
- Potassium (K, mg/kg)
- Autres indicateurs chimiques

## Qualité des données

- **Protocole standardisé** : guide SOP (Standard Operating Procedure) de terrain et d'analyse préétabli, documents publics disponibles
- **Laboratoire unique** : toutes les analyses effectuées dans le même laboratoire en Afrique du Sud, garantissant l'uniformité des mesures
- **Méthodes** : analyses spectrométriques calibrées par chimie humide
- **Homogénéité** : très élevée (jeu de données récent, protocole unique)
- **Limite** : peut manquer de représentativité fine locale (échantillonnage systématique continental)
- **Procédures publiques** : guides de laboratoire et de terrain disponibles en accès libre

## Correspondance des variables

| Variable | Unité | Cohérence |
|----------|-------|-----------|
| pH | eau 1:1 | Cohérent avec iSDA, AfSIS, WoSIS |
| N total | g/kg | Convertir en % (1 g/kg = 0,1 %) |
| P extractible | mg/kg | Directement comparable (Méhlich-3 ou Olsen) |
| C organique | g/kg | Convertir en MO % (×1,724) |
| K | mg/kg | Comparable avec iSDA |

## Liens d'accès

### Portail principal du SIS (Soil Information System)
| Lien | URL |
|------|-----|
| **Portail SIS** (carte, dashboard, catalogue, docs) | [https://africasis.isric.org](https://africasis.isric.org) |

### Téléchargement des données
| Lien | URL |
|------|-----|
| **Dashboard de téléchargement** (données ponctuelles géoréférencées) | [https://dashboards.isric.org/superset/dashboard/soils4africa/](https://dashboards.isric.org/superset/dashboard/soils4africa/) |
| **Téléchargement alternatif** (dashboard public) | [https://dashboards.isric.org/superset/dashboard/p/AWEgppXGgzd/](https://dashboards.isric.org/superset/dashboard/p/AWEgppXGgzd/) |
| **Catalogue de données géospatiales** (couches raster supplémentaires) | [https://africasis.isric.org/cat/collections/metadata:main/items](https://africasis.isric.org/cat/collections/metadata:main/items) |
| **Visualisation cartographique** (Map Viewer) | [https://africasis.isric.org/map/](https://africasis.isric.org/map/) |

### Documentation et procédures
| Lien | URL |
|------|-----|
| **Documents du projet** (guides, rapports, SOP) | [https://www.soils4africa-h2020.eu/documents](https://www.soils4africa-h2020.eu/documents) |
| **Procédures terrain et labo** (SOP) | [https://africasis.isric.org/procedures.html](https://africasis.isric.org/procedures.html) |
| **Protocole de terrain** (PDF) | [https://www.soils4africa-h2020.eu/serverspecific/soils4africa/images/Documents/4.2AENGProtocolsforfieldsurvey_v3_20_03_2023.pdf](https://www.soils4africa-h2020.eu/serverspecific/soils4africa/images/Documents/4.2AENGProtocolsforfieldsurvey_v3_20_03_2023.pdf) |
| **Guide d'analyse laboratoire** (PDF) | [https://www.soils4africa-h2020.eu/serverspecific/soils4africa/images/Documents/GuidanceonLaboratoryAnalysis.pdf](https://www.soils4africa-h2020.eu/serverspecific/soils4africa/images/Documents/GuidanceonLaboratoryAnalysis.pdf) |
| **Sampling Design** (PDF) | [https://www.soils4africa-h2020.eu/serverspecific/soils4africa/images/Documents/Soils4Africa_D3.2B_Sampling_design_v01.pdf](https://www.soils4africa-h2020.eu/serverspecific/soils4africa/images/Documents/Soils4Africa_D3.2B_Sampling_design_v01.pdf) |

### Code source et outils
| Lien | URL |
|------|-----|
| **Organisation GitHub** (code, API, notebooks) | [https://github.com/soil-data-of-africa](https://github.com/soil-data-of-africa) |
| **Dépôt spectral** (outils spectroscopie, notebooks Jupyter) | [https://github.com/soil-data-of-africa/spectral](https://github.com/soil-data-of-africa/spectral) |

### Projet et licence
| Lien | URL |
|------|-----|
| **Site officiel du projet Soils4Africa** | [https://www.soils4africa-h2020.eu](https://www.soils4africa-h2020.eu) |
| **Licence des données** (CC BY 4.0 - fichier PDF) | [https://africasis.isric.org/res/files/Soils4Africa_licence_agreement_v20240926.pdf](https://africasis.isric.org/res/files/Soils4Africa_licence_agreement_v20240926.pdf) |
| **Page ISRIC du projet** | [https://www.isric.org/projects/soils4africa](https://www.isric.org/projects/soils4africa) |
| **Vidéos YouTube** (protocoles terrain EN/FR/AR) | [https://www.youtube.com/channel/UCrk0Djl2xYUoZsrgGIL4Ztg/playlists](https://www.youtube.com/channel/UCrk0Djl2xYUoZsrgGIL4Ztg/playlists) |

## Licence et aspects légaux

- **Licence** : CC BY 4.0 (utilisation commerciale autorisée avec attribution)
- **Attribution requise** : citer ISRIC et le projet Soils4Africa (EU-H2020)
- **Pas de données personnelles** : aucun risque de confidentialité
- **Aucune garantie** : comme indiqué par le projet, aucune garantie d'exactitude n'est offerte

## Intérêt pour le modèle de recommandation

- **Source prioritaire** avec iSDA et AfSIS pour l'entraînement (variables clés P, N, MO, pH en format homogène)
- Contribue ~20 000 points sur les ~70 000–100 000 cibles pour un modèle robuste
- Couvre les terres agricoles africaines de façon uniforme
- Complément idéal à iSDA (50 000 points) pour atteindre une base solide

## Référence dans le rapport

> *"Les sources prioritaires pour l'entraînement sont celles fournissant les variables clés (P, N, MO, pH) en format homogène et couvrant bien l'Afrique (iSDA, Soils4Africa, AfSIS)."*

> *"Combiner les ~50 000 d'iSDA, ~20 000 de Soils4Africa et d'autres sources donnerait ≈70–100 000 cas."*
