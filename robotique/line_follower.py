#!/usr/bin/env python3
"""
TP2 Robotique — Suiveur de ligne à 3 capteurs infrarouges.

Les 3 capteurs IR (gauche / milieu / droite) détectent la réflexion
de la ligne noire sur le sol. Un capteur retourne :
    0 → ligne noire détectée (faible réflexion)
    1 → surface blanche (forte réflexion)

Brochage GPIO (Robot HAT Adeept, connecteur X8) :
    Capteur gauche  (S1) → GPIO22
    Capteur milieu  (S2) → GPIO27
    Capteur droit   (S3) → GPIO17

Table de décision :
    G M D | Action
    ------|--------
    0 0 0 | Aucune ligne → continuer tout droit
    0 0 1 | Ligne à droite → tourner à droite
    0 1 0 | Ligne au centre → tout droit
    0 1 1 | Centre + droite → tourner à droite
    1 0 0 | Ligne à gauche → tourner à gauche
    1 0 1 | Fourche → tout droit (ou comportement spécifique)
    1 1 0 | Gauche + centre → tourner à gauche
    1 1 1 | Trois capteurs → tout droit
"""

import time
from gpiozero import InputDevice

# --- Brochage ---
LINE_PIN_LEFT = 22
LINE_PIN_MIDDLE = 27
LINE_PIN_RIGHT = 17

# --- Capteurs ---
left = InputDevice(pin=LINE_PIN_LEFT)
middle = InputDevice(pin=LINE_PIN_MIDDLE)
right = InputDevice(pin=LINE_PIN_RIGHT)


def lire_capteurs():
    """Lit les 3 capteurs. Retourne (gauche, milieu, droite)."""
    return left.value, middle.value, right.value


def decision(status_left, status_middle, status_right):
    """
    Logique de décision du suiveur de ligne.
    Retourne l'action à effectuer : 'tout_droit', 'gauche', 'droite'.
    """
    if status_middle == 0:
        # Le capteur central détecte la ligne
        if status_left == 0 and status_right == 1:
            return "droite"
        elif status_left == 1 and status_right == 0:
            return "gauche"
        else:
            return "tout_droit"
    else:
        # Le capteur central ne détecte pas la ligne
        if status_left == 0 and status_right == 1:
            return "droite"
        elif status_left == 1 and status_right == 0:
            return "gauche"
        else:
            return "tout_droit"


def run():
    """Boucle principale de lecture des capteurs."""
    while True:
        sl, sm, sr = lire_capteurs()
        action = decision(sl, sm, sr)
        print(
            f"left: {sl}  middle: {sm}  right: {sr}  →  {action}"
        )
        time.sleep(0.1)


if __name__ == "__main__":
    run()
