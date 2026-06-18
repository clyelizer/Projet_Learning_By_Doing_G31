# Projet_Learning_By_Doing_G31

Robot autonome agricole miniature basé sur l'**Adeept PiCar Pro V2.0**.

Attention: C'est un modèle voiture classique (2WD arrière + direction servo avant), pas 4WD. 

|                  | **2WD** (2 roues motrices)            | **4WD** (4 roues motrices ind. ) |
| ---------------- | ------------------------------------- | -------------------------- |
| Moteurs          | 2                                     | 4                          |
| Virage sur place | ❌ Impossible (doit avancer en courbe) | ✅ Possible                 |
| Traction         | Moyenne                               | Meilleure                  |
| Consommation     | Faible                                | Plus élevée                |
| Code             | Plus simple (2 moteurs)               | 4 moteurs à synchroniser   |

Consulter svp  [La documentation](docs/main_doc.md) particuliere de ce robot

## Structure du projet

```
.
├── README.md                     ← ce fichier
├── CLAUDE.md                     ← règles pour l'assistant IA
├── requirements.txt              ← dépendances Python
│
├── src/                          ← système autonome (à déployer sur le Pi)
│   ├── main.py                   ← point d'entrée (orchestration du pipeline)
│   ├── planner.py                ← génération du plan de déplacement
│   ├── executor.py               ← exécution moteur (mouvement uniquement)
│   ├── arm.py                    ← contrôle du bras robotique (sonde)
│   ├── sensor_arduino.py         ← capteur sol via Arduino (USB série)
│   ├── camera.py                 ← capture photo via Picamera2
│   ├── camera_video.py           ← enregistrement vidéo H264
│   ├── vlm_analyzer.py           ← analyse IA des photos de sol (Gemini/Groq)
│   ├── image_processor.py        ← traitement asynchrone des images (pipeline IA)
│   ├── data_logger.py            ← agrégation des données mission → JSON
│   └── web/                      ← dashboard Flask (réseau local)
│       ├── app.py
│       ├── static/style.css
│       └── templates/
│
├── config/
│   ├── map.json                  ← carte du terrain (départ + waypoints)
│   └── calibration.json          ← constantes de calibration (cm/s, °/s, caméra)
│
├── tests/                        ← tests (unitaires + intégration hardware)
│   ├── test_sensor_arduino.py    ← tests unitaires parseur capteur (14 tests)
│   ├── test_sensor_live.py       ← test intégration hardware réel (3 tests)
│   ├── test_sensor_audit.py      ← audit complet chaîne de mesure
│   ├── test_camera.py            ← tests caméra + image processor (16 tests)
│   ├── test_cam_live.py          ← test caméra hardware
│   ├── test_vlm_analyzer.py      ← tests VLM (API réelle, 10 tests)
│   ├── test_video_record.py      ← test enregistrement vidéo
│   ├── test_steering.py          ← test direction interactive
│   ├── test_steering_diag.py     ← diagnostic direction
│   ├── test_steering_return.py   ← test compensation jeu mécanique
│   ├── test_speed_forward.py     ← test vitesse avant
│   ├── test_turn_rate.py         ← test taux de rotation
│   └── test_rest_position.py     ← test retour position
│
├── tools/                        ← outils de diagnostic hardware
│   └── i2c_diagnostic.py         ← scanner I2C
│
├── data/                         ← données générées à l'exécution
│   ├── photos/                   ← photos capturées du sol
│   └── results.json              ← résultats agrégés de mission
│
└── docs/                         ← documentation du projet
    ├── main_doc.md               ← documentation principale du robot
    ├── architecture.md           ← plan d'architecture logicielle
    ├── materiel.md               ← liste du matériel
    ├── planning_algo.md          ← algorithme de planification
    ├── Soils4Africa.md           ← recherche données pédologiques
    ├── obstacle_avoidance.md     ← évitement d'obstacles (VFH+)
    ├── database_research.md      ← recherche base de données agricole
    ├── results.md                ← résultats de tests
    └── TODO.md                   ← feuille de route
```

## Utilisation

```bash
cd src

# Fichiers par défaut (config/map.json, config/calibration.json)
python main.py

# Afficher le plan sans bouger le robot (simulation)
python main.py --dry-run

# Avec des fichiers personnalisés
python main.py --map ma_carte.json --calib ma_calib.json

# Combiner plusieurs options
python main.py --dry-run --map mission1.json --calib terrain_ouest.json

# Aide complète
python main.py --help

# Dashboard web (réseau local)
cd src && python web/app.py
# → http://<IP_PI>:5000
```

## Dashboard Web

Accessible sur le réseau local, 3 pages :
- **`/`** — Dashboard : stats mission, carte SVG des waypoints, tableau de mesures
- **`/data`** — Données : photos, JSON brut, historique des waypoints
- **`/recommandations`** — Conseils agricoles basés sur les mesures (pH, EC, humidité, température)

Le dashboard détecte automatiquement l'IP locale et l'affiche au démarrage.

## Fonctionnement

1. **Préparation** : on définit les points de mesure dans `config/map.json` et on mesure les constantes dans `config/calibration.json`
2. **Planification** : `planner.py` calcule les angles, distances et durées
3. **Exécution** : `main.py` orchestre le pipeline complet :
   - Déplacement autonome vers chaque waypoint (`executor.py`)
   - À chaque arrêt : descente du capteur (`arm.py`), mesure du sol (`sensor_arduino.py`), remontée
   - Capture de N photos du sol (`camera.py`)
   - Traitement asynchrone des images (`image_processor.py`)
   - Agrégation des résultats dans `data/results.json` (`data_logger.py`)

## Matériel

- Raspberry Pi 5/4B/3B+
- Adeept PiCar Pro V2.0 (châssis 2WD + bras 4-DOF + caméra + capteurs)
- Batterie 7.4V + 2x 18650

## Capteurs et composants

Le **PiCar-Pro V2** embarque une gamme complète de périphériques. 👉 [**Documentation complète du matériel**](docs/materiel.md)

| Composant | Description | Broche/Canal |
|-----------|-------------|----------|
| **Caméra USB** | Capture vidéo pour vision par ordinateur | USB |
| **Servomoteurs** | 8 servos PCA9685 pour mobilité et articulations du bras | CH0–CH7 |
| **Ultrason HC-SR04** | Détection d'obstacles (2 cm à 4 m) | GPIO23 (Trig), GPIO24 (Echo) |
| **Capteurs IR (×3)** | Suivi de ligne infrarouge (S1/S2/S3) | GPIO17, GPIO27, GPIO22 |
| **LEDs (×3)** | Signalisation visuelle | GPIO9, GPIO25, GPIO11 |
| **Buzzer** | Alertes sonores | GPIO18 |
| **Moteurs DC (×2)** | Propulsion des roues arrière (M1, M2) | CH12–CH15 |
| **Module OLED** | Affichage d'informations | I2C |
| **LED RGB WS2812** | Éclairage d'ambiance programmable | GPIO |
| **Récepteur IR** | Réception télécommande infrarouge | GPIO |

### Contrôleur PCA9685

Le **Robot HAT V3.2** intègre un PCA9685 (adresse I2C `0x5f`, fréquence 50 Hz) générant 16 signaux PWM indépendants :
- **CH0–CH7** : servomoteurs (direction, ultrason, bras, pince)
- **CH12–CH15** : moteurs DC via ponts en H

### Installation

```bash
sudo apt update && sudo apt install git -y
git clone https://github.com/adeept/Adeept_PiCar-Pro.git
cd Adeept_PiCar-Pro
sudo python3 setup.py

# Vérifier la connexion I2C
i2cdetect -y 1  # L'adresse 0x5f doit apparaître
```

### Pilotage à distance

```bash
# SSH — terminal uniquement (recommandé pour le développement)
ssh pi@<IP_ROBOT>

# VNC — bureau complet (pour voir la caméra)
# Activer dans raspi-config → Interface Options → VNC → Yes
```

---

## Interface web (`src/web/`)

*À développer — actuellement non implémentée.*

---

## Calculs mathématiques

Ensemble des calculs pour déplacer le robot d'un point A vers un point B. [Voir en détail](docs/planning_algo.md)

---

## Données d'entrée

| Paramètre | Description |
|-----------|-------------|
| $(x_A, y_A)$ | Coordonnées du point de départ A (cm) |
| $(x_B, y_B)$ | Coordonnées du point d'arrivée B (cm) |
| $\theta_{\text{actuel}}$ | Orientation actuelle du robot en degrés (heading, 0° = axe +X) |
| $v_{\text{lin}}$ | Vitesse linéaire du robot (cm/s), issue de `calibration.json` |
| $v_{\text{rot}}$ | Vitesse angulaire du robot (°/s), issue de `calibration.json` |

---

## Étape 1 — Vecteur de déplacement

On calcule d'abord les différences de coordonnées entre B et A :

$$
\Delta x = x_B - x_A
$$

$$
\Delta y = y_B - y_A
$$

---

## Étape 2 — Distance à parcourir

La distance euclidienne entre A et B est :

$$
d = \sqrt{(\Delta x)^2 + (\Delta y)^2}
$$

*En unités : centimètres (cm).*

---

## Étape 3 — Angle cible (cap vers B)

On détermine l'angle absolu que le robot doit avoir pour être orienté vers B. On utilise la fonction `atan2` qui gère tous les quadrants :

$$
\theta_{\text{cible}} = \operatorname{atan2}(\Delta y, \Delta x)
$$

**Conversion en degrés** (car les capteurs et moteurs utilisent des degrés) :

$$
\theta_{\text{cible}}^{\circ} = \theta_{\text{cible}} \times \frac{180}{\pi}
$$

*Résultat entre -180° et +180°.*

---

## Étape 4 — Angle de rotation à effectuer

Le robot doit tourner de la différence entre son orientation actuelle et l'angle cible :

$$
\Delta\theta = \theta_{\text{cible}}^{\circ} - \theta_{\text{actuel}}
$$

---

## Étape 5 — Normalisation de l'angle (optimisation du virage)

Pour que le robot tourne toujours par le chemin le plus court (jamais plus de 180°) :

$$
\Delta\theta_{\text{norm}} = ((\Delta\theta + 180^{\circ}) \bmod 360^{\circ}) - 180^{\circ}
$$

**Interprétation :**
- Si $\Delta\theta_{\text{norm}} > 0$ : tourner à **gauche** (sens trigonométrique / anti-horaire)
- Si $\Delta\theta_{\text{norm}} < 0$ : tourner à **droite** (sens horaire)
- Si $\Delta\theta_{\text{norm}} = 0$ : déjà bien orienté

---

## Étape 6 — Conversion en durées moteur

Grâce aux constantes de calibration, on transforme les grandeurs géométriques en temps de commande moteur.

### Durée de rotation

$$
t_{\text{rot}} = \frac{|\Delta\theta_{\text{norm}}|}{v_{\text{rot}}}
$$

*Unités : secondes (s).*

### Durée d'avance linéaire

$$
t_{\text{avance}} = \frac{d}{v_{\text{lin}}}
$$

*Unités : secondes (s).*

