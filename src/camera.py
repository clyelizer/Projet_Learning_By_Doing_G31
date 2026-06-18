#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de capture photo via Picamera2.
Prend N photos du sol et les sauvegarde dans data/photos/.

Usage:
    python camera.py          # test: prend 1 photo
"""

import os
import time

try:
    from picamera2 import Picamera2
    CAM_AVAILABLE = True
except ImportError:
    CAM_AVAILABLE = False
    print("[WARN] picamera2 non disponible - mode simulation")

# Chemin de sortie relatif au projet
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'photos')

# Instance singleton du module — la caméra reste allumée entre les appels
_camera = None


def _get_camera():
    """
    Retourne l'instance unique de Picamera2, avec initialisation paresseuse.
    Le délai de chauffe de 2s n'est subi qu'au premier appel.
    Retourne None si le matériel n'est pas disponible.
    """
    global _camera

    if not CAM_AVAILABLE:
        return None

    if _camera is not None:
        return _camera

    _camera = Picamera2()
    _camera.start()
    time.sleep(2)  # délai d'initialisation du capteur (une seule fois)
    return _camera


def take_photos(n=3, delay=0.5, output_dir=None):
    """
    Prend n photos et les sauvegarde.

    Args:
        n: nombre de photos à prendre (défaut: 3)
        delay: délai entre chaque photo en secondes (défaut: 0.5)
        output_dir: dossier de sortie (défaut: ../data/photos/)

    Returns:
        list[str]: chemins des fichiers sauvegardés, ou liste vide si caméra indisponible
    """
    cam = _get_camera()
    if cam is None:
        print("[WARN] Caméra indisponible - aucune photo prise")
        return []

    if output_dir is None:
        output_dir = OUTPUT_DIR

    os.makedirs(output_dir, exist_ok=True)

    paths = []
    try:
        for i in range(1, n + 1):
            timestamp = int(time.time() * 1000)
            filename = f"wp_photo_{timestamp}_{i:02d}.jpg"
            filepath = os.path.join(output_dir, filename)
            cam.capture_file(filepath)
            paths.append(filepath)
            print(f"[CAM] Photo {i}/{n} sauvegardée : {filepath}")

            if i < n:
                time.sleep(delay)

    except Exception as e:
        print(f"[ERROR] Échec capture photo: {e}")

    return paths


def cleanup():
    """
    Arrête et ferme la caméra si elle est active.
    Idempotent — peut être appelé plusieurs fois sans effet de bord.
    """
    global _camera

    if _camera is not None:
        try:
            _camera.stop()
            _camera.close()
        except Exception as e:
            print(f"[ERROR] Échec lors de l'arrêt de la caméra: {e}")
        finally:
            _camera = None


if __name__ == '__main__':
    print("Test capture photo (1 photo)")
    photos = take_photos(n=1)
    if photos:
        print(f"Photo sauvegardée : {photos[0]}")
    else:
        print("Aucune photo prise (caméra indisponible)")
    cleanup()
