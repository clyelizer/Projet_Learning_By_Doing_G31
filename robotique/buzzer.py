#!/usr/bin/env python3
"""
TP1 Robotique — Contrôle du Buzzer avec gpiozero.

Brochage (Robot HAT / Raspberry Pi) :
    Buzzer → GPIO18
"""

import time
from gpiozero import TonalBuzzer


BUZZER_PIN = 18


def jouer_note(note="C4", duree=0.5):
    """Joue une note unique."""
    tb = TonalBuzzer(BUZZER_PIN)
    tb.play(note)
    time.sleep(duree)
    tb.stop()


def jouer_melodie():
    """Joue une mélodie simple (gamme de Do)."""
    tb = TonalBuzzer(BUZZER_PIN)
    gamme = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]

    for note in gamme:
        tb.play(note)
        time.sleep(0.3)

    tb.stop()


def sonner_alarme(duree_s=3):
    """Fait sonner le buzzer pendant une durée donnée (secondes)."""
    tb = TonalBuzzer(BUZZER_PIN)
    fin = time.time() + duree_s

    while time.time() < fin:
        tb.play("C4")
        time.sleep(0.1)
        tb.play("E4")
        time.sleep(0.1)

    tb.stop()


if __name__ == "__main__":
    print("Test buzzer — mélodie")
    jouer_melodie()
