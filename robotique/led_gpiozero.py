#!/usr/bin/env python3
"""
TP1 Robotique — Contrôle de LEDs avec gpiozero.

Brochage (Robot HAT / Raspberry Pi) :
    LED1 → GPIO09
    LED2 → GPIO25
    LED3 → GPIO11
"""

from gpiozero import LED
from time import sleep


def demo_led_basics():
    """Démonstration des opérations de base sur une LED."""
    led = LED(17)

    led.on()                               # Allume la LED
    sleep(1)
    led.off()                              # Éteint la LED
    sleep(1)
    led.toggle()                           # Inverse l'état actuel
    sleep(1)
    led.blink()                            # Clignote automatiquement
    sleep(3)
    led.blink(on_time=0.5, off_time=0.5)   # Clignote avec durées personnalisées
    sleep(3)
    led.blink(n=3)                         # Clignote 3 fois
    sleep(3)
    print("LED allumée ?", led.is_lit)     # Vérifie si la LED est allumée


def chenillard():
    """Allume les 3 LEDs en chenillard (LED1 → LED2 → LED3)."""
    led1 = LED(9)   # GPIO09
    led2 = LED(25)  # GPIO25
    led3 = LED(11)  # GPIO11

    leds = [led1, led2, led3]

    while True:
        for led in leds:
            led.on()
            sleep(0.3)
            led.off()


if __name__ == "__main__":
    demo_led_basics()
