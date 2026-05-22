#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de contrôle du bras robotique.
Servos : 1=base, 2=épaule, 3=coude, 4=pince
Le channel 0 est réservé au servo de direction des roues avant.
"""

import time

try:
    import Adafruit_PCA9685
    PCA_AVAILABLE = True
except ImportError:
    PCA_AVAILABLE = False
    print("[WARN] Adafruit_PCA9685 non disponible - mode simulation bras")


# --- CONFIGURATION SERVOS BRAS ---
# Channel 0 = direction (NE PAS UTILISER)
ARM_SERVOS = {
    'base':     1,   # Base rotation du bras
    'shoulder': 2,   # Épaule haut/bas
    'elbow':    3,   # Coude
    'gripper':  4,   # Pince ouvert/fermé
}

# Valeurs PWM (0-180° ≈ 100-560) — À AJUSTER selon votre montage
PWM_POSITIONS = {
    'base':     {'center': 330, 'left': 200, 'right': 460},
    'shoulder': {'up': 200, 'down': 450, 'neutral': 330},
    'elbow':    {'up': 250, 'down': 450, 'neutral': 350},
    'gripper':  {'open': 400, 'closed': 200, 'neutral': 300},
}


class ArmController:
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
        """Positionne un servo du bras."""
        if self.pwm is None:
            return
        channel = ARM_SERVOS.get(servo_name)
        if channel is not None:
            self.pwm.set_pwm(channel, 0, int(pwm_value))
    
    def reset_position(self):
        print("[ARM] Reset position")
        self.set_servo('base', PWM_POSITIONS['base']['center'])
        self.set_servo('shoulder', PWM_POSITIONS['shoulder']['neutral'])
        self.set_servo('elbow', PWM_POSITIONS['elbow']['neutral'])
        self.set_servo('gripper', PWM_POSITIONS['gripper']['open'])
        time.sleep(0.5)
    
    def open_gripper(self):
        print("[ARM] Ouverture pince")
        self.set_servo('gripper', PWM_POSITIONS['gripper']['open'])
        time.sleep(0.3)
    
    def close_gripper(self):
        print("[ARM] Fermeture pince")
        self.set_servo('gripper', PWM_POSITIONS['gripper']['closed'])
        time.sleep(0.3)
    
    def move_down(self):
        print("[ARM] Descente")
        self.set_servo('shoulder', PWM_POSITIONS['shoulder']['down'])
        self.set_servo('elbow', PWM_POSITIONS['elbow']['down'])
        time.sleep(1.0)
    
    def move_up(self):
        print("[ARM] Remontée")
        self.set_servo('shoulder', PWM_POSITIONS['shoulder']['up'])
        self.set_servo('elbow', PWM_POSITIONS['elbow']['up'])
        time.sleep(1.0)


# Singleton
_arm_ctrl = None

def get_arm():
    global _arm_ctrl
    if _arm_ctrl is None:
        _arm_ctrl = ArmController()
    return _arm_ctrl


def perform_sample():
    """Séquence complète de prélèvement."""
    arm = get_arm()
    print("\n[ARM] === DÉBUT PRÉLÈVEMENT ===")
    arm.open_gripper()
    arm.move_down()
    arm.close_gripper()
    print("[ARM] Pause prélèvement (1s)")
    time.sleep(1.0)
    arm.move_up()
    arm.reset_position()
    print("[ARM] === FIN PRÉLÈVEMENT ===\n")


def cleanup():
    global _arm_ctrl
    if _arm_ctrl:
        _arm_ctrl.reset_position()
        _arm_ctrl = None


if __name__ == '__main__':
    print("Test bras robotique")
    perform_sample()