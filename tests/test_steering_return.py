#!/usr/bin/env python3
import sys, time, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from executor import get_controller, cleanup

ctrl = get_controller()
ctrl.reload_calibration()
c, l, r = ctrl._center, ctrl._max_left, ctrl._max_right
print(f"Centre={c}° Gauche={l}° Droite={r}°\n")

input("Droite max...")
ctrl._set_steering(r)
time.sleep(1)

input("Tout droit...")
ctrl._set_steering(c)
time.sleep(0.5)

input(f"Gauche {c-50}°...")
ctrl._set_steering(c - 50)
time.sleep(0.5)

input("Tout droit...")
ctrl._set_steering(c)
time.sleep(0.5)

print("Fait")
cleanup()
