# CLAUDE.md — AgroScan (Robot Agricole)

## Structure du projet

```
src/        ← code source (déployé sur le Pi)
├── main.py              ← Orchestrateur (plan → mission → VLM → reco → TTS)
├── planner.py           ← Plan de déplacement
├── executor.py          ← Mouvement moteurs
├── arm.py               ← Bras robotique + sonde sol
├── sensor_arduino.py    ← Capteur sol (pH, EC, T°, humidité)
├── camera.py            ← Capture photo
├── camera_video.py      ← Enregistrement vidéo
├── vlm_analyzer.py      ← Analyse IA des photos (Groq/Gemini)
├── image_processor.py   ← Traitement asynchrone images
├── reco_engine.py       ← Pipeline ML recommandations + NPK
├── tts_engine.py        ← Synthèse vocale multilingue (gTTS + espeak-ng)
├── data_logger.py       ← Agrégation → JSON
├── config_loader.py     ← Configuration
├── web/                 ← Dashboard SPA Flask
│   └── static/          ← index.html, app.js, style.css
├── doctor/              ← Robot Doctor (diagnostic + auto-healing)
│   ├── __init__.py
│   ├── engine.py        ← Orchestrateur (checks → Qwen → heal)
│   ├── checks.py        ← 12 tests hardware/software
│   ├── healer.py        ← Correctifs automatiques
│   ├── prompts.py       ← Prompts pour Qwen Code
│   └── state.py         ← Capture état système
└── ml/                  ← Pipeline ML
    ├── 01_databases/    ← base_reference_agricole.json (41 cultures)
    ├── 02_models/       ← Modèles .pkl (RF, XGBoost, régresseurs N/P/K)
    │   └── best/        ← Meilleurs modèles (sélection automatique)
    ├── 03_training/     ← Scripts d'entraînement + métriques
    ├── 04_figures/      ← Visualisations
    └── 05_recommendation/  ← Algorithme de classement

config/     ← map.json, calibration.json
tests/      ← tests unitaires + hardware
data/       ← photos, results.json, audio/
docs/       ← documentation
plans/      ← notes de développement
```

## Règles Générales

- **Simplicité avant tout.** Pas de classes inutiles, pas de sur-engineering.
- **Pas de code mort.** Si ce n'est pas utilisé, supprime-le.
- **Commentaires utiles seulement.** Explique le *pourquoi*, pas le *quoi* (le code parle de lui-même).
- **Constantes nommées** — pas de nombres magiques.
- **Responsabilité unique** — chaque module fait une chose et une seule.
- **PEP8** — respect strict (sauf exceptions documentées).
- **Test manuel possible** — chaque module doit pouvoir s'exécuter en `if __name__ == '__main__'`.
- **Pas de suppositions** — le capteur sol est documenté dans `sensor_arduino.py` et ses tests.

## Hardware / PCA9685

- **Adresse I2C** : `0x5f` (PCA9685 unique)
- **Fréquence PWM** : 50 Hz (période 20 ms)
- **Allocation des channels** (NE PAS DÉVIER) :

| Channel | Usage |
|---------|-------|
| 0       | Servo direction roues avant |
| 1       | Base rotation bras |
| 2       | Épaule bras |
| 3       | Coude bras |
| 4       | Sonde capteur sol (remplace la pince) |

- **Moteurs arrière** (2WD) : pilotés par pont en H via PCA9685, canaux **CH12–CH15**.
  → M1 gauche : IN1=CH14, IN2=CH15
  → M2 droite : IN1=CH13, IN2=CH12
  → Ne JAMAIS utiliser les channels 0-4 pour les moteurs (conflit avec direction + bras).

## Capteur Sol (`src/sensor_arduino.py`)

- **Architecture** : Arduino Uno + MAX485 fait le pont RS485/Modbus, le RPi lit via USB série
- **Port** : `/dev/ttyACM0`, 9600 baud
- **Format** : texte français multi-lignes (Humidité %, Température °C, EC µS/cm, pH)
- **Données retournées** : `{humidity_pct, temperature_c, ec_us_cm, ph, timestamp}`
- **Tests** : `tests/test_sensor_arduino.py` (parseur) + `tests/test_sensor_live.py` (intégration hardware)

## Bras Robotique (`src/arm.py`)

- La pince est remplacée physiquement par le capteur sol.
- Nouvelles fonctions : `lower_probe()` (descendre le capteur dans le sol) et `raise_probe()` (le remonter).
- `perform_sample()` est supprimé — le module ne fait plus de prélèvement avec pince.
- Séquences critiques avec `time.sleep()` adéquat entre chaque étape.

## Caméra (`src/camera.py`)

- Remplace l'ancien `cam.py` (buggé : exécution à l'import, chemin hardcodé).
- Utilise Picamera2. Photos sauvegardées dans `data/photos/`.
- Fallback si picamera2 indisponible (mode simulation).
- Garde `if __name__ == '__main__'` obligatoire.

## Exécuteur (`src/executor.py`)

- **Mouvement uniquement** : rotate, forward, stop.
- **Ne pas importer** `arm`, `sensor_arduino`, ou `camera` dans executor.
- Les moteurs arrière sont sur PCA9685 **CH12–CH15** (pont en H intégré).
- Le channel 0 du PCA9685 est **exclusivement** pour le servo de direction.
- **Rotation = virage en courbe (arc turn), PAS rotation sur place.** Le robot est un 2WD à direction servo avant, pas un tank. `rotate_left()`/`rotate_right()` utilisent le servo de direction + les deux moteurs en marche avant. Ne JAMAIS utiliser des directions opposées sur les moteurs arrière (casse la physique du châssis).

## Modules et Responsabilités

| Module | Responsabilité unique |
|--------|----------------------|
| `src/executor.py` | Mouvement moteurs uniquement |
| `src/arm.py` | Positionnement bras uniquement |
| `src/sensor_arduino.py` | Lecture capteur sol uniquement |
| `src/camera.py` | Capture photo uniquement |
| `src/camera_video.py` | Enregistrement vidéo H264 (module séparé) |
| `src/image_processor.py` | Traitement images (pipeline asynchrone) |
| `src/vlm_analyzer.py` | Analyse IA sol (Groq → Gemini fallback) |
| `src/reco_engine.py` | Pipeline ML : NPK → classement 41 cultures → impact |
| `src/tts_engine.py` | Synthèse vocale (gTTS + espeak-ng, 22 langues) |
| `src/data_logger.py` | Agrégation données mission → JSON |
| `src/planner.py` | Génération plan de déplacement |
| `src/main.py` | Orchestration du pipeline complet |
| `src/web/app.py` | Dashboard Flask (réseau local) |

## Style de Code

```python
# Bien — constantes nommées
MOTOR_LEFT_FORWARD = 17  # GPIO 17

# Mal — nombres magiques
self.gpio.output(17, True)
```

- `try/except` avec `ImportError` pour les libs optionnelles (simulation sans hardware).
- Pattern singleton simple, pas de dépendances lourdes.

## Workflow

1. Analyser le problème avant d'écrire du code.
2. Écrire le minimum viable.
3. Tester avec le `__main__` de chaque module.
4. Ne jamais faire de correction "à la va vite".
