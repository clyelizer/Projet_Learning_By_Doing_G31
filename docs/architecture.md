# Architecture — Robot 2WD + Bras + Capteur Sol + Vision

> Plan d'architecture pour la refonte du pipeline autonome.
> Date: 2026-06-12

---

## 1. État Actuel — Problèmes Identifiés

### 1.1 Violations de responsabilité unique

| Fichier | Problème |
|---------|----------|
| [`MAIN/executor.py`](../MAIN/executor.py#L170-L172) | Importe `arm` et appelle `arm.perform_sample()` → l'exécuteur ne doit gérer que le mouvement |
| [`MAIN/cam.py`](../MAIN/cam.py#L11) | `take()` exécuté à l'import, pas sous `if __name__` |
| [`MAIN/cam.py`](../MAIN/cam.py#L8) | Chemin absolu hardcodé `/home/kit13/Desktop/image.jpg` |

### 1.2 Conflits de canaux PCA9685

| Canal | [`arm.py`](../MAIN/arm.py#L21) | [`materiel.md`](../MD/materiel.md#L146) | Statut |
|-------|-----------|---------------|--------|
| CH0 | *(réservé commentaire)* | Direction | OK |
| CH1 | `base` (rotation bras) | Servo ultrason | ⚠️ Conflit futur |
| CH2 | `shoulder` | Coude | ⚠️ Libellés inversés |
| CH3 | `elbow` | Épaule | ⚠️ Libellés inversés |
| CH4 | `gripper` | Pince | OK (sera déprécié) |
| CH12-13 | Moteur M2 droite | Moteur M2 droite | OK |
| CH14-15 | Moteur M1 gauche | Moteur M1 gauche | OK |

### 1.3 Module caméra cassé

- Exécution à l'import (pas de garde `if __name__`)
- Chemin absolu machine-spécifique
- Aucune gestion d'erreur
- Pas de fallback simulation
- Headers manquants (`#!/usr/bin/env python3`, encoding)

---

## 2. Architecture Cible

### 2.1 Arborescence

```
MAIN/
├── main.py                  Orchestrateur (point d'entrée, pipeline complet)
├── planner.py               Planification (étendu pour nouveaux champs waypoint)
├── executor.py              Mouvement UNIQUEMENT (rotate, forward, stop)
├── arm.py                   Bras robotique (lower_probe, raise_probe, reset_position)
├── sensor_arduino.py      NEW  Capteur sol via Arduino (USB série)
├── camera.py                Capture photo Picamera2 (réécriture de cam.py)
├── image_processor.py  NEW  Traitement images (pipeline vers modèle IA)
├── data_logger.py      NEW  Agrégation données mission → JSON

Config/
├── map.json                 Étendu: champs "probe" et "photos" par waypoint
├── calibration.json         Étendu: constantes capteur/caméra

Results/
├── *.jpg                    Photos capturées
├── results.json             Données agrégées de mission
```

### 2.2 Flux de données par waypoint

```
Pour chaque waypoint:
  1. executor.rotate(direction, duration)
  2. executor.forward(duration)
  3. arm.lower_probe()           → insère le capteur dans le sol
  4. sensor_arduino.read_sensor()  → {humidity_pct, temperature_c, ec_us_cm, ph, timestamp}
  5. arm.raise_probe()           → retire le capteur
  6. camera.take_photos(n)       → ['Results/wp1_001.jpg', ...]
  7. data_logger.log(wp_id, data, paths)
  8. image_processor.enqueue(paths, wp_id)  → traitement asynchrone

Après tous les waypoints:
  9. image_processor.wait_all()
 10. data_logger.save_final()
```

### 2.3 Principe: chaque module fait UNE chose

| Module | Responsabilité unique |
|--------|----------------------|
| `executor.py` | Mouvement moteurs uniquement |
| `arm.py` | Positionnement bras uniquement |
| `sensor_arduino.py` | Lecture capteur sol uniquement |
| `camera.py` | Capture photo uniquement |
| `image_processor.py` | Traitement images uniquement |
| `data_logger.py` | Stockage données uniquement |
| `planner.py` | Génération plan uniquement |
| `main.py` | Orchestration uniquement |

---

## 3. Spécifications des Modules

### 3.1 [`sensor_arduino.py`](../src/sensor_arduino.py) — Capteur Sol

Le capteur sol (4-en-1: humidité, température, EC, pH) est connecté via un Arduino Uno + MAX485 qui fait le pont RS485/Modbus. Le Raspberry Pi lit les données via USB série.

- **Port**: `/dev/ttyACM0`, 9600 baud
- **Format**: texte français multi-lignes parsé par `_parse_arduino_output()`
- **Données retournées**: `{humidity_pct, temperature_c, ec_us_cm, ph, timestamp}`
- **Fallback**: Si `pyserial` non disponible → retourne `None` + warning

### 3.2 [`camera.py`](../MAIN/camera.py) — Capture Photo

Réécriture complète de [`cam.py`](../MAIN/cam.py) avec:
- Garde `if __name__ == '__main__'`
- Chemin relatif vers `Results/`
- Fallback si picamera2 indisponible
- Headers standard

### 3.3 [`arm.py`](../MAIN/arm.py) — Bras Robotique (modifié)

**Supprimé**: `open_gripper()`, `close_gripper()`, `perform_sample()`
**Ajouté**: `lower_probe()`, `raise_probe()`
**Conservé**: `reset_position()`, `get_arm()`, `cleanup()`

Le capteur NPK remplace physiquement la pince.

### 3.4 [`executor.py`](../MAIN/executor.py) — Mouvement (simplifié)

**Supprimé**: `import arm` et l'appel `arm.perform_sample()` dans `run()`
**Conservé**: `MotorController`, `run()` pour 'rotate' et 'forward' uniquement

### 3.5 [`image_processor.py`](../MAIN/image_processor.py) — Traitement Images (NOUVEAU)

Pipeline de traitement asynchrone:
- File d'attente (`queue.Queue`)
- Thread d'arrière-plan
- Placeholder pour le modèle IA (à définir)
- Sauvegarde des résultats par image

### 3.6 [`data_logger.py`](../MAIN/data_logger.py) — Journal de Mission (NOUVEAU)

Structure JSON de sortie:
```json
{
  "mission": {"start_time": "...", "end_time": "...", "waypoint_count": 2},
  "waypoints": [
    {
      "id": 1, "x": 60, "y": 40,
      "sensor": {"humidity_pct": 45.2, "temperature_c": 22.1, "ec_ms_cm": 1.2, "ph": 6.8},
      "photos": ["wp1_001.jpg", "wp1_002.jpg", "wp1_003.jpg"],
      "image_results": [{"file": "wp1_001.jpg", "model_output": {...}}, ...]
    }
  ]
}
```

### 3.7 [`planner.py`](../MAIN/planner.py) — Planification (étendu)

Gère les nouveaux champs waypoint: `probe` (bool) et `photos` (int).

### 3.8 [`main.py`](../MAIN/main.py) — Orchestrateur (restructuré)

Pipeline complet: plan → mouvement → acquisition → logging → processing → finalisation.

---

## 4. Fichiers de Configuration Étendus

### 4.1 [`map.json`](../Config/map.json)

```json
{
  "table": {"width_cm": 150, "height_cm": 100},
  "start": {"x": 10, "y": 10, "heading_deg": 0},
  "waypoints": [
    {"id": 1, "x": 60, "y": 40, "probe": true, "photos": 3},
    {"id": 2, "x": 120, "y": 70, "probe": true, "photos": 3}
  ]
}
```

### 4.2 [`calibration.json`](../Config/calibration.json)

```json
{
  "cm_per_sec": 20,
  "deg_per_sec": 36,
  "photo_count": 3,
  "photo_delay_s": 0.5,
  "probe_pause_s": 1.5,
  "sensor_port": "/dev/ttyS0",
  "sensor_baudrate": 9600
}
```

---

## 5. Ordre d'Implémentation

| # | Tâche | Fichier | Action |
|---|-------|---------|--------|
| 1 | Réécrire caméra | `MAIN/cam.py` → `MAIN/camera.py` | Corriger tous les bugs |
| 2 | Créer capteur sol | `src/sensor_arduino.py` | Arduino + MAX485 bridge |
| 3 | Modifier bras | `MAIN/arm.py` | Remplacer pince par sonde |
| 4 | Simplifier exécuteur | `MAIN/executor.py` | Retirer `import arm` |
| 5 | Étendre planificateur | `MAIN/planner.py` | Nouveaux champs waypoint |
| 6 | Créer processeur image | `MAIN/image_processor.py` | Pipeline asynchrone |
| 7 | Créer logger données | `MAIN/data_logger.py` | Agrégation JSON |
| 8 | Restructurer orchestrateur | `MAIN/main.py` | Nouveau pipeline |
| 9 | Étendre configuration | `Config/map.json`, `Config/calibration.json` | Nouveaux champs |
| 10 | Mettre à jour docs | `README.md`, `MD/*.md`, `CLAUDE.md` | Refléter nouvelle archi |
