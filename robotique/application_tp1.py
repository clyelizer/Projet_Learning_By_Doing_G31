#!/usr/bin/env python3
"""
TP1 Robotique — Application Pratique.

Spécifications :
    1. Détecter la présence d'un objet situé à ≤ 10 cm du robot (ultrason).
    2. Contrôler les servomoteurs du bras pour transporter l'objet
       d'une position A à une position B.
    3. Faire sonner le buzzer pendant 3 secondes une fois la pièce déposée.
    4. Ramener le bras à sa position initiale.
    5. Compter le nombre de pièces déplacées et l'afficher sur le terminal.

Bonus :
    L'ultrason balaie une zone (servo de balayage) et s'arrête dès qu'un
    objet est détecté, puis le robot le transporte de sa position initiale
    vers une position prédéfinie.

Dépendances :
    - ultrason.py  (capteur HC-SR04, GPIO23/24)
    - servo.py     (servos PCA9685)
    - buzzer.py    (buzzer GPIO18)

Canaux PCA9685 utilisés par le bras (Robot HAT Adeept) :
    Canal 0 : Servo de base (rotation horizontale / balayage)
    Canal 1 : Servo d'épaule
    Canal 2 : Servo de coude
    Canal 3 : Servo de pince
"""

import time
import RPi.GPIO as GPIO
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685
from gpiozero import TonalBuzzer

# ── Capteur ultrason ─────────────────────────────────────────────────────
TRIG = 23
ECHO = 24
SPEED_OF_SOUND_CM_PER_US = 0.0343
DISTANCE_SEUIL_CM = 10.0   # Seuil de détection d'objet

# ── Buzzer ────────────────────────────────────────────────────────────────
BUZZER_PIN = 18

# ── PCA9685 + servos du bras ─────────────────────────────────────────────
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

# Canaux du bras robotique
SERVO_BASE = 0    # Rotation horizontale (balayage)
SERVO_EPAULE = 1  # Épaule
SERVO_COUDE = 2   # Coude
SERVO_PINCE = 3   # Pince

# Positions angulaires (à calibrer selon le montage réel)
# Position A (prise de l'objet)
POS_A = {
    SERVO_BASE: 90,
    SERVO_EPAULE: 120,
    SERVO_COUDE: 60,
    SERVO_PINCE: 30,   # Pince ouverte
}

# Position B (dépôt de l'objet)
POS_B = {
    SERVO_BASE: 90,
    SERVO_EPAULE: 60,
    SERVO_COUDE: 120,
    SERVO_PINCE: 30,
}

# Position initiale (repos)
POS_INITIALE = {
    SERVO_BASE: 90,
    SERVO_EPAULE: 90,
    SERVO_COUDE: 90,
    SERVO_PINCE: 60,   # Pince fermée
}


# ── Fonctions bas niveau ─────────────────────────────────────────────────

def setup_ultrason():
    """Configure les broches du capteur HC-SR04."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.5)


def mesure_distance_cm():
    """Mesure la distance en cm. Retourne -1 si timeout."""
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


def set_servo(canal, angle):
    """Positionne un servo à l'angle donné."""
    s = servo.Servo(
        pca.channels[canal],
        min_pulse=500,
        max_pulse=2400,
        actuation_range=180,
    )
    s.angle = angle
    time.sleep(0.3)  # Laisser le temps au servo d'atteindre la position


def positionner_bras(positions):
    """Positionne tous les servos du bras selon un dictionnaire {canal: angle}."""
    for canal, angle in positions.items():
        set_servo(canal, angle)


def fermer_pince():
    """Ferme la pince pour saisir l'objet."""
    set_servo(SERVO_PINCE, 60)


def ouvrir_pince():
    """Ouvre la pince pour libérer l'objet."""
    set_servo(SERVO_PINCE, 30)


def sonner_buzzer(duree_s=3):
    """Fait sonner le buzzer pendant *duree_s* secondes."""
    tb = TonalBuzzer(BUZZER_PIN)
    fin = time.time() + duree_s
    while time.time() < fin:
        tb.play("C4")
        time.sleep(0.1)
        tb.play("E4")
        time.sleep(0.1)
    tb.stop()


# ── Séquence de transport ────────────────────────────────────────────────

def transporter_piece():
    """
    Séquence complète :
        A (prise) → fermer pince → B (dépôt) → ouvrir pince → position initiale.
    """
    print("  → Position A (prise)")
    positionner_bras(POS_A)
    time.sleep(0.5)
    fermer_pince()
    time.sleep(0.5)

    print("  → Position B (dépôt)")
    positionner_bras(POS_B)
    time.sleep(0.5)
    ouvrir_pince()
    time.sleep(0.5)

    print("  → Retour position initiale")
    positionner_bras(POS_INITIALE)


# ── Balayage ultrason (bonus) ────────────────────────────────────────────

def balayer_et_detecter(pas=5, angle_min=30, angle_max=150):
    """
    Balaye une zone avec le servo de base et l'ultrason.
    S'arrête dès qu'un objet est détecté à ≤ DISTANCE_SEUIL_CM.

    Returns
    -------
    int or None
        L'angle auquel l'objet a été détecté, ou None si rien trouvé.
    """
    for angle in range(angle_min, angle_max + 1, pas):
        set_servo(SERVO_BASE, angle)
        time.sleep(0.2)
        d = mesure_distance_cm()
        print(f"    balayage {angle}° → {d:.1f} cm")
        if 0 < d <= DISTANCE_SEUIL_CM:
            print(f"    ✅ Objet détecté à {angle}° !")
            return angle
    return None


# ── Programme principal ──────────────────────────────────────────────────

def main():
    setup_ultrason()
    positionner_bras(POS_INITIALE)
    compteur = 0

    print("=" * 50)
    print("TP1 — Application Pratique")
    print(f"Détection d'objet à ≤ {DISTANCE_SEUIL_CM:.0f} cm")
    print("Ctrl+C pour arrêter")
    print("=" * 50)

    try:
        while True:
            distance = mesure_distance_cm()
            print(f"\nDistance : {distance:.1f} cm")

            if 0 < distance <= DISTANCE_SEUIL_CM:
                print("🔍 Objet détecté ! Transport en cours…")
                transporter_piece()
                compteur += 1
                print(f"📦 Pièces déplacées : {compteur}")
                print("🔔 Buzzer 3 secondes")
                sonner_buzzer(3)
            else:
                # Bonus : balayage périodique
                print("Balayage de la zone…")
                angle_trouve = balayer_et_detecter()
                if angle_trouve is not None:
                    print("🔍 Objet trouvé au balayage ! Transport…")
                    transporter_piece()
                    compteur += 1
                    print(f"📦 Pièces déplacées : {compteur}")
                    sonner_buzzer(3)

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\nArrêt. Total pièces déplacées : {compteur}")
        positionner_bras(POS_INITIALE)
        pca.deinit()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
