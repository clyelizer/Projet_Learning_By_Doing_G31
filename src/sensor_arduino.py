#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de lecture du capteur sol via Arduino.

L'Arduino gère le RS485/MAX485 + le capteur et envoie les données
formatées en texte sur le port série USB (9600 baud).

Format réel de l'Arduino :
    Humidité: 17.20 %
    Température: 24.10 °C
    EC: 45.00 us/cm
    pH: 8.60
    -----------------------

Usage :
    python sensor_arduino.py              # lit et affiche une mesure
    python sensor_arduino.py --loop       # lit toutes les 3s
    python sensor_arduino.py --raw        # affiche les trames brutes
"""

import re
import sys
import time

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

ARDUINO_PORT = '/dev/ttyACM0'
ARDUINO_BAUDRATE = 9600
ARDUINO_TIMEOUT = 5

# Mapping des labels français → clés de sortie
LABEL_MAP = {
    'humidité':   'humidity_pct',
    'température': 'temperature_c',
    'ec':         'ec_us_cm',
    'ph':         'ph',
}


def _parse_arduino_output(text):
    """
    Parse la sortie multi-lignes de l'Arduino en dictionnaire.

    Args:
        text: chaîne brute reçue du port série

    Returns:
        dict avec les clés 'humidity_pct', 'temperature_c',
        'ec_us_cm', 'ph' ou None si échec
    """
    if not text or not text.strip():
        return None

    # Extrait les lignes complètes
    lines = text.strip().splitlines()

    values = {}

    for line in lines:
        # Ignore la ligne de séparation
        if set(line.strip()) == set('-'):
            continue
        if not line.strip():
            continue

        # Format attendu : "Label: valeur unité"
        m = re.match(
            r'^\s*(Humidité|Température|EC|pH)\s*:\s*([0-9]+\.?[0-9]*)\b',
            line,
            re.IGNORECASE,
        )
        if not m:
            continue

        label_fr = m.group(1).lower()
        raw_value = m.group(2)
        key = LABEL_MAP.get(label_fr)
        if key is None:
            continue

        values[key] = float(raw_value)

    # On doit avoir les 4 mesures
    required = {'humidity_pct', 'temperature_c', 'ec_us_cm', 'ph'}
    if not required.issubset(values.keys()):
        return None

    return values


def read_sensor(port=None, baudrate=None):
    """
    Lit les données du capteur sol via l'Arduino.

    Args:
        port: port série (défaut: /dev/ttyACM0)
        baudrate: vitesse (défaut: 9600)

    Returns:
        dict ou None : {
            'humidity_pct':   float,   # Humidité en %
            'temperature_c':  float,   # Température en °C
            'ec_us_cm':       float,   # Conductivité en µS/cm
            'ph':             float,   # pH
            'timestamp':      str,     # ISO 8601
        }
    """
    if not SERIAL_AVAILABLE:
        print("[WARN] Capteur indisponible (pyserial manquant)")
        return None

    port = port or ARDUINO_PORT
    baudrate = baudrate or ARDUINO_BAUDRATE

    try:
        ser = serial.Serial(port, baudrate, timeout=ARDUINO_TIMEOUT)
        time.sleep(1.5)           # laisse l'Arduino se stabiliser
        ser.reset_input_buffer()  # vide les données d'avant l'ouverture

        # Lire tout ce qui arrive pendant ~2s (cycle d'envoi de l'Arduino)
        time.sleep(2.5)
        raw = ser.read_all().decode('utf-8', errors='replace')
        ser.close()

        if not raw.strip():
            print(f"[WARN] Aucune donnée reçue de l'Arduino sur {port}")
            return None

        values = _parse_arduino_output(raw)
        if values is None:
            print(f"[WARN] Impossible de parser la trame Arduino : {raw!r}")
            return None

        result = {
            **values,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }

        print(f"[ARDUINO] Humidité={result['humidity_pct']:.1f}%  "
              f"Temp={result['temperature_c']:.1f}°C  "
              f"EC={result['ec_us_cm']:.1f}µS/cm  "
              f"pH={result['ph']:.1f}")

        return result

    except serial.SerialException as e:
        print(f"[ERROR] Port série {port} : {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Échec lecture capteur : {e}")
        return None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Lit les données du capteur sol via Arduino"
    )
    parser.add_argument('--port', default=ARDUINO_PORT)
    parser.add_argument('--baud', type=int, default=ARDUINO_BAUDRATE)
    parser.add_argument('--loop', action='store_true',
                        help="Lecture continue toutes les 3s")
    parser.add_argument('--raw', action='store_true',
                        help="Affiche la trame brute reçue")

    args = parser.parse_args()

    if args.loop:
        print(f"Lecture continue sur {args.port} @ {args.baud} baud")
        print("Ctrl+C pour arrêter\n")
        try:
            while True:
                data = read_sensor(port=args.port, baudrate=args.baud)
                if data:
                    print(f"  → {data}")
                else:
                    print("  → Pas de données")
                time.sleep(3)
        except KeyboardInterrupt:
            print("\nArrêt.")
    else:
        ser = serial.Serial(args.port, args.baud, timeout=ARDUINO_TIMEOUT)
        time.sleep(1.5)
        ser.reset_input_buffer()
        time.sleep(2.5)
        raw = ser.read_all().decode('utf-8', errors='replace')
        ser.close()

        if args.raw:
            print(repr(raw))
        else:
            data = read_sensor(port=args.port, baudrate=args.baud)
            if data:
                print(f"\nRésultat : {data}")
            else:
                print("Aucune donnée lue.")
                sys.exit(1)
