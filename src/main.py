#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'entrée principal du système autonome.
Orchestre le pipeline complet :
  planner → executor → arm → sensor_arduino → camera → image_preprocessor → data_logger

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
import sensor_arduino
import camera
import image_preprocessor
import vlm_analyzer
import reco_engine
import tts_engine
import data_logger


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def signal_handler(sig, frame):
    """Gestion propre de l'interruption (Ctrl+C)."""
    # Ignorer les Ctrl+C suivants pendant le nettoyage (évite la ré-entrance)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
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
        image_preprocessor.wait_all()
        img_results = image_preprocessor.get_results()
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
        default=os.path.join(SCRIPT_DIR, '..', 'config', 'map.json'),
        help="Chemin vers le fichier de carte (défaut: config/map.json)"
    )
    
    parser.add_argument(
        '--calib',
        type=str,
        default=os.path.join(SCRIPT_DIR, '..', 'config', 'calibration.json'),
        help="Chemin vers le fichier de calibration (défaut: config/calibration.json)"
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

    motor_speed = calib.get('motor_speed', 0.5)
    photo_delay_s = calib.get('photo_delay_s', 0.5)
    probe_pause_s = calib.get('probe_pause_s', 1.5)
    sensor_port = calib.get('sensor_port', '/dev/ttyACM0')
    sensor_baudrate = calib.get('sensor_baudrate', 9600)

    # Appliquer la vitesse moteur avant toute commande
    executor.get_controller().set_motor_speed(motor_speed)

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
    print("\n[1/4] Génération du plan de déplacement...")
    # Lancer le serveur web en arrière-plan avant la mission
    _launch_dashboard()
    try:
        plan = planner.generate_plan(args.map, args.calib)
    except FileNotFoundError as e:
        print(f"❌ Erreur : {e}")
        sys.exit(1)
    
    planner.print_plan(plan)

    # 2. Vérification
    print(f"\n[2/4] {len(plan)} commandes à exécuter")
    
    if args.dry_run:
        print("\n✅ Mode DRY-RUN : aucune commande exécutée")
        print("=" * 50)
        sys.exit(0)
    
    input("\nAppuyez sur ENTRÉE pour lancer la démonstration...")

    # 3. Exécution autonome
    print("\n[3/4] DÉMARRAGE AUTONOME\n")

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
                    sensor_data = sensor_arduino.read_sensor(
                        port=sensor_port, baudrate=sensor_baudrate
                    )
                    if sensor_data is None:
                        print("[WARN] Lecture capteur sol: aucune donnée retournée")
                    arm_ctrl.raise_probe()
                    probe_lowered = False
                    arm_ctrl.reset_position()
                except Exception as e:
                    print(f"[ERROR] Échec sondage capteur: {e}")
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
                    count = command.get('count', 3)  # planner surcharge, fallback=3
                    photo_paths = camera.take_photos(n=count, delay=photo_delay_s)
                    data_logger.log_waypoint(wp_id, image_paths=photo_paths)
                    if photo_paths:
                        image_preprocessor.enqueue(photo_paths, wp_id)
                    # Libérer la caméra entre les waypoints (évite "No such device")
                    camera.cleanup()
                except Exception as e:
                    print(f"[ERROR] Échec capture photo: {e}")
                    data_logger.log_waypoint(wp_id, image_paths=[])
        else:
            print(f"[WARN] Type de commande inconnu: {command['type']}")

        time.sleep(0.5)  # Pause entre chaque commande

    # Attendre la fin des traitements asynchrones
    print("\n[MAIN] Finalisation des traitements...")
    image_preprocessor.wait_all()

    # Récupérer les résultats image
    img_results = image_preprocessor.get_results()
    if img_results:
        data_logger.get_logger().attach_image_results(img_results)

    # ── Pipeline V2 : VLM + Reco + TTS ─────────────────────────

    print("\n[MAIN] Pipeline V2 — Analyse IA...")

    for wp in data_logger.get_logger().get_summary()['waypoints']:
        wp_id = wp['waypoint_id']
        sensor = wp.get('sensor')
        photos = wp.get('photos', [])

        if not sensor and not photos:
            continue

        # Étape 1 : VLM sur la première photo du waypoint
        vlm_result = None
        if photos:
            photo = photos[0]
            print(f"  🧠 VLM wp{wp_id} → {os.path.basename(photo)}")
            try:
                vlm_result = vlm_analyzer.analyze_soil_ia(photo, primary='gemini')
                if vlm_result.get('provider'):
                    data_logger.get_logger().attach_vlm(wp_id, vlm_result)
                    print(f"     ✅ {vlm_result['provider']}: "
                          f"sol={vlm_result.get('soil_type', '?')}")
                else:
                    print(f"     ⚠️  VLM échec: {vlm_result.get('error', 'inconnu')}")
            except Exception as e:
                print(f"     ❌ VLM erreur: {e}")

        # Étape 2 : Recommandations via ML
        if sensor:
            print(f"  📋 Reco wp{wp_id} → pipeline ML")
            try:
                reco_result = reco_engine.recommend(sensor, language='fr')
                if 'error' not in reco_result:
                    data_logger.get_logger().attach_reco(wp_id, reco_result)
                    crops = reco_result.get('crops', [])
                    print(f"     ✅ Cultures: {', '.join(crops[:3])}")
                else:
                    print(f"     ⚠️  Reco échec: {reco_result['error']}")
            except Exception as e:
                print(f"     ❌ Reco erreur: {e}")

        # Étape 3 : TTS (synthèse vocale de la reco)
        if sensor:
            try:
                reco_data = wp.get('recommendations', {})
                summary = reco_data.get('summary', '')
                if summary:
                    print(f"  🔊 TTS wp{wp_id}...")
                    audio = tts_engine.speak(summary, engine='auto', lang='fr')
                    if 'error' not in audio:
                        data_logger.get_logger().attach_audio(wp_id, audio)
                        tts_engine.play_audio(audio['path'])
                        print(f"     ✅ Audio joué ({audio['engine']})")
            except Exception as e:
                print(f"     ⚠️  TTS erreur: {e}")

    # Sauvegarde finale
    data_logger.save_final()

    print("\n" + "=" * 50)
    print("  MISSION TERMINÉE")
    print("=" * 50)

    # Nettoyage matériel
    executor.cleanup()
    arm.cleanup()
    camera.cleanup()

    # ── 4. TTS final : lecture audio sur le robot ──────────────────
    print("\n[4/4] Lecture audio des recommandations...")
    try:
        logger = data_logger.get_logger()
        summary = logger.get_summary() if logger else {}
        waypoints = summary.get('waypoints', [])
        if waypoints:
            # Synthétiser un résumé global
            all_text = "Mission terminée. "
            for wp in waypoints:
                reco = wp.get('recommendations', {})
                crops = reco.get('crops', [])
                if crops:
                    all_text += f"Zone {wp['waypoint_id']}: {', '.join(crops[:2])}. "
            if all_text:
                audio = tts_engine.speak(all_text, engine='auto', lang='fr')
                if 'error' not in audio:
                    tts_engine.play_audio(audio['path'])
                    print(f"     ✅ Audio joué sur le robot ({audio['engine']})")
    except Exception as e:
        print(f"     ⚠️ Lecture audio finale: {e}")


def _is_flask_running():
    """Vérifie si le dashboard Flask tourne déjà."""
    import subprocess
    try:
        # Cherche à la fois 'app.py' et 'web/app.py' (selon comment lancé)
        result = subprocess.run(
            ['pgrep', '-f', 'app.py'],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def _launch_dashboard():
    """Lance le dashboard web s'il n'est pas déjà actif."""
    import subprocess

    # Toujours calculer et afficher l'IP réseau
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'

    print()
    print("=" * 60)
    print("  🌱 AGROSCAN — Dashboard")
    print("=" * 60)
    print(f"  Local    : http://127.0.0.1:5000")
    print(f"  📡 Réseau  : http://{local_ip}:5000")
    print("=" * 60)
    print()

    if _is_flask_running():
        print("[MAIN] Dashboard déjà en ligne")
        return

    print("[MAIN] Lancement du dashboard...")
    try:
        web_dir = os.path.join(SCRIPT_DIR, 'web')
        subprocess.Popen(
            [sys.executable, 'app.py'],
            cwd=web_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
    except Exception as e:
        print(f"[MAIN] Échec lancement dashboard: {e}")


if __name__ == '__main__':
    main()
