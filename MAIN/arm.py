#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de contrôle du bras robotique du PiCar Pro.
Utilise les servomoteurs via PCA9685 (ports servo 0-15).
"""

import time
import threading

try:
    import Adafruit_PCA9685
    PCA_AVAILABLE = True
except ImportError:
    PCA_AVAILABLE = False
    print("[WARN] Adafruit_PCA9685 non disponible - mode simulation bras")


# Configuration des servos du bras
# Sur le PiCar Pro avec bras manipulateur:
# Servo 0: Base rotation (gauche/droite)
# Servo 1: Épaule (haut/bas)
# Servo 2: Coude (haut/bas)
# Servo 3: Pince (ouvert/fermé)
ARM_SERVOS = {
    'base': 0,
    'shoulder': 1,
    'elbow': 2,
    'gripper': 3,
}

# Valeurs PWM pour les positions (duty cycle 100-560 = 0°-180°)
# Ces valeurs sont à ajuster selon le montage mécanique
PWM_POSITIONS = {
    'base': {'center': 330, 'left': 200, 'right': 460},
    'shoulder': {'up': 200, 'down': 450, 'neutral': 330},
    'elbow': {'up': 250, 'down': 450, 'neutral': 350},
    'gripper': {'open': 400, 'closed': 200, 'neutral': 300},
}


class ArmController:
    """Contrôleur du bras robotique."""

    def __init__(self):
        self.pwm = None
        if PCA_AVAILABLE:
            try:
                self.pwm = Adafruit_PCA9685.PCA9685()
                self.pwm.set_pwm_freq(50)
                self.reset_position()
            except Exception as e:
                print(f"[ERROR] Échec init bras: {e}")
                self.pwm = None

    def set_servo(self, servo_name, pwm_value):
        """Positionne un servo à une valeur PWM donnée."""
        if self.pwm is None:
            return
        channel = ARM_SERVOS.get(servo_name)
        if channel is not None:
            self.pwm.set_pwm(channel, 0, int(pwm_value))

    def reset_position(self):
        """Position neutre du bras."""
        print("[ARM] Reset position")
        self.set_servo('base', PWM_POSITIONS['base']['center'])
        self.set_servo('shoulder', PWM_POSITIONS['shoulder']['neutral'])
        self.set_servo('elbow', PWM_POSITIONS['elbow']['neutral'])
        self.set_servo('gripper', PWM_POSITIONS['gripper']['open'])
        time.sleep(0.5)

    def open_gripper(self):
        """Ouvre la pince."""
        print("[ARM] Ouverture pince")
        self.set_servo('gripper', PWM_POSITIONS['gripper']['open'])
        time.sleep(0.3)

    def close_gripper(self):
        """Ferme la pince."""
        print("[ARM] Fermeture pince")
        self.set_servo('gripper', PWM_POSITIONS['gripper']['closed'])
        time.sleep(0.3)

    def move_down(self):
        """Descend le bras vers le sol."""
        print("[ARM] Descente")
        self.set_servo('shoulder', PWM_POSITIONS['shoulder']['down'])
        self.set_servo('elbow', PWM_POSITIONS['elbow']['down'])
        time.sleep(1.0)

    def move_up(self):
        """Remonte le bras."""
        print("[ARM] Remontée")
        self.set_servo('shoulder', PWM_POSITIONS['shoulder']['up'])
        self.set_servo('elbow', PWM_POSITIONS['elbow']['up'])
        time.sleep(1.0)


# Singleton
_arm_ctrl = None

def get_arm():
    """Retourne l'instance unique du contrôleur bras."""
    global _arm_ctrl
    if _arm_ctrl is None:
        _arm_ctrl = ArmController()
    return _arm_ctrl


def perform_sample():
    """
    Séquence complète de prélèvement:
    descendre → pause → remonter
    """
    arm = get_arm()

    print("\n[ARM] === DÉBUT PRÉLÈVEMENT ===")

    # 1. Ouvrir la pince
    arm.open_gripper()

    # 2. Descendre vers l'échantillon
    arm.move_down()

    # 3. Fermer la pince (saisir)
    arm.close_gripper()

    # 4. Pause (tenir l'échantillon)
    print("[ARM] Pause prélèvement (1s)")
    time.sleep(1.0)

    # 5. Remonter
    arm.move_up()

    # 6. Réinitialiser
    arm.reset_position()

    print("[ARM] === FIN PRÉLÈVEMENT ===\n")


def cleanup():
    """Nettoie les ressources du bras."""
    global _arm_ctrl
    if _arm_ctrl:
        _arm_ctrl.reset_position()
        _arm_ctrl = None


if __name__ == '__main__':
    print("Test bras robotique")
    perform_sample()
