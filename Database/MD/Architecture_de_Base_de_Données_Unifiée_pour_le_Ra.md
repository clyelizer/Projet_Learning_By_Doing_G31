# Architecture de Base de Données Unifiée pour le Raspberry Pi

Pour assurer un fonctionnement efficace et autonome du robot sur le terrain, une architecture de base de données légère et performante est essentielle. Compte tenu des contraintes de ressources du Raspberry Pi et de la nécessité d'un accès rapide aux données, une approche combinant une base de données embarquée et des mécanismes de synchronisation est recommandée.

## 1. Base de Données Locale (SQLite)

La solution la plus adaptée pour le Raspberry Pi est une base de données relationnelle embarquée comme **SQLite**. Elle offre les avantages suivants :

*   **Légèreté** : Ne nécessite pas de serveur de base de données séparé, les données sont stockées dans un fichier unique.
*   **Autonomie** : Fonctionne parfaitement hors ligne, ce qui est crucial pour les opérations sur le terrain où la connectivité peut être limitée.
*   **Facilité d'intégration** : Des bibliothèques Python natives (`sqlite3`) permettent une interaction aisée.

### Structure des Tables Recommandée :

| Table | Description | Champs Clés | Exemples de Champs |
| :--- | :--- | :--- | :--- |
| `sols_afrique` | Données pédologiques géo-référencées | `id_sol`, `latitude`, `longitude` | `ph_h2o`, `azote_total`, `phosphore_bray1`, `potassium_echangeable`, `type_sol` |
| `cultures_besoins` | Besoins NPK et pH par culture | `id_culture`, `nom_culture` | `ph_min`, `ph_max`, `n_ideal`, `p_ideal`, `k_ideal` |
| `donnees_meteo` | Données climatiques historiques/prévisionnelles | `id_meteo`, `latitude`, `longitude`, `date` | `temperature_moy`, `precipitations`, `humidite` |
| `recommandations_engrais` | Types d'engrais et leurs compositions | `id_engrais`, `nom_engrais` | `n_pourcentage`, `p_pourcentage`, `k_pourcentage`, `cout_kg` |

## 2. Mécanisme de Synchronisation

Bien que le robot doive fonctionner de manière autonome, une synchronisation périodique avec une base de données centrale ( par exemple) est nécessaire pour :

*   **Mises à jour des données** : Intégrer de nouvelles données pédologiques, de nouvelles variétés de cultures ou des ajustements aux recommandations.
*   **Téléchargement des données collectées** : Envoyer les mesures de sol et les observations du robot vers le serveur central pour analyse et archivage.

### Approche de Synchronisation :

*   **Fréquence** : La synchronisation peut être déclenchée manuellement lorsque le robot est connecté à un réseau Wi-Fi, ou automatiquement à intervalles réguliers si une connexion stable est disponible.
*   **Protocole** : Utilisation d'API RESTful pour échanger des données JSON entre le Raspberry Pi et le serveur central.
*   **Gestion des Conflits** : Des stratégies simples (ex: "dernière écriture gagne" ou fusion intelligente) peuvent être implémentées pour résoudre les conflits lors de la synchronisation.

## 3. Intégration avec le Moteur de Recommandation

Le moteur de recommandation, exécuté sur le Raspberry Pi, interrogera directement la base de données SQLite locale. Par exemple :

1.  Le robot mesure le pH et les niveaux de nutriments.
2.  Il récupère les données de sol les plus proches de sa position GPS dans la table `sols_afrique`.
3.  Il consulte les besoins de la culture cible dans `cultures_besoins`.
4.  Il calcule l'écart et génère une recommandation d'engrais en se basant sur `recommandations_engrais`.
5.  Les données météorologiques de `donnees_meteo` peuvent être utilisées pour affiner la recommandation (ex: ajuster l'apport d'azote en fonction des prévisions de pluie).

Cette architecture offre une solution robuste et adaptée aux contraintes d'un système embarqué tout en fournissant les données réelles nécessaires au moteur de recommandation du robot.
