#!/usr/bin/env python3
"""
TP2 Robotique — Déplacement complet du robot (moteurs + servo de direction).

Combine le contrôle des moteurs DC et le servo de direction (canal 0)
pour les virages avec orientation des roues avant.

Canaux PCA9685 :
    Moteur 1 : IN1=15, IN2=14
    Moteur 2 : IN1=12, IN2=13
    Servo direction : canal 0

Fonctions :
    avancer(vitesse)       — ligne droite, roues centrées (90°)
    reculer(vitesse)       — marche arrière, roues centrées
    tourner_gauche(vitesse) — roues braquées à gauche (60°)
    tourner_droite(vitesse) — roues braquées à droite (120°)
    arret()                — arrêt moteurs, roues centrées
"""

import time
from board import SCL, SDA
import busio
from adafruit_motor import motor, servo
from adafruit_pca9685 import PCA9685

# --- Canaux PCA9685 ---
MOTOR_M1_IN1 = 14
MOTOR_M1_IN2 = 15
MOTOR_M2_IN1 = 13
MOTOR_M2_IN2 = 12
SERVO_DIRECTION = 0        # Canal du servo de direction

# --- Initialisation ---
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

# Moteurs
motor1 = motor.DCMotor(pca.channels[MOTOR_M1_IN1], pca.channels[MOTOR_M1_IN2])
motor2 = motor.DCMotor(pca.channels[MOTOR_M2_IN1], pca.channels[MOTOR_M2_IN2])
motor1.decay_mode = motor.SLOW_DECAY
motor2.decay_mode = motor.SLOW_DECAY


def set_angle(ID, angle):
    """Positionne un servo du canal *ID* à l'angle donné (0–180°)."""
    s = servo.Servo(
        pca.channels[ID],
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
    )
    s.angle = angle


# --- Mouvements avec direction ---

def avancer(vitesse=0.5):
    """Avancer en ligne droite (roues centrées à 90°)."""
    motor1.throttle = vitesse
    motor2.throttle = vitesse
    set_angle(SERVO_DIRECTION, 90)


def reculer(vitesse=0.5):
    """Reculer en ligne droite (roues centrées à 90°)."""
    motor1.throttle = -vitesse
    motor2.throttle = -vitesse
    set_angle(SERVO_DIRECTION, 90)


def tourner_gauche(vitesse=0.5):
    """Tourner à gauche (roues braquées à ~60°)."""
    motor1.throttle = vitesse
    motor2.throttle = vitesse
    set_angle(SERVO_DIRECTION, 60)


def tourner_droite(vitesse=0.5):
    """Tourner à droite (roues braquées à ~120°)."""
    motor1.throttle = vitesse
    motor2.throttle = vitesse
    set_angle(SERVO_DIRECTION, 120)


def arret():
    """Arrêt complet (moteurs + roues centrées)."""
    motor1.throttle = 0.0
    motor2.throttle = 0.0
    set_angle(SERVO_DIRECTION, 90)


# --- Programme de test ---
if __name__ == "__main__":
    set_angle(SERVO_DIRECTION, 90)
    try:
        while True:
            print("AVANCE 50%")
            avancer(0.5)
            time.sleep(2)

            print("RECULE 50%")
            reculer(0.5)
            time.sleep(2)

            print("TOURNER GAUCHE (50%)")
            tourner_gauche(0.5)
            time.sleep(2)

            print("TOURNER DROITE (50%)")
            tourner_droite(0.5)
            time.sleep(2)

            print("ARRET")
            arret()
            time.sleep(2)

    except KeyboardInterrupt:
        print("Stop par l'utilisateur.")
        arret()
        pca.deinit()
