#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic braquage — compare gauche et droite étape par étape.

Le servo bouge de 5° en 5° pour trouver le vrai range mécanique.
Écoute si ça grince ou force.

Usage :
    python tests/test_steering_diag.py
"""

import sys
import time
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from executor import get_controller, cleanup


def main():
    ctrl = get_controller()
    ctrl.reload_calibration()

    center = ctrl._center
    left_max = ctrl._max_left
    right_max = ctrl._max_right

    print("🔧 DIAG BRAQUAGE — Balayage progressif")
    print("=" * 50)
    print(f"Centre : {center}°")
    print(f"Gauche : {left_max}°")
    print(f"Droite : {right_max}°")
    print()
    print(" Observe les roues ET écoute le servo.")
    print(" Dès que ça grince ou force → angle max atteint.")
    print()

    # Balayage gauche (de center vers left_max)
    input("1) BALAYAGE GAUCHE. Prêt ? ENTRÉE...")
    for angle in range(center, left_max - 2, -5):
        ctrl._set_steering(angle)
        print(f"   → {angle}°", end='\r')
        time.sleep(0.5)
    ctrl._set_steering(left_max)
    print(f"\n   → Gauche max : {left_max}°")
    time.sleep(1)
    input("   Le servo force-t-il ? (grincement ?) ")
    ctrl.center_steering()
    time.sleep(1)
    print()

    # Balayage droite (de center vers right_max)
    input("2) BALAYAGE DROITE. Prêt ? ENTRÉE...")
    for angle in range(center, right_max + 2, 5):
        ctrl._set_steering(angle)
        print(f"   → {angle}°", end='\r')
        time.sleep(0.5)
    ctrl._set_steering(right_max)
    print(f"\n   → Droite max : {right_max}°")
    time.sleep(1)
    input("   Le servo force-t-il ? (grincement ?) ")
    ctrl.center_steering()
    time.sleep(1)
    print()

    # Test centrage après chaque position
    print("3) TEST CENTRAGE après chaque position")
    for label, angle in [("Gauche max", left_max),
                          ("Mi-gauche", center - 25),
                          ("Centre", center),
                          ("Mi-droite", center + 25),
                          ("Droite max", right_max)]:
        ctrl._set_steering(angle)
        time.sleep(0.5)
        print(f"   Braqué à {label} ({angle}°)", end='')
        ctrl.center_steering()
        time.sleep(0.5)
        print(f" → centré ✅")

    print()
    print("✅ Diagnostic terminé")
    print(" Si le servo force à droite, réduis 'max_right_deg'")
    print(" Si le servo force à gauche, réduis 'max_left_deg'")

    cleanup()


if __name__ == '__main__':
    main()
