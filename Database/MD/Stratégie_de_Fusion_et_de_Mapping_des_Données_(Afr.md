# Stratégie de Fusion et de Mapping des Données (Afrique)

Pour remplacer la base de données fictive, nous devons mapper les entrées du robot (capteurs + GPS) avec les bases de données réelles identifiées.

## 1. Mapping des Variables

| Variable Entrée Robot | Source de Donnée Réelle (Afrique) | Méthode de Fusion |
| :--- | :--- | :--- |
| **Coordonnées GPS** | ISRIC AfSP / SoilGrids | Clé de jointure spatiale (Lat/Long) |
| **pH (Capteur)** | ISRIC AfSP (pH H2O) | Validation locale vs Moyenne régionale |
| **Azote (N)** | ISRIC SoilGrids (Total Nitrogen) | Estimation de la base de départ du sol |
| **Phosphore (P)** | AfSIS Phase I (Bray-1 P) | Seuil de carence spécifique au sol africain |
| **Potassium (K)** | AfSIS Phase I (Exch. K) | Recommandation d'amendement |
| **Température/Humidité** | NASA POWER API | Corrélation temps réel pour la culture |

## 2. Logique de Recommandation (Moteur de Décision)

Le moteur ne doit plus utiliser de simples "if/else" sur des données statiques, mais une logique de **"Yield Gap Analysis"** (Analyse de l'écart de rendement) :

1.  **Identification de la Culture** : L'utilisateur choisit la culture cible (ex: Maïs).
2.  **Extraction des Besoins** : Le système extrait les besoins NPK/pH de la table de référence (ex: ISRIC 2018).
3.  **Lecture du Sol (Réel)** : Le robot mesure le pH et les nutriments actuels.
4.  **Calcul de l'Écart** : `Besoin - Mesure = Apport Nécessaire`.
5.  **Ajustement Climatique** : Si la NASA POWER indique une sécheresse prolongée, le système réduit la recommandation d'engrais azoté (risque de brûlure).

## 3. Compatibilité Technique
*   **Format de sortie** : Les données de l'ISRIC et de la FAO sont disponibles en **GeoTIFF** (raster) ou **CSV** (points).
*   **Intégration Raspberry Pi** : Les fichiers CSV filtrés par pays ou région sont plus légers (< 50 Mo) et peuvent être stockés localement en **SQLite** pour un accès hors-ligne au champ.
