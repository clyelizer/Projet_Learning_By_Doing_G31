#!/usr/bin/env python3
"""
executor.py — Module d'exécution des commandes moteur.

Reçoit des commandes de type :
  {"type": "forward",  "duration": 2.75}
  {"type": "rotate",  "direction": "left", "duration": 0.88}
  {"type": "sample"}

Utilise l'API Adeept PiCar-Pro (Move.py) pour piloter les moteurs DC
via le PCA9685 en I2C.
"""

import sys
import os
import time

# ---------------------------------------------------------------------------
# Ajout du chemin vers les modules Adeept (à adapter si l'arborescence change)
# ---------------------------------------------------------------------------
_ADEEPT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "Adeept_PiCar-Pro"
)
if _ADEEPT_DIR not in sys.path:
    sys.path.insert(0, _ADEEPT_DIR)

try:
    import Move as move
except ImportError:
    print("ERREUR : impossible d'importer Move.py depuis Adeept_PiCar-Pro/")
    print("Vérifiez que le dossier Adeept_PiCar-Pro existe et contient Server/Move.py")
    sys.exit(1)

# ---------------------------------------------------------------------------
# État global
# ---------------------------------------------------------------------------
_initialized = False
_default_speed = 40  # vitesse par défaut (0-100)


def init():
    """Initialise les moteurs (à appeler une fois avant d'exécuter un plan)."""
    global _initialized
    if not _initialized:
        move.setup()
        _initialized = True


def cleanup():
    """Arrête les moteurs et libère les ressources."""
    if _initialized:
        move.motorStop()
        move.destroy()


def run_command(cmd, speed=None):
    """
    Exécute une commande unique.

    Paramètres
    ----------
    cmd : dict
        Commande au format {"type": ..., ...}
    speed : int or None
        Vitesse moteur 0-100. Si None, utilise la vitesse par défaut (40).
    """
    if speed is None:
        speed = _default_speed

    cmd_type = cmd["type"]

    if cmd_type == "forward":
        duration = cmd["duration"]
        move.move(speed, 1, "no")
        time.sleep(duration)
        move.motorStop()

    elif cmd_type == "rotate":
        direction = cmd["direction"]  # "left" ou "right"
        duration = cmd["duration"]
        move.move(speed, 1, direction)
        time.sleep(duration)
        move.motorStop()

    elif cmd_type == "sample":
        # L'action sample est déléguée au module arm.py
        from arm import sample as arm_sample
        arm_sample()

    else:
        print(f"Commande inconnue ignorée : {cmd}")


def run_plan(plan, speed=None):
    """
    Exécute une liste complète de commandes.

    Paramètres
    ----------
    plan : list[dict]
        Liste de commandes générée par planner.generate()
    speed : int or None
        Vitesse moteur 0-100.
    """
    init()
    try:
        for i, cmd in enumerate(plan, 1):
            print(f"[{i}/{len(plan)}] {cmd}")
            run_command(cmd, speed=speed)
        print("Plan terminé.")
    except KeyboardInterrupt:
        print("\nInterruption utilisateur — arrêt des moteurs.")
    finally:
        cleanup()


# ---------------------------------------------------------------------------
# Exécution directe (test)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Test executor : avance 1s, rotation gauche 0.5s, arrêt.")
    init()
    try:
        move.move(30, 1, "no")
        time.sleep(1.0)
        move.motorStop()
        time.sleep(0.3)
        move.move(30, 1, "left")
        time.sleep(0.5)
        move.motorStop()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
