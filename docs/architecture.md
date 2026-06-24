# Architecture — AgroScan

> Architecture actuelle du robot agricole autonome (Juin 2026).

## 1. Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────┐
│                       main.py (Orchestrateur)                │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Planner  │ Executor │ Arm      │ Camera   │ Data Logger     │
│ (plan)   │ (move)   │ (probe)  │ (photos) │ (JSON)          │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                   Pipeline IA (asynchrone)                    │
├────────────────────┬─────────────────────┬───────────────────┤
│ VLM Analyzer       │ Reco Engine         │ TTS Engine        │
│ (photo → sol)      │ (ML → recommand.)   │ (texte → audio)   │
├────────────────────┴─────────────────────┴───────────────────┤
│                   Dashboard Web (Flask SPA)                   │
│  / → /api/results → /api/recommendations → /api/ml/*         │
└──────────────────────────────────────────────────────────────┘
```

## 2. Pipeline de mission (main.py)

```
[1/4] Lancement serveur web (arrière-plan)
      Plan de déplacement (planner.py)
[2/4] Vérification / dry-run
[3/4] Pour chaque waypoint :
        1. Se déplacer (executor.py)
        2. Sonder le sol (arm.py + sensor_arduino.py)
        3. Photos (camera.py) → traitement asynchrone (image_processor.py)
        Ensuite :
        4. Analyse VLM (vlm_analyzer.py)
        5. Recommandations ML (reco_engine.py)
        6. TTS par zone (tts_engine.py)
      Sauvegarde finale (data_logger.py)
      Cleanup matériel
[4/4] TTS final sur le robot (synthèse globale)
```

## 3. Modules

| Module | Fichier | Responsabilité |
|--------|---------|----------------|
| **Planner** | `src/planner.py` | Calcule angles, distances, durées depuis `map.json` |
| **Executor** | `src/executor.py` | Mouvement uniquement (rotate, forward, stop) |
| **Arm** | `src/arm.py` | Bras : descente/remontée sonde, reset position |
| **Sensor** | `src/sensor_arduino.py` | Lecture pH, EC, T°, humidité via Arduino RS485 |
| **Camera** | `src/camera.py` | Capture photos (Picamera2), fallback simulation |
| **VLM** | `src/vlm_analyzer.py` | Analyse IA des photos (Groq → Gemini fallback) |
| **Image Processor** | `src/image_processor.py` | Traitement asynchrone (file + thread) |
| **Reco Engine** | `src/reco_engine.py` | Pipeline ML : NPK → classement 41 cultures → impact |
| **TTS Engine** | `src/tts_engine.py` | Synthèse vocale (gTTS en ligne, espeak-ng offline) |
| **Data Logger** | `src/data_logger.py` | Agrégation mission → `data/results.json` |
| **Orchestrateur** | `src/main.py` | Pipeline complet (plan → mission → IA → TTS → serveur) |
| **Dashboard** | `src/web/app.py` | SPA Flask, 6 onglets, API REST |

## 4. Pipeline ML

```
EDA (eda_preprocessing.py)
  → dataset_preprocessed.csv (1697 lignes, 14 colonnes)
  → 4 figures (histogrammes, boxplots, heatmap, pairplot)
  → splits train/val/test (70/15/15)

Entraînement (model_training.py)
  → Classifieur (RandomForest / XGBoost) → prédit la culture
  → Régresseurs N, P, K (RandomForest / XGBoost) → estime les nutriments
  → Meilleurs modèles copiés dans best/ (sélection auto par métriques)

Recommandation (recommendation_ranking.py)
  → Scorer 41 cultures par similarité (pH, NPK, T°, humidité, EC)
  → Top N cultures avec scores
  → Graphiques d'impact par paramètre
```

## 5. Dashboard Web (SPA)

| Route API | Description |
|-----------|-------------|
| `GET /` | Page SPA (index.html) |
| `GET /api/results` | Données mission (results.json) |
| `GET /api/recommendations?lang=fr` | Recommandations + TTS |
| `POST /api/reco/analyze` | Analyse interactive (sliders → NPK → classement) |
| `GET /api/base-reference` | Base 41 cultures (filtres zone/recherche) |
| `GET /api/ml/models` | Liste modèles .pkl |
| `GET /api/ml/figures` | Liste figures PNG |
| `GET /api/ml/metrics` | Métriques d'entraînement |
| `POST /api/ml/predict` | Prédiction avec paramètres personnalisés |
| `GET /audio/<file>` | Fichiers audio TTS |
| `GET /photos/<file>` | Photos de mission |

## 6. Synthèse vocale (TTS)

- **gTTS** (online — prioritaire) : fr, en, ha, sw, af, am, ar
- **espeak-ng** (offline — fallback) : + yo, ig, zu, xh, st, tn, sn, rw, so, bm, wo, ff
- **22 langues dont 18 africaines** — sélectionnables dans le dashboard

## 7. Matériel

- Raspberry Pi 5/4B/3B+
- Adeept PiCar Pro V2.0 (2WD + bras 4-DOF)
- Capteur sol 4-en-1 via Arduino + MAX485 (RS485/Modbus → USB série)
- Caméra Picamera2 (CSI ou USB)
- Batterie 7.4V + 2× 18650

## 8. Canaux PCA9685

| Canal | Usage |
|-------|-------|
| 0 | Servo direction roues avant |
| 1-3 | Bras robotique |
| 4 | Sonde capteur sol |
| 12-15 | Moteurs DC (pont en H) |
