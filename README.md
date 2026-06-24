# 🌱 AgroScan

Robot autonome agricole miniature basé sur l'**Adeept PiCar Pro V2.0** — Analyse de sol, recommandations culturales, dashboard web.

> **2WD** (2 roues motrices arrière + direction servo avant). Pas 4WD.

## Structure du projet

```
.
├── src/                          # Code robot (déployé sur le Pi)
│   ├── main.py                   ← Point d'entrée (orchestration complète)
│   ├── planner.py                ← Plan de déplacement (angles, distances)
│   ├── executor.py               ← Exécution moteurs
│   ├── arm.py                    ← Bras robotique (sonde sol)
│   ├── sensor_arduino.py         ← Capteur sol via Arduino (USB série)
│   ├── camera.py / camera_video.py  ← Capture photo / vidéo
│   ├── vlm_analyzer.py           ← Analyse IA des photos (Groq/Gemini)
│   ├── image_processor.py        ← Traitement asynchrone des images
│   ├── reco_engine.py            ← Pipeline ML recommandations
│   ├── tts_engine.py             ← Synthèse vocale (gTTS + espeak-ng)
│   ├── data_logger.py            ← Agrégation données mission → JSON
│   ├── config_loader.py          ← Configuration
│   ├── web/                      ← Dashboard SPA Flask
│   │   ├── app.py                ← API REST (Flask)
│   │   └── static/               ← Frontend (index.html, app.js, style.css)
│   ├── doctor/                   ← Robot Doctor (diagnostic + auto-healing)
│   │   ├── engine.py             ← Orchestrateur checks → LLM → heal
│   │   ├── checks.py             ← 12 tests hardware/software
│   │   ├── healer.py             ← Correctifs automatiques sécurisés
│   │   ├── prompts.py            ← Prompts pour Qwen Code (local Pi)
│   │   └── state.py              ← Capture état système
│   └── ml/                       ← Pipeline Machine Learning
│       ├── 01_databases/         ← Base de référence 41 cultures + dataset
│       ├── 02_models/            ← Modèles entraînés (.pkl)
│       │   └── best/             ← Meilleurs modèles (classifieur + régresseurs N/P/K)
│       ├── 03_training/          ← Scripts d'entraînement + métriques
│       ├── 04_figures/           ← Visualisations (heatmap, boxplots, SHAP...)
│       └── 05_recommendation/    ← Algorithme de classement cultures
│
├── config/                       ← map.json, calibration.json
├── tests/                        ← Tests unitaires + hardware
├── data/                         ← Données générées (photos, results.json, audio/)
├── docs/                         ← Documentation
├── plans/                        ← Notes de développement
└── robotique/                    ← Scripts d'apprentissage (TP)
```

## Dashboard Web

Accessible sur le réseau local en **6 onglets** :

| Onglet | Description |
|--------|-------------|
| **Dashboard** | Stats mission, carte SVG, tableau des mesures |
| **Recommandations** | Conseils agricoles par zone + TTS (22 langues) |
| **Données** | Photos, JSON brut, historique waypoints |
| **Test analyse** | Simulateur interactif (sliders pH/T/H/EC → NPK + classement) |
| **Base Réf.** | Browse 41 cultures africaines (filtre zone, recherche) |
| **Modèles ML** | Figures, métriques, SHAP, fichiers .pkl |
| **🩺 Doctor** | Diagnostic 12 tests + auto-healing (PCA9685, caméra, Flask...) |

## Pipeline ML

1. **EDA** → Dataset préprocessing + figures + splits train/val/test
2. **Entraînement** → RandomForest / XGBoost classifieur + régresseurs N/P/K
3. **Classement** → 41 cultures africaines scorées (NPK, pH, T°, humidité, EC)
4. **Explicabilité** → Impact par paramètre (vert/orange/rouge)

Les modèles sont sauvegardés dans `src/ml/02_models/best/` (meilleurs classifieur + régresseurs).

## Synthèse vocale (TTS)

- **gTTS** (online) : français, anglais, hausa, swahili, afrikaans, amharic, arabe
- **espeak-ng** (offline) : + yoruba, igbo, zulu, xhosa, shona, sesotho, somali...
- **22 langues dont 18 africaines** — sélectionnables dans le dashboard

## 🩺 Robot Doctor

Diagnostic et auto-réparation intégrés au dashboard. Vérifie 12 points critiques :

| Test | Correctif auto |
|------|---------------|
| ✅ PCA9685 (I2C 0x5f) | Reset I2C `i2cset` |
| ✅ Moteurs 2WD | — (manual si bloqué) |
| ✅ Direction servo CH0 | — (manual si désynchronisé) |
| ✅ Bras robotique CH1-4 | — (manual) |
| ✅ Caméra (libcamera) | Cleanup + reload module |
| ✅ Capteur sol (Arduino série) | Reset DTR |
| ✅ Flask (port 5000) | Redémarrage auto |
| ✅ Disque | Nettoyage cache audio |
| ✅ RAM | — |
| ✅ Température CPU | — |
| ✅ Modèles ML (.pkl) | — |
| ✅ Base référence (41 cultures) | — |

- **🔍 Diagnostiquer** : exécute les 12 tests en 2-3 secondes
- **🤖 Analyse LLM** : optionnel, utilise Qwen Code (local Pi) pour interpréter les erreurs
- **🔧 Auto-réparer** : correctifs sécurisés (reset I2C, redémarrage services, nettoyage)
- **📋 Historique** : tous les diagnostics sauvegardés dans `data/doctor/`

Tests à valider sur le Pi :
- `i2cdetect -y 1` → détection PCA9685 (0x5f)
- Impulsions moteurs (sans roues)
- Balayage servo direction
- `libcamera-still --list-cameras` → détection caméra
- Port série Arduino (/dev/ttyACM0)
- Lecture des 15 modèles .pkl

## Utilisation

```bash
# Mission complète (plan → déplacement → mesures → recommandations → audio)
cd src && python main.py

# Simulation (affiche le plan sans bouger)
python main.py --dry-run

# Dashboard web seul
python src/web/app.py
# → http://<IP_PI>:5000
```

## Matériel

- Raspberry Pi 5/4B/3B+
- Adeept PiCar Pro V2.0 (2WD + bras 4-DOF + caméra)
- Capteur sol Arduino (pH, EC, température, humidité)
- Batterie 7.4V + 2× 18650

Détails → [docs/materiel.md](docs/materiel.md)

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Architecture logicielle détaillée |
| [Matériel](docs/materiel.md) | Liste complète des composants |
| [Planification](docs/planning_algo.md) | Calculs de déplacement |
| [Base de données](docs/database_research.md) | Sources pédologiques |
| [Résultats](docs/results.md) | Résultats de tests |
