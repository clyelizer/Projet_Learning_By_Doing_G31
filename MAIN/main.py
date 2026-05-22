#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal du système autonome.
Coordonne planner → executor → arm.
"""

import sys
import signal
import planner
import executor
import arm


def signal_handler(sig, frame):
    """Gestion propre de l'interruption (Ctrl+C)."""
    print("\n[INFO] Arrêt demandé - nettoyage...")
    executor.cleanup()
    arm.cleanup()
    sys.exit(0)


def main():
    """Exécution autonome complète."""
    # Gestion du Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 50)
    print("  SYSTÈME AUTONOME - ADEEPT PICAR PRO")
    print("  Robot agricole miniature")
    print("=" * 50)

    # 1. Génération du plan
    print("\n[1/3] Génération du plan de déplacement...")
    plan = planner.generate_plan('map.json', 'calibration.json')
    planner.print_plan(plan)

    # 2. Vérification
    print(f"\n[2/3] {len(plan)} commandes à exécuter")
    input("\nAppuyez sur ENTRÉE pour lancer la démonstration...")

    # 3. Exécution autonome
    print("\n[3/3] DÉMARRAGE AUTONOME\n")

    for i, command in enumerate(plan, 1):
        print(f"--- Étape {i}/{len(plan)} ---")
        executor.run(command)
        time.sleep(0.5)  # Pause entre chaque commande

    print("\n" + "=" * 50)
    print("  MISSION TERMINÉE")
    print("=" * 50)

    # Nettoyage
    executor.cleanup()
    arm.cleanup()


if __name__ == '__main__':
    main()
