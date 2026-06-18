#!/usr/bin/env python3
"""
TP1 Robotique — Contrôle des servomoteurs via PCA9685 (bus I2C).

Le PCA9685 est un driver PWM 16 canaux contrôlé en I²C.
Adresse par défaut du Robot HAT : 0x5f

Fonctions :
    set_angle(ID, angle)           — positionne un servo
    set_multiple_angles(chs, angle) — positionne plusieurs servos au même angle
    tourner(channels)              — cycle 0°→180°→0° sur les canaux donnés
"""

import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

# --- Bus I²C et PCA9685 ---
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)   # Adresse du Robot HAT Adeept
pca.frequency = 50                  # 50 Hz pour les servos standard


def set_angle(ID, angle):
    """
    Positionne le servo du canal *ID* à l'angle donné (0–180°).

    Parameters
    ----------
    ID : int
        Canal PCA9685 (0–15).
    angle : float
        Angle en degrés.
    """
    servo_angle = servo.Servo(
        pca.channels[ID],
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
    )
    servo_angle.angle = angle


def set_multiple_angles(channels, angle):
    """
    Applique le même angle à plusieurs servos.

    Parameters
    ----------
    channels : list[int]
        Liste des canaux PCA9685.
    angle : float
        Angle en degrés.
    """
    for channel in channels:
        set_angle(channel, angle)


def tourner(channels):
    """
    Cycle de rotation : 0° → 180° puis 180° → 0°.

    Parameters
    ----------
    channels : list[int]
        Canaux à faire tourner.
    """
    # 0 → 180
    for i in range(180):
        set_multiple_angles(channels, i)
        time.sleep(0.01)
    time.sleep(0.5)

    # 180 → 0
    for i in range(180, 0, -1):
        set_multiple_angles(channels, i)
        time.sleep(0.01)
    time.sleep(0.5)


if __name__ == "__main__":
    channels = [0, 1]  # Exemple : roue et ultrason
    try:
        print(f"Servos canaux {channels} — rotation 0°↔180° (Ctrl+C pour arrêter)")
        while True:
            tourner(channels)
    except KeyboardInterrupt:
        print("Arrêt — positionnement à 90°")
        set_multiple_angles(channels, 90)
        pca.deinit()
