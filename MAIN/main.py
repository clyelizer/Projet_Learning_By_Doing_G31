#!/usr/bin/env python3
"""
main.py — Point d'entrée du robot autonome agricole.

Coordonne l'ensemble du système :
  1. Génère le plan de déplacement à partir de map.json et calibration.json
  2. Exécute chaque commande (moteurs + bras)
  3. Termine proprement

Usage :
  python main.py [--speed N] [--dry-run]

Options :
  --speed N    Vitesse moteur 0-100 (défaut : 40)
  --dry-run    Affiche le plan sans bouger le robot
"""

import sys
import os
import argparse

# ---------------------------------------------------------------------------
# Ajout du répertoire courant au path pour les imports locaux
# ---------------------------------------------------------------------------
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import planner


def main():
    parser = argparse.ArgumentParser(
        description="Robot autonome agricole — PiCar Agri"
    )
    parser.add_argument(
        "--speed", type=int, default=40,
        help="Vitesse moteur 0-100 (défaut : 40)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Affiche le plan de déplacement sans exécuter les moteurs"
    )
    parser.add_argument(
        "--map", type=str, default="map.json",
        help="Chemin vers le fichier map.json (défaut : map.json)"
    )
    parser.add_argument(
        "--calibration", type=str, default="calibration.json",
        help="Chemin vers calibration.json (défaut : calibration.json)"
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # 1. Génération du plan
    # ------------------------------------------------------------------
    print("=== Génération du plan de déplacement ===")
    plan = planner.generate(
        map_path=args.map,
        calibration_path=args.calibration
    )

    print(f"\nPlan ({len(plan)} commandes) :")
    for i, cmd in enumerate(plan, 1):
        print(f"  {i:2d}. {cmd}")

    if args.dry_run:
        print("\n[Mode dry-run] Aucune commande moteur exécutée.")
        return

    # ------------------------------------------------------------------
    # 2. Exécution (import lazy pour ne pas dépendre du hardware en dry-run)
    # ------------------------------------------------------------------
    import executor
    print(f"\n=== Exécution (vitesse = {args.speed}) ===")
    executor.run_plan(plan, speed=args.speed)


if __name__ == "__main__":
    main()
