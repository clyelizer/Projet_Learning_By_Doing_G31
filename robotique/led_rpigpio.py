#!/usr/bin/env python3
"""
TP1 Robotique — Contrôle de LEDs avec RPi.GPIO.

Brochage (Robot HAT / Raspberry Pi) :
    LED1 → GPIO09
    LED2 → GPIO25
    LED3 → GPIO11
"""

import RPi.GPIO as GPIO
from time import sleep

# Pins
LED2 = 25
LED3 = 11


def setup():
    """Configure les broches GPIO en sortie."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED2, GPIO.OUT)
    GPIO.setup(LED3, GPIO.OUT)


def cleanup():
    """Libère les ressources GPIO."""
    GPIO.cleanup()


def clignotement_alterne():
    """
    Cycle de clignotement :
      1. LED2 allumée, LED3 éteinte (1s)
      2. LED3 allumée, LED2 éteinte (1s)
      3. Les deux allumées (2s)
      4. Les deux éteintes (1s)
    """
    while True:
        # Allumer LED2, éteindre LED3
        GPIO.output(LED2, GPIO.HIGH)
        GPIO.output(LED3, GPIO.LOW)
        sleep(1)

        # Allumer LED3, éteindre LED2
        GPIO.output(LED2, GPIO.LOW)
        GPIO.output(LED3, GPIO.HIGH)
        sleep(1)

        # Allumer les deux LEDs
        GPIO.output(LED2, GPIO.HIGH)
        GPIO.output(LED3, GPIO.HIGH)
        sleep(2)

        # Éteindre les deux LEDs
        GPIO.output(LED2, GPIO.LOW)
        GPIO.output(LED3, GPIO.LOW)
        sleep(1)


if __name__ == "__main__":
    setup()
    try:
        clignotement_alterne()
    except KeyboardInterrupt:
        cleanup()
