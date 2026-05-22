#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal du système autonome.
Coordonne planner → executor → arm.

Usage:
    python main.py                                          # Fichiers par défaut
    python main.py --dry-run                               # Affiche le plan sans exécuter
    python main.py --map ma_carte.json                     # Carte personnalisée
    python main.py --calib ma_calib.json                   # Calibration personnalisée
    python main.py --dry-run --map map.json --calib calib.json
"""

import sys
import signal
import argparse
import planner
import executor
import arm
import time


def signal_handler(sig, frame):
    """Gestion propre de l'interruption (Ctrl+C)."""
    print("\n[INFO] Arrêt demandé - nettoyage...")
    executor.cleanup()
    arm.cleanup()
    sys.exit(0)


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Système autonome - PiCar-Pro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python main.py --dry-run
  python main.py --map ma_carte.json --calib ma_calib.json
  python main.py --dry-run --map mission1.json --calib calib_terrain.json
        """
    )
    
    parser.add_argument(
        '--map',
        type=str,
        default='map.json',
        help="Chemin vers le fichier de carte (défaut: map.json)"
    )
    
    parser.add_argument(
        '--calib',
        type=str,
        default='calibration.json',
        help="Chemin vers le fichier de calibration (défaut: calibration.json)"
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Affiche le plan sans exécuter les commandes (simulation)"
    )
    
    return parser.parse_args()


def main():
    """Exécution autonome complète."""
    # Parser les arguments
    args = parse_arguments()
    
    # Gestion du Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 50)
    print("  SYSTÈME AUTONOME - ADEEPT PICAR PRO")
    print("  Robot agricole miniature")
    print("=" * 50)
    
    # Afficher les fichiers utilisés
    print(f"\n📍 Carte : {args.map}")
    print(f"📍 Calibration : {args.calib}")
    if args.dry_run:
        print("🔍 Mode : DRY-RUN (simulation)")

    # 1. Génération du plan
    print(f"\n[1/3] Génération du plan de déplacement...")
    try:
        plan = planner.generate_plan(args.map, args.calib)
    except FileNotFoundError as e:
        print(f"❌ Erreur : {e}")
        sys.exit(1)
    
    planner.print_plan(plan)

    # 2. Vérification
    print(f"\n[2/3] {len(plan)} commandes à exécuter")
    
    if args.dry_run:
        print("\n✅ Mode DRY-RUN : aucune commande exécutée")
        print("=" * 50)
        sys.exit(0)
    
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
