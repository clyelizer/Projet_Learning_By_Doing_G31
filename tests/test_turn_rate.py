#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test virage — mesurer deg_per_sec.

Le robot tourne à fond à gauche pendant 2 secondes.
Tu estimes l'angle parcouru, on calcule deg_per_sec.

Usage :
    python tests/test_turn_rate.py
"""

import sys
import time
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from executor import get_controller, cleanup


DURATION = 2.0


def main():
    ctrl = get_controller()
    ctrl.reload_calibration()

    print("🔄 TEST VIRAGE — Mesure deg_per_sec")
    print("=" * 50)
    print(f"  Durée    : {DURATION} s")
    print()
    print("  Protocole :")
    print("  1. Dégage la zone devant le robot")
    print(f"  2. Le robot va tourner à gauche {DURATION} secondes")
    print("  3. Estime l'angle dont il a tourné")
    print("     (90° = quart de tour, 180° = demi-tour, 360° = tour complet)")
    print()

    input("Prêt ? Appuie sur ENTRÉE pour lancer le test...")
    print()
    print("🎬 VIRAGE !")
    ctrl.rotate(90, 'left')
    time.sleep(DURATION)
    ctrl.stop_all()
    print("✅ Arrêté.")
    print()

    angle = input("Angle observé approximatif (deg) : ").strip()
    try:
        a = float(angle)
        calc = round(a / DURATION, 1)
        print(f"\n  📊 Résultat :")
        print(f"     Angle : {a}°")
        print(f"     Durée : {DURATION} s")
        print(f"     → deg_per_sec = {calc}")
        print()
        print(f"  Reporte {calc} dans 'deg_per_sec' dans calibration.json")
    except ValueError:
        print("  Pas de valeur enregistrée.")

    cleanup()


if __name__ == '__main__':
    main()
