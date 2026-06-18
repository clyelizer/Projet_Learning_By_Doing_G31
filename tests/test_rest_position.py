#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rest_position — met tout le robot en position de repos.

Usage :
    python tests/test_rest_position.py
"""

import sys
import time
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from executor import rest_position, get_controller, cleanup


def main():
    print("🛌 TEST REST POSITION")
    print("=" * 50)
    print("Le robot va avancer 0.5s puis se mettre au repos.")
    print()

    input("Prêt ? Appuie sur ENTRÉE...")

    ctrl = get_controller()
    ctrl.reload_calibration()
    ctrl.set_speed(0.3)
    ctrl.move_forward()
    time.sleep(0.5)

    print("🛌 Rest position...")
    rest_position()

    print()
    print("✅ Vérifie :")
    print("   • Moteurs arrêtés")
    print("   • Roues avant droites")
    print("   • Bras en position neutre")
    print()

    cleanup()


if __name__ == '__main__':
    main()
