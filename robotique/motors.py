#!/usr/bin/env python3
"""
TP2 Robotique — Contrôle des moteurs DC via PCA9685 (bus I2C).

Le driver moteur est piloté par des canaux PWM du PCA9685.
Chaque moteur DC utilise 2 canaux (IN1, IN2).

Canaux PCA9685 (Robot HAT Adeept) :
    Moteur 1 (gauche) : IN1 = canal 14, IN2 = canal 15
    Moteur 2 (droite) : IN1 = canal 13, IN2 = canal 12

Fonctions :
    avancer(vitesse)      — les 2 moteurs vers l'avant
    reculer(vitesse)      — les 2 moteurs vers l'arrière
    tourner_gauche(vitesse) — moteur droit avance, gauche arrêté
    tourner_droite(vitesse) — moteur gauche avance, droit arrêté
    arret()               — moteurs à l'arrêt

throttle ∈ [-1.0, 1.0] :
    > 0 → avant
    < 0 → arrière
    = 0 → arrêt
"""

import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor

# --- Canaux PCA9685 (Robot HAT Adeept) ---
MOTOR_M1_IN1 = 14
MOTOR_M1_IN2 = 15
MOTOR_M2_IN1 = 13
MOTOR_M2_IN2 = 12

# --- Initialisation bus I²C et PCA9685 ---
i2c = busio.I2C(SCL, SDA)
pwm = PCA9685(i2c, address=0x5f)
pwm.frequency = 50

# --- Objets moteurs DC ---
motor1 = motor.DCMotor(
    pwm.channels[MOTOR_M1_IN1],
    pwm.channels[MOTOR_M1_IN2],
)
motor2 = motor.DCMotor(
    pwm.channels[MOTOR_M2_IN1],
    pwm.channels[MOTOR_M2_IN2],
)

# Freinage doux (SLOW_DECAY)
motor1.decay_mode = motor.SLOW_DECAY
motor2.decay_mode = motor.SLOW_DECAY


def avancer(vitesse=0.5):
    """Avancer : les 2 moteurs tournent vers l'avant."""
    motor1.throttle = vitesse
    motor2.throttle = vitesse


def reculer(vitesse=0.5):
    """Reculer : les 2 moteurs tournent vers l'arrière."""
    motor1.throttle = -vitesse
    motor2.throttle = -vitesse


def tourner_gauche(vitesse=0.5):
    """Tourner à gauche : moteur droit avance, gauche arrêté."""
    motor1.throttle = 0.0
    motor2.throttle = vitesse


def tourner_droite(vitesse=0.5):
    """Tourner à droite : moteur gauche avance, droit arrêté."""
    motor1.throttle = vitesse
    motor2.throttle = 0.0


def arret():
    """Arrêter les 2 moteurs."""
    motor1.throttle = 0.0
    motor2.throttle = 0.0


# --- Programme de test ---
if __name__ == "__main__":
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
        pwm.deinit()
