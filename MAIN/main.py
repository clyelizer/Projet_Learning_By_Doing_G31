#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal du système autonome.
Orchestre le pipeline complet :
  planner → executor → arm → sensor_npk → camera → image_processor → data_logger

Usage:
    python main.py                                          # Fichiers par défaut
    python main.py --dry-run                               # Affiche le plan sans exécuter
    python main.py --map ma_carte.json                     # Carte personnalisée
    python main.py --calib ma_calib.json                   # Calibration personnalisée
    python main.py --dry-run --map map.json --calib calib.json
"""

import os
import sys
import signal
import argparse
import json
import time

import planner
import executor
import arm
import sensor_npk
import camera
import image_processor
import data_logger


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def signal_handler(sig, frame):
    """Gestion propre de l'interruption (Ctrl+C)."""
    print("\n[INFO] Arrêt demandé - nettoyage...")

    # Sécurité : remonter le bras si la sonde était baissée
    try:
        arm_ctrl = arm.get_arm()
        arm_ctrl.raise_probe()
        arm_ctrl.reset_position()
    except Exception:
        pass

    executor.cleanup()
    arm.cleanup()
    camera.cleanup()

    # Sauvegarde des données de mission déjà collectées
    try:
        image_processor.wait_all()
        img_results = image_processor.get_results()
        if img_results:
            data_logger.get_logger().attach_image_results(img_results)
        data_logger.save_final()
    except Exception:
        pass

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
        default=os.path.join(SCRIPT_DIR, '..', 'Config', 'map.json'),
        help="Chemin vers le fichier de carte (défaut: Config/map.json)"
    )
    
    parser.add_argument(
        '--calib',
        type=str,
        default=os.path.join(SCRIPT_DIR, '..', 'Config', 'calibration.json'),
        help="Chemin vers le fichier de calibration (défaut: Config/calibration.json)"
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
    
    # Charger la calibration pour les constantes
    try:
        with open(args.calib, 'r') as f:
            calib = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Impossible de charger la calibration: {e} — valeurs par défaut utilisées")
        calib = {}

    photo_count = calib.get('photo_count', 3)
    photo_delay_s = calib.get('photo_delay_s', 0.5)
    probe_pause_s = calib.get('probe_pause_s', 1.5)
    sensor_port = calib.get('sensor_port', '/dev/ttyS0')
    sensor_baudrate = calib.get('sensor_baudrate', 9600)

    # Gestion du Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 50)
    print("  SYSTÈME AUTONOME - ADEEPT PICAR PRO")
    print("  Robot agricole miniature")
    print("=" * 50)
    
    # Afficher les fichiers utilisés
    print(f"\n📍 Carte : {os.path.normpath(args.map)}")
    print(f"📍 Calibration : {os.path.normpath(args.calib)}")
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

        if command['type'] in ('rotate', 'forward'):
            try:
                executor.run(command)
            except Exception as e:
                print(f"[ERROR] Échec mouvement ({command['type']}): {e}")
                print("[INFO] Arrêt de la mission — position incertaine")
                break

        elif command['type'] == 'action':
            action = command['action']
            wp_id = command['waypoint_id']
            print(f"[MAIN] Action '{action}' au waypoint {wp_id}")

            if action == 'probe':
                probe_lowered = False
                try:
                    arm_ctrl = arm.get_arm()
                    arm_ctrl.lower_probe()
                    probe_lowered = True
                    time.sleep(probe_pause_s)
                    sensor_data = sensor_npk.read_sensor(
                        port=sensor_port, baudrate=sensor_baudrate
                    )
                    if sensor_data is None:
                        print("[WARN] Lecture capteur NPK: aucune donnée retournée")
                    arm_ctrl.raise_probe()
                    probe_lowered = False
                    arm_ctrl.reset_position()
                except Exception as e:
                    print(f"[ERROR] Échec sondage NPK: {e}")
                    sensor_data = None
                    # Récupération sécurisée : ne relever que si la sonde a été baissée
                    try:
                        arm_ctrl = arm.get_arm()
                        if probe_lowered:
                            arm_ctrl.raise_probe()
                        arm_ctrl.reset_position()
                    except Exception:
                        pass
                data_logger.log_waypoint(wp_id, sensor_data=sensor_data)

            elif action == 'photo':
                try:
                    count = command.get('count', photo_count)
                    photo_paths = camera.take_photos(n=count, delay=photo_delay_s)
                    data_logger.log_waypoint(wp_id, image_paths=photo_paths)
                    if photo_paths:
                        image_processor.enqueue(photo_paths, wp_id)
                except Exception as e:
                    print(f"[ERROR] Échec capture photo: {e}")
                    data_logger.log_waypoint(wp_id, image_paths=[])
        else:
            print(f"[WARN] Type de commande inconnu: {command['type']}")

        time.sleep(0.5)  # Pause entre chaque commande

    # Attendre la fin des traitements asynchrones
    print("\n[MAIN] Finalisation des traitements...")
    image_processor.wait_all()

    # Attacher les résultats d'image au logger
    img_results = image_processor.get_results()
    if img_results:
        data_logger.get_logger().attach_image_results(img_results)

    # Sauvegarde finale
    data_logger.save_final()

    print("\n" + "=" * 50)
    print("  MISSION TERMINÉE")
    print("=" * 50)

    # Nettoyage
    executor.cleanup()
    arm.cleanup()
    camera.cleanup()


if __name__ == '__main__':
    main()
