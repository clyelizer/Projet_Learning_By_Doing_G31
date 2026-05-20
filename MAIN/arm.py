#!/usr/bin/env python3
"""
arm.py — Contrôle du bras robotique 4-DOF (Adeept PiCar-Pro).

Gère la séquence de prélèvement :
  descendre → pause → remonter

Utilise l'API ServoCtrl (RPIservo.py) pour piloter les servomoteurs
via le PCA9685 en I2C.
"""

import sys
import os
import time

# ---------------------------------------------------------------------------
# Ajout du chemin vers les modules Adeept
# ---------------------------------------------------------------------------
_ADEEPT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "Adeept_PiCar-Pro"
)
if _ADEEPT_DIR not in sys.path:
    sys.path.insert(0, _ADEEPT_DIR)

try:
    import RPIservo
except ImportError:
    print("ERREUR : impossible d'importer RPIservo.py depuis Adeept_PiCar-Pro/")
    print("Vérifiez que le dossier Adeept_PiCar-Pro existe et contient Server/RPIservo.py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration des servos du bras
# ---------------------------------------------------------------------------
# Mapping des servos (index 0-7 sur le PCA9685) :
#   0 : rotation base / caméra pan
#   1 : épaule (shoulder)
#   2 : coude (elbow) — c'est le servo principal pour descendre/remonter
#   3 : poignet (wrist)
#   4 : pince (gripper)

SERVO_ELBOW = 2       # servo utilisé pour le mouvement vertical du bras
ANGLE_DOWN = -45       # angle relatif (degrés) pour descendre
ANGLE_UP = 0           # angle relatif pour remonter (position neutre)
PAUSE_DURATION = 1.0   # temps de pause en position basse (secondes)
MOVE_DELAY = 1.5       # délai pour laisser le servo atteindre sa position

# ---------------------------------------------------------------------------
# Instance globale du contrôleur de servos
# ---------------------------------------------------------------------------
_sc = None
_initialized = False


def init():
    """Initialise le contrôleur de servos (à appeler une fois)."""
    global _sc, _initialized
    if not _initialized:
        _sc = RPIservo.ServoCtrl()
        _sc.moveInit()
        _sc.start()
        _initialized = True
        time.sleep(0.3)


def cleanup():
    """Replace le bras en position neutre et arrête le thread servo."""
    global _sc, _initialized
    if _initialized and _sc is not None:
        _sc.moveAngle(SERVO_ELBOW, ANGLE_UP)
        time.sleep(0.5)
        # Le thread ServoCtrl tourne en boucle, on le laisse pour
        # d'éventuelles autres utilisations. Pour un arrêt complet
        # il faudrait un mécanisme de sortie explicite.
    _initialized = False


def sample():
    """
    Exécute la séquence de prélèvement :
      1. Descendre le bras
      2. Pause (simule la prise d'échantillon)
      3. Remonter le bras
    """
    init()

    print("  Bras → descente")
    _sc.moveAngle(SERVO_ELBOW, ANGLE_DOWN)
    time.sleep(MOVE_DELAY)

    print("  Bras → prélèvement en cours...")
    time.sleep(PAUSE_DURATION)

    print("  Bras → remontée")
    _sc.moveAngle(SERVO_ELBOW, ANGLE_UP)
    time.sleep(MOVE_DELAY)


# ---------------------------------------------------------------------------
# Exécution directe (test)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Test bras : séquence de prélèvement.")
    try:
        sample()
        print("Test terminé.")
    except KeyboardInterrupt:
        print("\nInterruption.")
    finally:
        cleanup()
