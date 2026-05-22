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
└── Evitement/             
    

## Utilisation

```bash
cd MAIN

# Afficher le plan sans bouger le robot
python main.py --dry-run

# Exécution réelle (sur le Raspberry Pi équipé du PiCar)
python main.py --speed 40

# Avec une carte personnalisée
python main.py --map ma_carte.json --calibration ma_calib.json
```

## Fonctionnement

1. **Préparation** : on définit les points de prélèvement dans `map.json` et on mesure les constantes dans `calibration.json`
2. **Planification** : `planner.py` calcule les angles, distances et durées
3. **Exécution** : `main.py` lance le robot qui se déplace de point en point et effectue les prélèvements avec le bras

## Matériel

- Raspberry Pi 5/4B/3B+
- Adeept PiCar Pro V2.0 (châssis 4WD + bras 4-DOF + caméra + capteurs)
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
