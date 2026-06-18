#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit complet de la chaîne de mesure capteur sol.

Reproduit EXACTEMENT la séquence de main.py :
  arm.lower_probe() → pause → sensor_arduino.read_sensor() → arm.raise_probe()
  → arm.reset_position() → data_logger.log_waypoint()

Lancement :
    python tests/test_sensor_audit.py
    python tests/test_sensor_audit.py --loop    (3 lectures)
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import arm
import sensor_arduino
import data_logger

# ── Configuration (identique à main.py) ──────────────────────────

SENSOR_PORT = '/dev/ttyACM0'
SENSOR_BAUDRATE = 9600
PROBE_PAUSE_S = 1.5
WP_ID = 99  # waypoint factice pour le test


# ── Affichage ─────────────────────────────────────────────────────

def hr(title):
    """Séparateur de section."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def show_sensor(r):
    """Affiche les données du capteur."""
    if r is None:
        print("  ⛔ Aucune donnée")
        return
    print(f"  💧 Humidité     : {r['humidity_pct']:6.1f} %")
    print(f"  🌡️  Température  : {r['temperature_c']:6.1f} °C")
    print(f"  ⚡ Conductivité : {r['ec_us_cm']:6.1f} µS/cm")
    print(f"  🧪 pH           : {r['ph']:6.1f}")
    print(f"  🕐 Timestamp    : {r['timestamp']}")


def show_logger():
    """Affiche le contenu du logger."""
    logger = data_logger.get_logger()
    summary = logger.get_summary()
    waypoints = summary['waypoints']

    if not waypoints:
        print("  (vide)")
        return

    for wp in waypoints:
        print(f"\n  📍 Waypoint {wp['waypoint_id']} — {wp['timestamp']}")
        if wp.get('sensor'):
            s = wp['sensor']
            print(f"     💧 {s['humidity_pct']:.1f}%  "
                  f"🌡️ {s['temperature_c']:.1f}°C  "
                  f"⚡ {s['ec_us_cm']:.1f}µS/cm  "
                  f"🧪 pH {s['ph']:.1f}")
        else:
            print(f"     ⛔ pas de données capteur")
        if wp.get('photos'):
            print(f"     📷 {len(wp['photos'])} photo(s)")
        if wp.get('image_results'):
            print(f"     🧠 {len(wp['image_results'])} analyse(s) IA")


# ── Séquence de mesure (copie exacte de main.py) ──────────────────

def probe_cycle():
    """
    Exécute UN cycle complet de mesure.
    Code identique à main.py (sans le data_logger.log_waypoint final).
    Retourne le dict capteur ou None.
    """
    probe_lowered = False
    sensor_data = None

    try:
        arm_ctrl = arm.get_arm()
        print("  🤖 Bras initialisé")

        # 1. Descendre la sonde
        arm_ctrl.lower_probe()
        probe_lowered = True
        print(f"  ⬇️  Sonde descendue — pause {PROBE_PAUSE_S}s")
        time.sleep(PROBE_PAUSE_S)

        # 2. Lire le capteur
        print("  📡 Lecture capteur...")
        sensor_data = sensor_arduino.read_sensor(
            port=SENSOR_PORT, baudrate=SENSOR_BAUDRATE
        )
        if sensor_data is None:
            print("  ⚠️  Aucune donnée retournée")
        else:
            show_sensor(sensor_data)

        # 3. Remonter la sonde
        arm_ctrl.raise_probe()
        probe_lowered = False
        print("  ⬆️  Sonde remontée")

        # 4. Reset position
        arm_ctrl.reset_position()
        print("  🏠 Bras en position neutre")

    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        sensor_data = None
        # Récupération sécurisée
        try:
            arm_ctrl = arm.get_arm()
            if probe_lowered:
                print("  🔄 Remontée d'urgence...")
                arm_ctrl.raise_probe()
            arm_ctrl.reset_position()
        except Exception:
            print("  💥 Échec récupération bras")
            pass

    return sensor_data


# ── Mode interactif ───────────────────────────────────────────────

def run_single():
    """Un seul cycle de test."""
    print("=" * 60)
    print("  🔬 AUDIT CAPTEUR SOL — 1 CYCLE")
    print("=" * 60)
    print(f"  Port      : {SENSOR_PORT} @ {SENSOR_BAUDRATE} baud")
    print(f"  Waypoint  : {WP_ID}")
    print(f"  Pause     : {PROBE_PAUSE_S}s")

    hr("1. VÉRIFICATION CONNEXION")
    print(f"  Arduino présent : {os.path.exists(SENSOR_PORT)}")
    print(f"  pyserial dispo  : {sensor_arduino.SERIAL_AVAILABLE}")

    hr("2. CYCLE DE MESURE")
    t0 = time.time()
    data = probe_cycle()
    elapsed = time.time() - t0
    print(f"\n  ⏱️  Durée du cycle : {elapsed:.1f}s")

    hr("3. ENREGISTREMENT")
    data_logger.log_waypoint(WP_ID, sensor_data=data)
    logger = data_logger.get_logger()
    logger.save_final()

    hr("4. RÉCAPITULATIF LOGGER")
    show_logger()

    hr("5. RÉSULTAT")
    if data:
        print("  ✅ CAPTEUR OPÉRATIONNEL")
        for k, v in data.items():
            if k != 'timestamp':
                print(f"     {k}: {v}")
    else:
        print("  ❌ ÉCHEC — aucune donnée")

    print(f"\n{'=' * 60}")
    print(f"  Fichier sauvegardé : data/results.json")
    print(f"{'=' * 60}")

    # Nettoyage
    arm.cleanup()


def run_loop(count=3):
    """Plusieurs cycles pour observer la stabilité."""
    print("=" * 60)
    print(f"  🔬 AUDIT CAPTEUR SOL — {count} CYCLES")
    print("=" * 60)
    print(f"  Port      : {SENSOR_PORT} @ {SENSOR_BAUDRATE} baud")

    readings = []
    for i in range(1, count + 1):
        hr(f"CYCLE {i}/{count}")
        data = probe_cycle()
        if data:
            readings.append(data)
            data_logger.log_waypoint(WP_ID + i, sensor_data=data)
        else:
            print("  ⚠️  Cycle sans donnée")
        if i < count:
            print(f"\n  ⏳ Pause 3s avant prochain cycle...")
            time.sleep(3)

    # Sauvegarde
    hr("SAUVEGARDE")
    logger = data_logger.get_logger()
    logger.save_final()

    # Analyse statistique
    if len(readings) >= 2:
        hr("ANALYSE STABILITÉ")
        for key in ['humidity_pct', 'temperature_c', 'ec_us_cm', 'ph']:
            vals = [r[key] for r in readings]
            mn, mx = min(vals), max(vals)
            spread = mx - mn
            avg = sum(vals) / len(vals)
            bar = '✅' if spread < 1.0 else ('⚠️' if spread < 5.0 else '❌')
            print(f"  {bar} {key:20s}  min={mn:6.1f}  max={mx:6.1f}  "
                  f"Δ={spread:.1f}  μ={avg:.1f}")

    hr("RÉCAPITULATIF")
    show_logger()

    # Nettoyage
    arm.cleanup()
    print(f"\n{'=' * 60}")
    print(f"  {len(readings)}/{count} cycles réussis")
    print(f"  Fichier : data/results.json")
    print(f"{'=' * 60}")


# ── Main ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit complet de la chaîne capteur sol"
    )
    parser.add_argument(
        '--loop', '-l', action='store_true',
        help="Plusieurs cycles de mesure (défaut: 3)"
    )
    parser.add_argument(
        '--count', '-n', type=int, default=3,
        help="Nombre de cycles en mode --loop"
    )
    args = parser.parse_args()

    try:
        if args.loop:
            run_loop(count=args.count)
        else:
            run_single()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu — nettoyage...")
        arm.cleanup()
        print("Terminé.")
