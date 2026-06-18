#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test direction — vérifier centrage et angles max de braquage.

1. Centre les roues à 90°
2. Balayage gauche → droite pour vérifier le range
3. Test angle gauche max + droit max

Usage :
    python tests/test_steering.py
"""

import sys
import time
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from executor import get_controller, cleanup


def main():
    ctrl = get_controller()
    ctrl.reload_calibration()

    print("🧭 TEST DIRECTION")
    print("=" * 50)
    print(f"Centre configuré : {ctrl._center}°")
    print(f"Gauche max        : {ctrl._max_left}°")
    print(f"Droite max        : {ctrl._max_right}°")
    print()

    # 1. Centrage
    input("1) Appuie sur ENTRÉE pour centrer les roues à 90°...")
    ctrl.center_steering()
    time.sleep(1)
    print("   Les roues sont-elles bien droites ?")
    print("   Si non, ajuste 'center_deg' dans calibration.json")
    print()

    # 2. Gauche max
    input("2) Appuie sur ENTRÉE pour braquer à gauche max...")
    ctrl._set_steering(ctrl._max_left)
    time.sleep(1.5)
    print(f"   Roues à {ctrl._max_left}° — le servo grince-t-il ?")
    print("   Si oui, réduis 'max_left_deg' dans calibration.json")
    print()

    # 3. Droite max
    input("3) Appuie sur ENTRÉE pour braquer à droite max...")
    ctrl._set_steering(ctrl._max_right)
    time.sleep(1.5)
    print(f"   Roues à {ctrl._max_right}° — le servo grince-t-il ?")
    print("   Si oui, réduis 'max_right_deg' dans calibration.json")
    print()

    # 4. Retour centre
    ctrl.center_steering()
    print("✅ Test terminé. Roues centrées.")

    cleanup()


if __name__ == '__main__':
    main()
