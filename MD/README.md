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

Consulter svp  [La documentation](docs/doc.md) particuliere de ce robot

## Structure du projet

```
.
├── README.md                     ← ce fichier
├── MAIN/                         ← système autonome (à déployer sur le Pi)
│   ├── map.json                  ← carte du terrain (départ + waypoints)
│   ├── calibration.json          ← constantes de calibration (cm/s, °/s)
│   ├── planner.py                ← génération du plan de déplacement
│   ├── executor.py               ← exécution moteur via l'API Adeept
│   ├── arm.py                    ← contrôle du bras robotique (prélèvement)
│   └── main.py                   ← point d'entrée (orchestration)
└── Evitement/             
    └──              
    └──              
└── docs/             
    └──doc.md              


## Utilisation

```bash
cd MAIN

# Afficher le plan sans bouger le robot
python main.py --dry-run

# Avec une carte personnalisée
python main.py --map ma_carte.json --calibration ma_calib.json
```

## Fonctionnement

1. **Préparation** : on définit les points de prélèvement dans `map.json` et on mesure les constantes dans `calibration.json`
2. **Planification** : `planner.py` calcule les angles, distances et durées
3. **Exécution** : `main.py` lance le robot qui se déplace de point en point et effectue les prélèvements avec le bras

## Matériel

- Raspberry Pi 5/4B/3B+
- Adeept PiCar Pro V2.0 (châssis 2WD + bras 4-DOF + caméra + capteurs)
- Batterie 7.4V + 2x 18650

---

## Interface web (`MAIN/web/`)

Interface de contrôle et monitoring accessible depuis un navigateur.

### Structure

```
MAIN/web/
├── app.py                ← backend Flask (API REST + SSE logs temps réel)
├── database.py           ← SQLite (persistance : missions, échantillons, logs)
├── requirements.txt      ← dépendances Python
├── hardware/
│   └── simulator.py      ← simulation matérielle (développement sans Pi)
├── templates/
│   └── index.html        ← frontend (dashboard + pilotage + historique)
└── static/               ← fichiers statiques (CSS/JS/images)
```

### Démarrage

```bash
cd MAIN/web
pip install -r requirements.txt

# Mode simulation (développement PC, recommandé)
SIMULATE=1 python3 app.py

# Mode réel (Raspberry Pi avec PiCar)
SIMULATE=0 python3 app.py
```

Ouvrir [http://localhost:5000](http://localhost:5000) dans le navigateur.

### Fonctionnalités

| Fonction | Description |
|----------|-------------|
| **Joystick** | Pilotage manuel (direction, angle, durée) |
| **Collecte** | Prélèvement d'échantillons avec le bras |
| **Dépôt analyse** | Transfert des échantillons vers tubes d'analyse |
| **Mission autonome** | Lance `main.py` et affiche la progression en direct |
| **Logs temps réel** | SSE — tous les événements visibles sans rafraîchir |
| **Historique** | Missions passées, échantillons, logs persistés en DB |

### API REST

Tous les endpoints sont en `/api/` :

- `GET  /api/state` — état persistant du robot
- `POST /api/move` — commande manuelle `{dir, angle, t}`
- `POST /api/collect` — prélèvement `{n}`
- `POST /api/deposit` — dépôt analyse `{tpc, ept}`
- `POST /api/mission/start` — lance mission `{speed, map, calibration}`
- `POST /api/mission/stop` — interrompt la mission
- `GET  /api/missions` — historique des missions
- `GET  /api/samples` — historique des échantillons
- `GET  /api/logs` — historique des logs
- `GET  /api/events` — SSE (logs temps réel)




------------
Ensemble des calculs mathématiques, pour déplacer le robot d'un point A vers un point B. [voir en detail ](Planning.md) )

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

