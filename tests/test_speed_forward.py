#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test avance — mesurer cm_per_sec.

Le robot avance 2 secondes à throttle_forward.
Tu mesures la distance parcourue, on calcule cm_per_sec.

Usage :
    python tests/test_speed_forward.py
"""

import sys
import time
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from executor import get_controller, cleanup


DURATION = 5.0


def main():
    ctrl = get_controller()
    ctrl.reload_calibration()
    throttle = ctrl._throttle

    print("📏 TEST AVANCE — Mesure cm_per_sec")
    print("=" * 50)
    print(f"  Throttle : {throttle}")
    print(f"  Durée    : {DURATION} s")
    print()
    print("  Protocole :")
    print("  1. Marque une ligne de départ au sol")
    print(f"  2. Le robot va avancer {DURATION} secondes")
    print("  3. Mesure la distance en cm depuis la ligne de départ")
    print()

    input("Prêt ? Appuie sur ENTRÉE pour lancer le test...")
    print()
    print("🎬 AVANCE !")
    ctrl.move_forward()
    time.sleep(DURATION)
    ctrl.stop_all()
    print("✅ Arrêté.")
    print()

    dist = input("Distance parcourue (cm) : ").strip()
    try:
        d = float(dist)
        calc = round(d / DURATION, 1)
        print(f"\n  📊 Résultat :")
        print(f"     Distance : {d} cm")
        print(f"     Durée    : {DURATION} s")
        print(f"     → cm_per_sec = {calc}")
        print()
        print(f"  Reporte {calc} dans 'cm_per_sec' dans calibration.json")
    except ValueError:
        print("  Pas de valeur enregistrée.")

    cleanup()


if __name__ == '__main__':
    main()
