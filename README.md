# Projet_Learning_By_Doing_G31

Robot autonome agricole miniature basé sur l'**Adeept PiCar Pro V2.0**.

## Structure

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
└── Adeept_PiCar-Pro/             ← code source officiel Adeept (dépendance)
    ├── Server/                   ← Move.py, RPIservo.py, WebServer.py, etc.
    ├── Client/                   ← GUI client
    └── Examples/                 ← exemples fournis par Adeept
```

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
