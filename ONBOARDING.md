# Onboarding — AgroScan

> Projet robot agricole autonome. Raspberry Pi + Adeept PiCar Pro + ML.

## Structure du code

```
src/                          ← À déployer sur le Pi
├── main.py                   ← Point d'entrée (orchestrateur)
├── planner.py                ← Plan de déplacement
├── executor.py               ← Moteurs (rotate, forward, stop)
├── arm.py                    ← Bras + sonde sol
├── sensor_arduino.py         ← Capteur 4-en-1 (pH, EC, T°, humidité)
├── camera.py                 ← Photos
├── camera_video.py           ← Vidéo
├── vlm_analyzer.py           ← Analyse IA des photos
├── image_processor.py        ← Traitement asynchrone
├── reco_engine.py            ← Pipeline ML (NPK → classement)
├── tts_engine.py             ← Synthèse vocale (22 langues)
├── data_logger.py            ← Enregistrement JSON
├── config_loader.py          ← Configuration
├── web/                      ← Dashboard SPA Flask
│   └── static/               ← HTML/CSS/JS
└── ml/                       ← Pipeline Machine Learning
    ├── 01_databases/         ← Base référence + dataset
    ├── 02_models/            ← Modèles .pkl + best/
    ├── 03_training/          ← Scripts + métriques
    ├── 04_figures/           ← Visualisations
    └── 05_recommendation/    ← Algorithme de classement
```

## Pipeline mission complet

1. **Plan** — `planner.py` calcule les mouvements depuis `config/map.json`
2. **Déplacement** — `executor.py` : rotation (virage en courbe) + avance
3. **Son** — `arm.py` descend la sonde, `sensor_arduino.py` lit le sol
4. **Photo** — `camera.py` capture N photos, `image_processor.py` les traite en async
5. **IA** — `vlm_analyzer.py` analyse la photo (Groq), `reco_engine.py` classe les cultures
6. **Audio** — `tts_engine.py` synthétise les recommandations
7. **Log** — `data_logger.py` → `data/results.json`
8. **Web** — Dashboard accessible pendant toute la mission

## Démarrage rapide

```bash
# 1. Cloner
git clone <url> ~/n
cd ~/n

# 2. Installer les dépendances
pip install -r requirements.txt
pip install flask gtts python-dotenv groq

# 3. Configurer les clés API
cp .env.example .env
# Éditer .env avec GROQ_API_KEY

# 4. Lancer une simulation
python src/main.py --dry-run

# 5. Lancer le dashboard seul
python src/web/app.py

# 6. Mission complète
python src/main.py
```

## Dépendances principales

```
requirements.txt : Adafruit_PCA9685, picamera2, pyserial, flask
pip install      : gtts, groq, python-dotenv, joblib, xgboost, scikit-learn
sudo apt install : espeak-ng (pour TTS offline)

.env : GROQ_API_KEY, GEMINI_API_KEY (optionnel)
```

## Dashboard web

Accessible sur `http://<IP_PI>:5000` — 6 onglets :

| Onglet | Route API | Description |
|--------|-----------|-------------|
| Dashboard | `GET /api/results` | Stats + carte SVG |
| Recommandations | `GET /api/recommendations?lang=XX` | Conseils + TTS audio |
| Données | `GET /api/results` | Photos + JSON |
| Test analyse | `POST /api/reco/analyze` | Sliders → NPK → classement |
| Base Réf. | `GET /api/base-reference` | Browse 41 cultures |
| Modèles ML | `GET /api/ml/*` | Figures + métriques + .pkl |

## TTS — Langues disponibles

| Moteur | Langues |
|--------|---------|
| **gTTS** (online) | fr, en, ha, sw, af, am, ar |
| **espeak-ng** (offline) | + yo, ig, zu, xh, st, tn, sn, rw, so, bm, wo, ff |

## Points d'attention

- Les modèles ML doivent être régénérés si le dataset change : `python src/ml/03_training/model_training.py`
- Le port du capteur sol est `/dev/ttyACM0` (pas ttyS0)
- Le dashboard Flask tourne en `debug=True, use_reloader=False`
- La caméra doit être libérée entre les waypoints (`camera.cleanup()`)
