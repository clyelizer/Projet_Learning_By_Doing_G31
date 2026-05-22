#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'exécution pour modèle 2WD arrière + direction servo avant.
Moteurs arrière : 0 (gauche), 1 (droite)
Servo direction : channel 0 (roues avant)
"""

import time
import sys

try:
    import Adafruit_PCA9685
    PCA_AVAILABLE = True
except ImportError:
    PCA_AVAILABLE = False
    print("[WARN] Adafruit_PCA9685 non disponible - mode simulation")


# --- CONFIGURATION MATERIELLE ---
# Moteurs arrière (2 roues motrices indépendantes)
MOTOR_CHANNELS = {
    'left_rear':  (0, 1),   # M0 : roue arrière gauche
    'right_rear': (2, 3),   # M1 : roue arrière droite
}

# Servo de direction sur les roues avant
STEERING_SERVO = 0

# Valeurs PWM direction (à ajuster selon votre montage mécanique)
STEERING_PWM = {
    'center': 330,
    'left':   200,   # ou 400 selon l'orientation du servo
    'right':  460,   # ou 100 selon l'orientation du servo
}

# Valeurs PWM moteurs (pont en H)
PWM_STOP = 0
PWM_FORWARD = 4095
PWM_BACKWARD = 4095


class MotorController:
    """Contrôleur pour 2WD + servo direction."""
    
    def __init__(self):
        self.pwm = None
        if PCA_AVAILABLE:
            try:
                self.pwm = Adafruit_PCA9685.PCA9685()
                self.pwm.set_pwm_freq(50)
                self.center_steering()
                self.stop_all()
            except Exception as e:
                print(f"[ERROR] Échec init PCA9685: {e}")
                self.pwm = None
    
    def _set_motor(self, motor_name, direction):
        """Contrôle un moteur arrière individuel."""
        if self.pwm is None:
            return
        ch_a, ch_b = MOTOR_CHANNELS[motor_name]
        if direction == 'forward':
            self.pwm.set_pwm(ch_a, 0, PWM_FORWARD)
            self.pwm.set_pwm(ch_b, 0, 0)
        elif direction == 'backward':
            self.pwm.set_pwm(ch_a, 0, 0)
            self.pwm.set_pwm(ch_b, 0, PWM_BACKWARD)
        else:
            self.pwm.set_pwm(ch_a, 0, 0)
            self.pwm.set_pwm(ch_b, 0, 0)
    
    def _set_steering(self, position):
        """Positionne le servo de direction."""
        if self.pwm is None:
            return
        pwm_val = STEERING_PWM.get(position, STEERING_PWM['center'])
        self.pwm.set_pwm(STEERING_SERVO, 0, pwm_val)
    
    # --- Mouvements de base ---
    
    def center_steering(self):
        """Remet les roues avant droites."""
        self._set_steering('center')
    
    def move_forward(self):
        """Avance tout droit (servo centré, 2 moteurs forward)."""
        self.center_steering()
        self._set_motor('left_rear', 'forward')
        self._set_motor('right_rear', 'forward')
    
    def move_backward(self):
        """Recule (servo centré, 2 moteurs backward)."""
        self.center_steering()
        self._set_motor('left_rear', 'backward')
        self._set_motor('right_rear', 'backward')
    
    def rotate_left(self):
        """
        Rotation sur place vers la gauche.
        Servo centré (ou légèrement gauche si besoin),
        moteur gauche recule, moteur droit avance.
        """
        self.center_steering()
        self._set_motor('left_rear', 'backward')
        self._set_motor('right_rear', 'forward')
    
    def rotate_right(self):
        """
        Rotation sur place vers la droite.
        Servo centré,
        moteur gauche avance, moteur droit recule.
        """
        self.center_steering()
        self._set_motor('left_rear', 'forward')
        self._set_motor('right_rear', 'backward')
    
    def stop_all(self):
        """Arrête les moteurs et centre la direction."""
        self._set_motor('left_rear', 'stop')
        self._set_motor('right_rear', 'stop')
        self.center_steering()


# Singleton
_motor_ctrl = None

def get_controller():
    global _motor_ctrl
    if _motor_ctrl is None:
        _motor_ctrl = MotorController()
    return _motor_ctrl


def run(command):
    """Exécute une commande du plan."""
    ctrl = get_controller()
    cmd_type = command['type']
    
    if cmd_type == 'rotate':
        direction = command['direction']
        duration = command['duration']
        angle = command['angle_deg']
        print(f"[EXEC] Rotation {direction} de {angle:.1f}° pendant {duration:.3f}s")
        
        if direction == 'left':
            ctrl.rotate_left()
        else:
            ctrl.rotate_right()
        
        time.sleep(duration)
        ctrl.stop_all()
        print("[EXEC] Rotation terminée")
    
    elif cmd_type == 'forward':
        duration = command['duration']
        distance = command['distance_cm']
        print(f"[EXEC] Avance de {distance:.1f} cm pendant {duration:.3f}s")
        ctrl.move_forward()
        time.sleep(duration)
        ctrl.stop_all()
        print("[EXEC] Avance terminée")
    
    elif cmd_type == 'action':
        action = command['action']
        wp_id = command['waypoint_id']
        print(f"[EXEC] Action '{action}' au waypoint {wp_id}")
        if action == 'sample':
            import arm
            arm.perform_sample()
    
    else:
        print(f"[WARN] Commande inconnue: {cmd_type}")


def cleanup():
    global _motor_ctrl
    if _motor_ctrl:
        _motor_ctrl.stop_all()
        _motor_ctrl = None


if __name__ == '__main__':
    ctrl = get_controller()
    print("Test: avance 1s")
    ctrl.move_forward()
    time.sleep(1)
    ctrl.stop_all()
    print("Test terminé")