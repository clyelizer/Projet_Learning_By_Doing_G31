# CLAUDE.md — Projet Robot 2WD + Bras + NPK + Vision

## Règles Générales

- **Simplicité avant tout.** Pas de classes inutiles, pas de sur-engineering.
- **Pas de code mort.** Si ce n'est pas utilisé, supprime-le.
- **Commentaires utiles seulement.** Explique le *pourquoi*, pas le *quoi* (le code parle de lui-même).
- **Constantes nommées** — pas de nombres magiques.
- **Responsabilité unique** — chaque module fait une chose et une seule.
- **PEP8** — respect strict (sauf exceptions documentées).
- **Test manuel possible** — chaque module doit pouvoir s'exécuter en `if __name__ == '__main__'`.
- **Pas de suppositions** — pour le capteur NPK, se baser uniquement sur le code de référence dans `MAIN/sample/`.

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
| 4       | Pince bras (déprécié — le capteur NPK remplace la pince) |

- **Moteurs arrière** (2WD) : pilotés par pont en H via PCA9685, canaux **CH12–CH15**.
  → M1 gauche : IN1=CH14, IN2=CH15
  → M2 droite : IN1=CH13, IN2=CH12
  → Ne JAMAIS utiliser les channels 0-4 pour les moteurs (conflit avec direction + bras).

## Capteur NPK (`MAIN/sensor_npk.py`)

- **Protocole** : RS485/Modbus RTU sur `/dev/ttyS0`, 9600 baud, 8N1
- **Trame requête** : `[0x01, 0x03, 0x00, 0x00, 0x00, 0x04, 0x44, 0x09]`
- **Données retournées** : Humidité (%), Température (°C), EC (mS/cm), pH
- **Code de référence** : [`MAIN/sample/diagnostic_capteur.py`](MAIN/sample/diagnostic_capteur.py) et [`MAIN/sample/test_capteur.py`](MAIN/sample/test_capteur.py)
- **NE PAS INVENTER** de paramètres ou de trames — utiliser exclusivement ce qui est dans les fichiers sample.

## Bras Robotique (`MAIN/arm.py`)

- La pince est remplacée physiquement par le capteur NPK.
- Nouvelles fonctions : `lower_probe()` (descendre le capteur dans le sol) et `raise_probe()` (le remonter).
- `perform_sample()` est supprimé — le module ne fait plus de prélèvement avec pince.
- Séquences critiques avec `time.sleep()` adéquat entre chaque étape.

## Caméra (`MAIN/camera.py`)

- Remplace l'ancien `MAIN/cam.py` (buggé : exécution à l'import, chemin hardcodé).
- Utilise Picamera2. Photos sauvegardées dans `Results/`.
- Fallback si picamera2 indisponible (mode simulation).
- Garde `if __name__ == '__main__'` obligatoire.

## Exécuteur (`MAIN/executor.py`)

- **Mouvement uniquement** : rotate, forward, stop.
- **Ne pas importer** `arm`, `sensor_npk`, ou `camera` dans executor.
- Les moteurs arrière sont sur PCA9685 **CH12–CH15** (pont en H intégré).
- Le channel 0 du PCA9685 est **exclusivement** pour le servo de direction.

## Modules et Responsabilités

| Module | Responsabilité unique |
|--------|----------------------|
| `executor.py` | Mouvement moteurs uniquement |
| `arm.py` | Positionnement bras uniquement |
| `sensor_npk.py` | Lecture capteur sol uniquement |
| `camera.py` | Capture photo uniquement |
| `image_processor.py` | Traitement images (pipeline asynchrone) |
| `data_logger.py` | Agrégation données mission → JSON |
| `planner.py` | Génération plan de déplacement |
| `main.py` | Orchestration du pipeline complet |

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
