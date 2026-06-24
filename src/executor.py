#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'exécution pour modèle 2WD arrière + direction servo avant.
Servo direction : CH0 (roues avant)
Moteurs arrière M1 (gauche) : CH14 (IN1), CH15 (IN2)
Moteurs arrière M2 (droite) : CH13 (IN1), CH12 (IN2)
Channels CH1-CH4 réservés au bras robotique (ne pas toucher).
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
    'left_rear':  (14, 15),  # M1 gauche : IN1=CH14, IN2=CH15
    'right_rear': (13, 12),  # M2 droite : IN1=CH13, IN2=CH12
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
PWM_MAX = 4095  # 100% duty cycle (vitesse max)
PWM_DEFAULT = 2048  # 50% duty cycle (vitesse par défaut si motor_speed non défini)


class MotorController:
    """Contrôleur pour 2WD + servo direction."""
    
    def __init__(self):
        self.pwm = None
        self._motor_pwm = PWM_DEFAULT  # vitesse par défaut: 50%
        if PCA_AVAILABLE:
            try:
                self.pwm = Adafruit_PCA9685.PCA9685(address=0x5f)
                self.pwm.set_pwm_freq(50)
                self.center_steering()
                self.stop_all()
            except Exception as e:
                print(f"[ERROR] Échec init PCA9685: {e}")
                self.pwm = None
    
    def set_motor_speed(self, fraction):
        """
        Définit la vitesse des moteurs (0.0 à 1.0).
        
        Args:
            fraction: float entre 0.0 (arrêt) et 1.0 (vitesse max)
        """
        fraction = max(0.0, min(1.0, fraction))
        self._motor_pwm = int(PWM_MAX * fraction)
        print(f"[EXEC] Vitesse moteurs réglée à {fraction*100:.0f}% (PWM={self._motor_pwm})")
    
    def _set_motor(self, motor_name, direction):
        """Contrôle un moteur arrière individuel.

        Note: la polarité IN1/IN2 dépend du câblage physique du pont H.
        Si le robot recule quand il doit avancer, inverser ch_a↔ch_b
        dans MOTOR_CHANNELS (plutôt que toucher à cette méthode).
        """
        if self.pwm is None:
            return
        ch_a, ch_b = MOTOR_CHANNELS[motor_name]
        # forward:  IN1=PWM, IN2=LOW  → moteur tourne vers l'avant
        # backward: IN1=LOW, IN2=PWM  → moteur tourne vers l'arrière
        if direction == 'forward':
            self.pwm.set_pwm(ch_a, 0, self._motor_pwm)
            self.pwm.set_pwm(ch_b, 0, 0)
        elif direction == 'backward':
            self.pwm.set_pwm(ch_a, 0, 0)
            self.pwm.set_pwm(ch_b, 0, self._motor_pwm)
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
        Virage en courbe vers la gauche (2WD car-style).
        Servo tourné à gauche, les deux moteurs avancent.
        Le robot décrit un arc de cercle — PAS une rotation sur place.
        """
        self._set_steering('left')
        self._set_motor('left_rear', 'forward')
        self._set_motor('right_rear', 'forward')
    
    def rotate_right(self):
        """
        Virage en courbe vers la droite (2WD car-style).
        Servo tourné à droite, les deux moteurs avancent.
        Le robot décrit un arc de cercle — PAS une rotation sur place.
        """
        self._set_steering('right')
        self._set_motor('left_rear', 'forward')
        self._set_motor('right_rear', 'forward')
    
    def stop_all(self):
        """Arrête les moteurs et centre la direction."""
        self._set_motor('left_rear', 'stop')
        self._set_motor('right_rear', 'stop')
        self.center_steering()
        time.sleep(0.3)  # délai pour que le servo revienne physiquement au centre


# Singleton
_motor_ctrl = None

def get_controller():
    global _motor_ctrl
    if _motor_ctrl is None:
        _motor_ctrl = MotorController()
    return _motor_ctrl


def run(command):
    """
    Exécute une commande de mouvement.
    Gère uniquement les types 'rotate' et 'forward'.
    Les actions (probe, photo) sont gérées par main.py.
    """
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
    
    else:
        print(f"[WARN] Commande inconnue dans executor: {cmd_type}")


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
