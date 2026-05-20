#!/usr/bin/env python3
"""
planner.py — Module de planification du robot autonome.

Lit map.json et calibration.json, puis génère une liste de commandes
exploitables par l'exécuteur moteur :
  - rotation (gauche/droite) pendant X secondes
  - avance tout droit pendant X secondes
  - prélèvement (appel au bras robotique)
"""

import json
import math
import os


def _normalize_angle(deg):
    """Ramène un angle dans [-180, 180]."""
    deg = deg % 360
    if deg > 180:
        deg -= 360
    return deg


def _compute_segment(x1, y1, heading_deg, x2, y2, calibration):
    """
    Calcule les commandes pour aller de (x1,y1) à (x2,y2)
    en partant avec l'orientation heading_deg (en degrés, 0 = +X).

    Retourne (commands, new_heading_deg) où commands est une liste
    de dicts {"type": ..., "duration": ...} (sans l'action sample,
    qui sera ajoutée par l'appelant).
    """
    cm_per_sec = calibration["cm_per_sec"]
    deg_per_sec = calibration["deg_per_sec"]

    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)

    if distance < 0.5:  # déjà sur place
        return [], heading_deg

    target_angle = math.degrees(math.atan2(dy, dx))
    heading_change = _normalize_angle(target_angle - heading_deg)

    commands = []

    if abs(heading_change) > 0.5:
        direction = "left" if heading_change > 0 else "right"
        duration = abs(heading_change) / deg_per_sec
        commands.append({
            "type": "rotate",
            "direction": direction,
            "duration": round(duration, 2)
        })

    forward_duration = distance / cm_per_sec
    commands.append({
        "type": "forward",
        "duration": round(forward_duration, 2)
    })

    new_heading = target_angle
    return commands, new_heading


def generate(map_path="map.json", calibration_path="calibration.json"):
    """
    Lit la carte et la calibration, puis retourne la liste complète
    des commandes à exécuter.

    Paramètres
    ----------
    map_path : str
        Chemin vers le fichier map.json (relatif ou absolu).
    calibration_path : str
        Chemin vers le fichier calibration.json.

    Retourne
    --------
    list[dict]
        Liste de commandes : {"type": "rotate"|"forward"|"sample", ...}
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isabs(map_path):
        map_path = os.path.join(base_dir, map_path)
    if not os.path.isabs(calibration_path):
        calibration_path = os.path.join(base_dir, calibration_path)

    with open(map_path, "r") as f:
        map_data = json.load(f)
    with open(calibration_path, "r") as f:
        cal = json.load(f)

    start = map_data["start"]
    waypoints = map_data["waypoints"]

    current_x = start["x"]
    current_y = start["y"]
    current_heading = start.get("heading_deg", 0)

    plan = []

    for wp in waypoints:
        seg_cmds, new_heading = _compute_segment(
            current_x, current_y, current_heading,
            wp["x"], wp["y"],
            cal
        )
        plan.extend(seg_cmds)

        action = wp.get("action", "sample")
        if action == "sample":
            plan.append({"type": "sample"})

        current_x = wp["x"]
        current_y = wp["y"]
        current_heading = new_heading

    return plan


# ---------------------------------------------------------------------------
# Exécution directe : affiche le plan sans bouger le robot (mode dry-run)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    plan = generate()
    print("Plan généré :")
    for i, cmd in enumerate(plan, 1):
        print(f"  {i:2d}. {cmd}")
