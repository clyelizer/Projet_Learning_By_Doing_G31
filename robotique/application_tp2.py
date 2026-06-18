#!/usr/bin/env python3
"""
TP2 Robotique — Application Pratique : Suivi de ligne + obstacle + transport.

Spécifications :
    1. Contrôler les moteurs et suivre une ligne noire (3 capteurs IR).
    2. S'arrêter dès qu'un obstacle est détecté (ultrason).
    3. Transporter une pièce d'un point A à un point B tout en suivant la ligne.

Étapes du parcours :
    Phase 1 : Départ A → suivre la ligne jusqu'au point B (avec STOP intermédiaire).
    Phase 2 : Tri par couleur, chargement/déchargement, points C/D/E.

Dépendances :
    - line_follower.py  (capteurs IR GPIO22/27/17 + logique de décision)
    - ultrason.py       (HC-SR04 GPIO23/24)
    - robot_movement.py (moteurs + servo direction PCA9685)
    - servo.py          (servos PCA9685 pour le bras)
"""

import time
import RPi.GPIO as GPIO
from board import SCL, SDA
import busio
from adafruit_motor import motor, servo
from adafruit_pca9685 import PCA9685
from gpiozero import InputDevice

# ── Capteurs de ligne ────────────────────────────────────────────────────
LINE_PIN_LEFT = 22
LINE_PIN_MIDDLE = 27
LINE_PIN_RIGHT = 17

left_sensor = InputDevice(pin=LINE_PIN_LEFT)
middle_sensor = InputDevice(pin=LINE_PIN_MIDDLE)
right_sensor = InputDevice(pin=LINE_PIN_RIGHT)

# ── Capteur ultrason (obstacle) ──────────────────────────────────────────
TRIG = 23
ECHO = 24
SPEED_OF_SOUND_CM_PER_US = 0.0343
DISTANCE_OBSTACLE_CM = 10.0  # Seuil obstacle

# ── PCA9685 : moteurs + servo direction + bras ───────────────────────────
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

# Moteurs DC
MOTOR_M1_IN1 = 14
MOTOR_M1_IN2 = 15
MOTOR_M2_IN1 = 13
MOTOR_M2_IN2 = 12

motor1 = motor.DCMotor(pca.channels[MOTOR_M1_IN1], pca.channels[MOTOR_M1_IN2])
motor2 = motor.DCMotor(pca.channels[MOTOR_M2_IN1], pca.channels[MOTOR_M2_IN2])
motor1.decay_mode = motor.SLOW_DECAY
motor2.decay_mode = motor.SLOW_DECAY

# Servo direction
SERVO_DIR = 0

# Servos du bras
SERVO_BASE = 1
SERVO_EPAULE = 2
SERVO_COUDE = 3
SERVO_PINCE = 4


# ── Fonctions bas niveau ─────────────────────────────────────────────────

def set_servo(canal, angle):
    """Positionne un servo."""
    s = servo.Servo(
        pca.channels[canal],
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
    )
    s.angle = angle
    time.sleep(0.2)


def setup_ultrason():
    """Configure les broches GPIO de l'ultrason."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.5)


def mesure_distance_cm():
    """Mesure la distance en cm (ultrason)."""
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG, GPIO.LOW)

    debut = time.time()
    timeout = debut + 0.04
    while GPIO.input(ECHO) == GPIO.LOW:
        debut = time.time()
        if debut > timeout:
            return -1
    while GPIO.input(ECHO) == GPIO.HIGH:
        fin = time.time()
        if fin > timeout:
            return -1

    duree_us = (fin - debut) * 1_000_000
    return (duree_us * SPEED_OF_SOUND_CM_PER_US) / 2.0


# ── Mouvements ───────────────────────────────────────────────────────────

def avancer(vitesse=0.4):
    """Avancer tout droit (roues centrées)."""
    motor1.throttle = vitesse
    motor2.throttle = vitesse
    set_servo(SERVO_DIR, 90)


def arret():
    """Arrêt complet."""
    motor1.throttle = 0.0
    motor2.throttle = 0.0
    set_servo(SERVO_DIR, 90)


def tourner_gauche(vitesse=0.3):
    """Correction : tourner à gauche."""
    motor1.throttle = vitesse
    motor2.throttle = 0.0
    set_servo(SERVO_DIR, 60)


def tourner_droite(vitesse=0.3):
    """Correction : tourner à droite."""
    motor1.throttle = 0.0
    motor2.throttle = vitesse
    set_servo(SERVO_DIR, 120)


# ── Suivi de ligne ───────────────────────────────────────────────────────

def lire_capteurs():
    """Retourne (gauche, milieu, droite). 0 = ligne noire."""
    return left_sensor.value, middle_sensor.value, right_sensor.value


def decision_suivi(sl, sm, sr):
    """
    Logique de suivi de ligne.
    Retourne : 'tout_droit', 'gauche', 'droite', 'stop'.
    """
    if sm == 0:
        if sl == 0 and sr == 1:
            return "droite"
        elif sl == 1 and sr == 0:
            return "gauche"
        else:
            return "tout_droit"
    else:
        if sl == 0 and sr == 1:
            return "droite"
        elif sl == 1 and sr == 0:
            return "gauche"
        else:
            return "tout_droit"


def appliquer_action(action):
    """Exécute l'action de suivi sur les moteurs."""
    if action == "tout_droit":
        avancer(0.3)
    elif action == "gauche":
        tourner_gauche(0.3)
    elif action == "droite":
        tourner_droite(0.3)
    elif action == "stop":
        arret()


# ── Bras robotique ───────────────────────────────────────────────────────

def position_prise():
    """Positionne le bras pour saisir une pièce."""
    set_servo(SERVO_BASE, 90)
    set_servo(SERVO_EPAULE, 120)
    set_servo(SERVO_COUDE, 60)
    set_servo(SERVO_PINCE, 30)   # Pince ouverte


def position_depot():
    """Positionne le bras pour déposer une pièce."""
    set_servo(SERVO_BASE, 90)
    set_servo(SERVO_EPAULE, 60)
    set_servo(SERVO_COUDE, 120)
    set_servo(SERVO_PINCE, 30)


def position_repos():
    """Position de repos du bras."""
    set_servo(SERVO_BASE, 90)
    set_servo(SERVO_EPAULE, 90)
    set_servo(SERVO_COUDE, 90)
    set_servo(SERVO_PINCE, 60)   # Pince fermée


def fermer_pince():
    set_servo(SERVO_PINCE, 60)


def ouvrir_pince():
    set_servo(SERVO_PINCE, 30)


def transporter_piece():
    """Séquence : prise → fermer → dépôt → ouvrir → repos."""
    print("    → Bras en position prise")
    position_prise()
    time.sleep(1)
    fermer_pince()
    time.sleep(0.5)

    print("    → Bras en position dépôt")
    position_depot()
    time.sleep(1)
    ouvrir_pince()
    time.sleep(0.5)

    print("    → Bras au repos")
    position_repos()


# ── Détection d'obstacle ─────────────────────────────────────────────────

def obstacle_detecte():
    """Retourne True si un obstacle est à ≤ DISTANCE_OBSTACLE_CM."""
    d = mesure_distance_cm()
    return 0 < d <= DISTANCE_OBSTACLE_CM


# ── Programme principal : suivi de ligne + obstacle + transport ──────────

def main():
    setup_ultrason()
    position_repos()
    set_servo(SERVO_DIR, 90)

    print("=" * 50)
    print("TP2 — Suivi de ligne + Détection d'obstacle + Transport")
    print(f"Seuil obstacle : ≤ {DISTANCE_OBSTACLE_CM:.0f} cm")
    print("Ctrl+C pour arrêter")
    print("=" * 50)

    etape = "suivi"          # États : suivi, obstacle, transport, termine
    transport_effectue = False

    try:
        while True:
            # Vérifier obstacle en permanence
            if obstacle_detecte():
                print("\n⛔ Obstacle détecté ! Arrêt.")
                arret()
                time.sleep(1)

                if not transport_effectue:
                    print("📦 Transport de la pièce…")
                    transporter_piece()
                    transport_effectue = True
                    print("✅ Pièce transportée. Reprise du suivi.")
                else:
                    print("Pièce déjà transportée. Attente…")
                    time.sleep(2)

                continue

            # Suivi de ligne
            sl, sm, sr = lire_capteurs()
            action = decision_suivi(sl, sm, sr)
            print(f"  Capteurs L:{sl} M:{sm} R:{sr} → {action}")
            appliquer_action(action)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nArrêt.")
        arret()
        position_repos()
        pca.deinit()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
