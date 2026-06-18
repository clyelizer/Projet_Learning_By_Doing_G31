#!/usr/bin/env python3
"""
TP1 Robotique — Capteur de distance ultrason HC-SR04.

Principe (voir chronogramme du document) :
    1. Envoyer une impulsion HIGH de 10 µs sur la broche Trig.
    2. Le module émet 8 impulsions ultrasoniques à 40 kHz.
    3. La broche Echo passe à HIGH pendant la durée de l'aller-retour.
    4. distance_cm = (durée_echo_us × 0.0343) / 2

Brochage (Robot HAT Adeept, connecteur X9) :
    VCC  → 5V
    Trig → GPIO23
    Echo → GPIO24
    GND  → GND
"""

import time
import RPi.GPIO as GPIO

# --- Brochage ---
TRIG = 23
ECHO = 24

# Constante : vitesse du son ≈ 343 m/s → 0.0343 cm/µs
SPEED_OF_SOUND_CM_PER_US = 0.0343


def setup():
    """Configure les broches GPIO."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    # S'assurer que Trig est à LOW au démarrage
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.5)  # Stabilisation du capteur


def cleanup():
    """Libère les ressources GPIO."""
    GPIO.cleanup()


def mesure_distance_cm():
    """
    Effectue une mesure de distance.

    Returns
    -------
    float
        Distance en centimètres, ou -1 si erreur de mesure (timeout).
    """
    # 1. Impulsion Trig de 10 µs
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)          # 10 µs
    GPIO.output(TRIG, GPIO.LOW)

    # 2. Mesurer la durée de l'impulsion Echo
    debut = time.time()
    timeout_debut = debut + 0.04  # Timeout 40 ms (~7 m max)

    # Attendre le front montant de Echo
    while GPIO.input(ECHO) == GPIO.LOW:
        debut = time.time()
        if debut > timeout_debut:
            return -1

    # Attendre le front descendant de Echo
    while GPIO.input(ECHO) == GPIO.HIGH:
        fin = time.time()
        if fin > timeout_debut:
            return -1

    # 3. Calculer la distance
    duree_us = (fin - debut) * 1_000_000  # secondes → µs
    distance = (duree_us * SPEED_OF_SOUND_CM_PER_US) / 2.0
    return distance


def mesure_continue(intervalle_s=0.5):
    """
    Boucle de mesure continue. Affiche la distance en cm et mm.
    Ctrl+C pour arrêter.
    """
    print("Capteur HC-SR04 — mesure continue (Ctrl+C pour arrêter)")
    try:
        while True:
            d_cm = mesure_distance_cm()
            if d_cm < 0:
                print("⚠️  Erreur de mesure (timeout)")
            else:
                print(f"Distance : {d_cm:.2f} cm  =  {d_cm * 10:.1f} mm")
            time.sleep(intervalle_s)
    except KeyboardInterrupt:
        print("Arrêt.")


if __name__ == "__main__":
    setup()
    try:
        mesure_continue()
    finally:
        cleanup()
