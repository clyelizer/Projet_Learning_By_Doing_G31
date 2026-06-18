#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de planification des déplacements autonomes.
Calcule les angles, distances et durées pour le robot adeept_picarpro.
"""

import json
import math


def load_json(filepath):
    """Charge un fichier JSON."""
    with open(filepath, 'r') as f:
        return json.load(f)


def normalize_angle(angle_deg):
    """
    Normalise un angle pour qu'il soit dans [-180, +180].
    Le robot tourne toujours par le chemin le plus court.
    """
    angle = angle_deg % 360.0
    if angle > 180.0:
        angle -= 360.0
    return angle


def calculate_movement(x_a, y_a, x_b, y_b, heading_deg):
    """
    Calcule tous les paramètres du déplacement de A vers B.

    Retourne un dict avec:
      - delta_x, delta_y : écarts de coordonnées
      - distance_cm      : distance euclidienne
      - target_angle_deg : angle absolu vers B (0° = +X)
      - rotation_deg     : angle de rotation à effectuer (normalisé)
      - direction        : 'left' ou 'right'
    """
    # 1. Vecteur de déplacement
    delta_x = x_b - x_a
    delta_y = y_b - y_a

    # 2. Distance euclidienne
    distance_cm = math.sqrt(delta_x**2 + delta_y**2)

    # 3. Angle cible (cap vers B)
    target_angle_rad = math.atan2(delta_y, delta_x)
    target_angle_deg = math.degrees(target_angle_rad)

    # 4. Angle de rotation requis
    rotation_deg = normalize_angle(target_angle_deg - heading_deg)

    # 5. Direction du virage
    direction = 'left' if rotation_deg >= 0 else 'right'

    return {
        'delta_x': delta_x,
        'delta_y': delta_y,
        'distance_cm': distance_cm,
        'target_angle_deg': target_angle_deg,
        'rotation_deg': abs(rotation_deg),
        'direction': direction
    }


def generate_plan(map_file, calibration_file):
    """
    Génère le plan complet de déplacement à partir de la carte et de la calibration.

    Retourne une liste de commandes exploitables par executor.py.
    """
    map_data = load_json(map_file)
    calibration = load_json(calibration_file)

    cm_per_sec = calibration['cm_per_sec']
    deg_per_sec = calibration['deg_per_sec']

    start = map_data['start']
    waypoints = map_data['waypoints']

    plan = []
    current_x = start['x']
    current_y = start['y']
    current_heading = start['heading_deg']

    for wp in waypoints:
        # Calcul du déplacement vers le prochain point
        move = calculate_movement(current_x, current_y, wp['x'], wp['y'], current_heading)

        # Ajout de la commande de rotation
        if move['rotation_deg'] > 0.5:  # seuil de 0.5° pour éviter les micro-rotations
            plan.append({
                'type': 'rotate',
                'direction': move['direction'],
                'angle_deg': move['rotation_deg'],
                'duration': round(move['rotation_deg'] / deg_per_sec, 3)
            })

        # Ajout de la commande d'avance
        if move['distance_cm'] > 0.5:  # seuil de 0.5 cm
            plan.append({
                'type': 'forward',
                'distance_cm': move['distance_cm'],
                'duration': round(move['distance_cm'] / cm_per_sec, 3)
            })

        # Ajout des actions au point d'arrivée
        if wp.get('probe', False):
            plan.append({
                'type': 'action',
                'action': 'probe',
                'waypoint_id': wp['id']
            })
        
        if wp.get('photos', 0) > 0:
            plan.append({
                'type': 'action',
                'action': 'photo',
                'waypoint_id': wp['id'],
                'count': wp['photos']
            })
        
        # Rétrocompatibilité: ancien champ 'action' (déprécié)
        if wp.get('action') and not wp.get('probe') and not wp.get('photos'):
            plan.append({
                'type': 'action',
                'action': wp['action'],
                'waypoint_id': wp['id']
            })

        # Mise à jour de la position et du heading pour le prochain segment
        current_x = wp['x']
        current_y = wp['y']
        current_heading = move['target_angle_deg']

    return plan


def print_plan(plan):
    """Affiche le plan de manière lisible."""
    print("\n=== PLAN DE DÉPLACEMENT ===\n")
    for i, cmd in enumerate(plan, 1):
        if cmd['type'] == 'rotate':
            print(f"{i}. ROTATION {cmd['direction'].upper()}")
            print(f"   Angle : {cmd['angle_deg']:.2f}°")
            print(f"   Durée : {cmd['duration']:.3f} s")
        elif cmd['type'] == 'forward':
            print(f"{i}. AVANCE")
            print(f"   Distance : {cmd['distance_cm']:.2f} cm")
            print(f"   Durée    : {cmd['duration']:.3f} s")
        elif cmd['type'] == 'action':
            if cmd['action'] == 'photo':
                print(f"{i}. PHOTO (x{cmd.get('count', 1)})")
            else:
                print(f"{i}. ACTION : {cmd['action'].upper()}")
            print(f"   Waypoint ID : {cmd['waypoint_id']}")
        print()


if __name__ == '__main__':
    import os as _os
    _here = _os.path.dirname(_os.path.abspath(__file__))
    _cfg = _os.path.join(_here, '..', 'config')
    plan = generate_plan(
        _os.path.join(_cfg, 'map.json'),
        _os.path.join(_cfg, 'calibration.json')
    )
    print_plan(plan)

    # Sauvegarde du plan
    with open('plan.json', 'w') as f:
        json.dump(plan, f, indent=2)
    print("Plan sauvegardé dans plan.json")
