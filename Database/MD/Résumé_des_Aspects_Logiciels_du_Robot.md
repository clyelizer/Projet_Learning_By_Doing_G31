# Résumé des Aspects Logiciels du Robot

Ce document détaille les composants et les approches logicielles qui sous-tendent le fonctionnement du robot, en se basant sur l'architecture fonctionnelle et les modes de fonctionnement décrits.

## 1. Architecture Fonctionnelle du Robot

### 1.2 Module de Contrôle
Le contrôle central est assuré par un **Raspberry Pi** (versions 5/4B/3B+/3B), agissant comme unité de traitement et de coordination. La carte **Adeept Robot HAT V3.2** est utilisée pour piloter les moteurs et servomoteurs.

### 1.3 Module de Perception et Navigation
Pour la vision, une caméra USB HD 1080p est employée. Les capteurs ultrasoniques sont utilisés pour l'évitement d'obstacles.

## 2. Modes de Fonctionnement

### 2.1 Segmentation (IA & Satellite)
Cette étape utilise l'imagerie satellitaire pour cartographier la biomasse et diviser les champs en zones homogènes. Le processus s'appuie sur des outils open source et suit les étapes clés suivantes :

*   **Choix et Téléchargement des Images** : Utilisation de données provenant de satellites comme **Sentinel-2**, téléchargées depuis des archives ouvertes telles que Copernicus ou Earth Explorer.
*   **Prétraitement** : Correction atmosphérique, découpage géographique et masquage des nuages. Des outils **Python** comme **Sen2Chain** sont utilisés pour automatiser ces tâches.
*   **Calcul des Indices** : Calcul d'indices spectraux comme le **NDVI** (Normalized Difference Vegetation Index) ou l'**EVI** (Enhanced Vegetation Index) à partir des bandes spectrales. Des bibliothèques **Python** telles que **GDAL** ou **Rasterio** sont employées pour ces opérations.
*   **Segmentation ou Classification & Définition des Points d'Échantillonnage** : Regroupement des pixels similaires via des seuils. Des outils **SIG** comme **QGIS** avec le plugin Semi-Automatic Classification sont utilisés pour convertir ces groupes en polygones vectorisés. Des modèles statistiques ou d'apprentissage automatique peuvent être combinés avec des échantillons de terrain pour inférer des teneurs en matière organique, azote ou pH. Les points GPS représentatifs (centroïdes) sont exportés en format **CSV**.

### 2.2 Prélèvement
Le robot se déplace en évitant les obstacles grâce à des capteurs ultrasons et une caméra. Les technologies logicielles clés incluent :

*   **Vision** : **OpenCV** est utilisé pour le traitement des images capturées par la caméra HD afin de repérer les obstacles. La méthode implique la conversion en niveaux de gris, l'application d'un flou gaussien et la détection des bords avec l'algorithme Canny.
*   **Architecture Globale** : **ROS (Robot Operating System)** est mentionné pour l'architecture globale du système.
*   **Planification de Trajectoire** : Des algorithmes comme **A*** sont utilisés pour la planification des déplacements.

### 2.5 Restitution des Informations (Recommandation, Cartographie)
Cette étape transforme les données brutes en conseils pratiques pour l'agriculteur. L'approche repose sur l'utilisation de deux modèles prêts à l'emploi du projet open source **Harvestify** [1] :

*   **Modèle de Prédiction de Culture** : Prédit la culture la plus adaptée en fonction des paramètres du sol et du climat.
*   **Modèle d'Analyse des Ratios** : Analyse les ratios d'azote, phosphore, matière organique, détecte les carences ou excès, et suggère des ajustements (ex: type d'engrais, plantation de couverts végétaux).

Ces modèles sont conçus pour être légers et exécutables directement sur le **Raspberry Pi**, fournissant des conseils actionnables.

## Références

[1] Harvestify: https://github.com/Gladiator07/Harvestify
