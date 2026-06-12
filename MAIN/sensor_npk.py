#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de lecture du capteur sol NPK via RS485/Modbus.
Basé sur le code de référence dans MAIN/sample/.

Protocole : Modbus RTU
Port      : /dev/ttyS0, 9600 baud, 8 bits, sans parité, 1 stopbit
Trame     : [0x01, 0x03, 0x00, 0x00, 0x00, 0x04, 0x44, 0x09]
Données   : Humidité (%), Température (°C), EC (mS/cm), pH

Usage:
    python sensor_npk.py       # test: lit et affiche les mesures
"""

import time

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("[WARN] pyserial non disponible - mode simulation capteur")

# Configuration du capteur (basée sur MAIN/sample/)
SENSOR_PORT = '/dev/ttyS0'
SENSOR_BAUDRATE = 9600
SENSOR_TIMEOUT = 2

# Trame Modbus de requête (issue de MAIN/sample/diagnostic_capteur.py)
REQUEST_FRAME = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x04, 0x44, 0x09])
RESPONSE_LENGTH = 20


def _crc16_modbus(data):
    """
    Calcule le checksum CRC-16 Modbus standard.

    Algorithme :
    - Initialiser le CRC à 0xFFFF
    - Pour chaque octet : XOR avec l'octet faible du CRC,
      puis 8 itérations de décalage à droite avec XOR 0xA001
      si le bit de poids faible était 1

    Args:
        data: bytes ou bytearray contenant les données à valider

    Returns:
        int: valeur CRC-16 (16 bits)
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def read_sensor(port=None, baudrate=None):
    """
    Lit les données du capteur sol via RS485/Modbus.

    Args:
        port: port série (défaut: /dev/ttyS0)
        baudrate: vitesse (défaut: 9600)

    Returns:
        dict ou None: {
            'humidity_pct': float,    # Humidité du sol en %
            'temperature_c': float,   # Température en °C
            'ec_ms_cm': float,        # Conductivité électrique en mS/cm
            'ph': float,              # pH
            'timestamp': str          # Horodatage ISO 8601
        }
        Retourne None si le capteur est indisponible ou en erreur.
    """
    if not SERIAL_AVAILABLE:
        print("[WARN] Capteur NPK indisponible (pyserial manquant)")
        return None

    if port is None:
        port = SENSOR_PORT
    if baudrate is None:
        baudrate = SENSOR_BAUDRATE

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=SENSOR_TIMEOUT
        )

        ser.write(REQUEST_FRAME)
        time.sleep(0.5)
        response = ser.read(RESPONSE_LENGTH)
        ser.close()

        if len(response) < 5:
            print(f"[WARN] Réponse capteur trop courte : {len(response)} octets")
            return None

        computed_crc = _crc16_modbus(response[:-2])
        received_crc = response[-2] | (response[-1] << 8)
        if computed_crc != received_crc:
            print(f"[ERROR] CRC mismatch - données corrompues "
                  f"(calculé=0x{computed_crc:04X}, reçu=0x{received_crc:04X})")
            return None

        data = list(response)

        result = {
            'humidity_pct': (data[3] << 8 | data[4]) / 10.0,
            'temperature_c': (data[5] << 8 | data[6]) / 10.0,
            'ec_ms_cm': (data[7] << 8 | data[8]) / 10.0,
            'ph': (data[9] << 8 | data[10]) / 10.0,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

        print(f"[NPK] Humidité={result['humidity_pct']:.1f}% "
              f"Temp={result['temperature_c']:.1f}°C "
              f"EC={result['ec_ms_cm']:.2f}mS/cm "
              f"pH={result['ph']:.1f}")

        return result

    except serial.SerialException as e:
        print(f"[ERROR] Erreur port série ({port}): {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Échec lecture capteur: {e}")
        return None


if __name__ == '__main__':
    print("Test lecture capteur NPK")
    data = read_sensor()
    if data:
        print(f"\nRésultat : {data}")
    else:
        print("Aucune donnée lue (capteur indisponible)")
