# Codebase Onboarding Report — Projet Robot Agricole G31

> Régénéré 2026-06-17 | Branch `main` | 14 commits

---

## 1. Overview

| Métrique | Valeur |
|----------|--------|
| **Fichiers source** | 11 |
| **Fichiers de test** | 13 |
| **Ratio tests/source** | 118% |
| **Lignes totales** | 3,584 |
| **Language** | Python 3 |
| **Runtime** | Raspberry Pi (aarch64, kernel 6.1.21-v8+) |
| **Dettes** | 1 TODO, calibration.json port erroné |

---

## 2. File Map (by size)

```
src/web/app.py              291   Dashboard Flask
src/vlm_analyzer.py         287   Analyse IA sol (Gemini/Groq)
tests/test_sensor_audit.py  258   Audit chaîne mesure complète
src/main.py                 242   Orchestrateur mission
src/sensor_arduino.py       203   Capteur sol via Arduino
src/executor.py             200   Mouvement moteurs
src/camera_video.py         192   Enregistrement vidéo H264
tests/test_sensor_arduino.py 182  Tests parseur capteur
src/planner.py              174   Génération plan
tests/test_camera.py         167   Tests caméra + image processor
tests/test_vlm_analyzer.py   163   Tests VLM (API réelle)
src/data_logger.py           162   Agrégation JSON
src/image_processor.py       142   Pipeline asynchrone images
tests/test_sensor_live.py    117   Tests hardware capteur
src/camera.py                114   Capture photo
src/arm.py                   114   Bras robotique
tests/test_cam_live.py       100   Tests caméra hardware
tests/test_video_record.py    85   Tests vidéo
tests/test_steering_diag.py   90   Test direction
tests/test_speed_forward.py   66   Test vitesse avant
tests/test_turn_rate.py       65   Test taux rotation
tests/test_steering.py        65   Test direction interactive
tests/test_rest_position.py   46   Test retour position
tests/test_steering_return.py 28   Test compensation jeu mécanique
```

---

## 3. Entry Points

| Fichier | Rôle |
|---------|------|
| `src/main.py` | 🚀 **Principal** — mission autonome complète |
| `src/web/app.py` | 🌐 Dashboard Flask (3 routes) |
| `src/sensor_arduino.py` | 📡 Lecture capteur standalone (`--loop` / `--raw`) |
| `src/camera.py` | 📷 Photo standalone |
| `src/camera_video.py` | 🎥 Vidéo standalone |
| `src/vlm_analyzer.py` | 🧠 Analyse IA standalone |
| `src/data_logger.py` | 💾 Agrégation standalone |
| `src/image_processor.py` | ⚙️ Pipeline standalone |
| `src/planner.py` | 🗺️ Génération plan standalone |
| `src/executor.py` | 🏎️ Test moteurs standalone |
| `src/arm.py` | 🦾 Test bras standalone |

---

## 4. Architecture — Data Flow

```
map.json ──▶ planner ──▶ main (orchestrateur)
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          executor       arm         camera
          (mouvement)  (sonde)    (take_photos)
                           │            │
                           ▼            ▼
                      sensor_arduino  image_processor
                      (read_sensor)   (enqueue async)
                           │            │
                           ▼            ▼
                      ┌─────────────────────┐
                      │     data_logger     │
                      │  log_waypoint()     │
                      │  → results.json     │
                      └─────────────────────┘
```

**Séquence par waypoint** (identique à main.py) :
1. `executor →` déplacement (rotate + forward)
2. `arm.lower_probe()` → descend capteur
3. `time.sleep(1.5)` → stabilisation
4. `sensor_arduino.read_sensor(port, baudrate)` → mesure 4-en-1
5. `arm.raise_probe()` + `arm.reset_position()` → remonte
6. `camera.take_photos(n)` → capture photos sol
7. `image_processor.enqueue(paths, wp_id)` → traitement asynchrone
8. `data_logger.log_waypoint(wp_id, sensor, paths)` → enregistrement

---

## 5. Module Summary

| Module | Lignes | Classes | Responsabilité |
|--------|--------|---------|----------------|
| `main.py` | 242 | 0 | Orchestration pipeline complet |
| `executor.py` | 200 | `Executor` | Moteurs 2WD : forward, rotate, stop |
| `arm.py` | 114 | `ArmController` | Bras 4-DOF : lower_probe, raise_probe, reset_position |
| `sensor_arduino.py` | 203 | 0 | Lecture capteur via Arduino USB : `read_sensor()`, `_parse_arduino_output()` |
| `camera.py` | 114 | 0 | Photo uniquement : `take_photos(n)`, `cleanup()` |
| `camera_video.py` | 192 | 0 | Vidéo H264 : `record_video(duration)`. Module séparé |
| `image_processor.py` | 142 | `ImageProcessor` | File d'attente asynchrone : `enqueue()`, `wait_all()`, `get_results()` |
| `data_logger.py` | 162 | `DataLogger` | Agrégation : `log_waypoint()`, `save_final()` → `data/results.json` |
| `vlm_analyzer.py` | 287 | 0 | Analyse IA sol : Gemini 2.0 Flash → Groq Llama 4 Scout (fallback) |
| `planner.py` | 174 | 0 | Plan de mission : `generate_plan()`, `calculate_movement()` |
| `web/app.py` | 291 | 0 | Dashboard Flask : `/` (carte SVG), `/data` (photos), `/recommandations` (conseils) |

---

## 6. Hardware Architecture

```
Capteur sol 4-en-1 ←─RS485─→ MAX485 ←─TTL─→ Arduino Uno
                                                 │
                                             USB (/dev/ttyACM0)
                                                 │
                                             Raspberry Pi
                                                 │
                               ┌─────────────────┼──────────────────┐
                               ▼                 ▼                  ▼
                         PCA9685 (0x5f)    Picamera2       USB Webcam
                               │            (libcamera)     (Atlantis)
                         ┌─────┴─────┐
                         ▼           ▼
                    Servo dir    Bras 4-DOF
                    (CH0)        (CH1-4)
                         │
                    Moteurs 2WD
                    (CH12-15)
```

| Composant | Détail |
|-----------|--------|
| **PCA9685** | I²C 0x5f, PWM 50 Hz, CH0-15 |
| **Moteurs** | 2WD arrière, pont en H, CH12-15 |
| **Direction** | Servo avant, CH0 |
| **Bras** | 4-DOF : base (CH1), épaule (CH2), coude (CH3), sonde (CH4) |
| **Caméra** | USB Atlantis, 640×480 MJPEG, via Picamera2/libcamera |
| **Capteur sol** | 4-en-1 (humidité %, température °C, EC µS/cm, pH) via Arduino + MAX485 |
| **Vidéo** | Module séparé `camera_video.py` — H264 via Picamera2 encoder ou ffmpeg V4L2 fallback |

---

## 7. Dependencies

```
requirements.txt:
  Adafruit_PCA9685    — PWM servos + moteurs
  picamera2           — Capture photo/vidéo (libcamera)
  pyserial            — USB série Arduino
  flask               — Dashboard web

.env:
  GEMINI_API_KEY      — Google AI Studio (Gemini 2.0 Flash)
  GROQ_API_KEY        — Groq Cloud (Llama 4 Scout)

Standard Library:
  json, os, sys, time, signal, argparse, math, threading, queue,
  re, pathlib, base64, subprocess
```

---

## 8. Configuration

| Fichier | Contenu |
|---------|---------|
| `config/map.json` | Départ + waypoints (x, y, action, n_photos) |
| `config/calibration.json` | Vitesses, délais, ports série, angles servo |
| `.env` | Clés API (⚠️ ne pas commiter) |
| `.env.example` | Template variables |

---

## 9. Test Coverage

| Suite | Fichier | Type | Tests |
|-------|---------|------|-------|
| **Capteur** | `test_sensor_arduino.py` | Unitaire parseur | 14 |
| | `test_sensor_live.py` | Intégration hardware | 3 |
| | `test_sensor_audit.py` | Audit chaîne complète | manuel |
| **Caméra** | `test_camera.py` | Hardware + image processor | 16 |
| | `test_cam_live.py` | Caméra hardware | — |
| **Vidéo** | `test_video_record.py` | Vidéo hardware | — |
| **VLM** | `test_vlm_analyzer.py` | API réelle (skip par défaut) | 10 |
| **Mouvement** | `test_steering*.py` (×4), `test_rest*.py`, `test_speed*.py`, `test_turn*.py` | Interactif | 6 |

**Commandes :**
```bash
pytest tests/test_sensor_arduino.py tests/test_camera.py -v   # sans hardware
pytest tests/ -v                                               # tout (hardware requis)
RUN_VLM=1 pytest tests/test_vlm_analyzer.py -v                # API (quota !)
python tests/test_sensor_audit.py --loop                       # audit chaîne mesure
```

---

## 10. Points d'Attention

| # | Fichier | Problème | Sévérité |
|---|---------|----------|----------|
| 1 | `config/calibration.json:8` | `sensor_port: "/dev/ttyS0"` — devrait être `/dev/ttyACM0` | 🟡 |
| 2 | `src/web/app.py` | `debug=True` (console Werkzeug exposée). `use_reloader=False` corrige le crash au démarrage | 🟡 |
| 3 | `.env` | 3 clés API inutilisées (CEREBRAS, MISTRAL, DEEPSEEK) | 🟡 |
| 4 | `src/image_processor.py:69` | TODO : placeholder → appel IA réel (`vlm_analyzer.analyze_soil_ia()`) | 🟡 |
| 5 | `src/image_processor.py` | Pas de méthode `stop()` — thread daemon tourne indéfiniment | 🟡 |
| 6 | `src/executor.py` + `arm.py` | `cleanup()` ne ferme pas le PCA9685 | 🟡 |

### ✅ Corrigé récemment

| Date | Correction |
|------|-----------|
| 2026-06-17 | `executor.py` — mapping moteurs IN1/IN2 inversé corrigé (M1: 15,14 / M2: 12,13) |
| 2026-06-17 | `main.py` — `sensor_npk` → `sensor_arduino`, port `ttyS0` → `ttyACM0` |
| 2026-06-17 | `web/` — dashboard responsive (mobile-first, hamburger menu, CSS custom properties) |

---

## 11. Derniers Commits

```
a0ef1b2 — implémentation (piquer sol, mesurer, photos, modèle)
aa85482 — fix adresse PCA9685 (0x5f)
0333b1e — edit main.py pour map + config
bcb3215 — soumission fichiers MD
7047ae9 — création dossier database + fiche technique
```
