#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'enregistrement vidéo H264 via ffmpeg (V4L2 direct).
Ne passe PAS par l'encodeur Picamera2 — utilise /dev/video0 directement.

Usage:
    python camera_video.py                              # test: 5s → data/videos/
    python camera_video.py --duration 10 --out test.h264
"""

import os
import signal
import subprocess
import sys
import time

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VIDEO_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'videos')

_signal_registered = False
_recording_process = None
_preview_active = False


def _sig_handler(signum, frame):
    """Arrête l'enregistrement ou le preview sur Ctrl+C."""
    global _recording_process, _preview_active
    if _preview_active:
        print("\n[CAM] Arrêt preview...")
        _preview_active = False
        return
    print("\n[CAM] Signal reçu — arrêt enregistrement...")
    if _recording_process is not None:
        _recording_process.terminate()
        _recording_process.wait(timeout=2)
    sys.exit(1)


def _register_signals():
    """Enregistre les handlers SIGINT/SIGTERM une seule fois."""
    global _signal_registered
    if not _signal_registered:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
        _signal_registered = True


def record_video(duration_s=5, output_path=None):
    """
    Enregistre une vidéo H264 via ffmpeg depuis /dev/video0.

    Args:
        duration_s: durée en secondes (défaut: 5)
        output_path: chemin .h264 (défaut: data/videos/video_<ts>.h264)

    Returns:
        str: chemin du fichier, ou None si /dev/video0 absent
    """
    if not os.path.exists('/dev/video0'):
        print("[WARN] /dev/video0 absent — pas de vidéo")
        return None

    _register_signals()

    if output_path is None:
        os.makedirs(DEFAULT_VIDEO_DIR, exist_ok=True)
        timestamp = int(time.time() * 1000)
        output_path = os.path.join(DEFAULT_VIDEO_DIR,
                                   f"video_{timestamp}.h264")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"[CAM] Début enregistrement vidéo {duration_s}s → {output_path}")

    global _recording_process
    _recording_process = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "v4l2",
        "-input_format", "mjpeg",
        "-video_size", "640x480",
        "-i", "/dev/video0",
        "-t", str(duration_s),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        output_path,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ret = _recording_process.wait()
    _recording_process = None

    if ret != 0:
        print(f"[ERROR] ffmpeg a échoué (code {ret})")
        return None

    print(f"[CAM] Vidéo sauvegardée : {output_path}")
    return output_path


def preview():
    """
    Ouvre une fenêtre de preview en direct (flux caméra).
    Appuyer sur 'q' ou Ctrl+C pour fermer.

    Returns:
        bool: True si le preview a fonctionné, False sinon
    """
    global _preview_active

    if not CV2_AVAILABLE:
        print("[WARN] OpenCV non disponible — pas de preview")
        return False

    if not os.path.exists('/dev/video0'):
        print("[WARN] /dev/video0 absent — pas de preview")
        return False

    _register_signals()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Impossible d'ouvrir /dev/video0")
        return False

    # Forcer MJPEG à 640x480
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[CAM] Preview démarré — 'q' ou Ctrl+C pour fermer")
    _preview_active = True

    try:
        while _preview_active:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Perte du flux caméra")
                break

            cv2.imshow("Camera Preview (q=quitter)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    finally:
        _preview_active = False
        cap.release()
        cv2.destroyAllWindows()
        print("[CAM] Preview fermé")

    return True


def cleanup():
    """Tue ffmpeg s'il tourne encore."""
    global _recording_process
    if _recording_process is not None:
        _recording_process.terminate()
        _recording_process.wait(timeout=2)
        _recording_process = None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Enregistrement et preview vidéo")
    parser.add_argument('--duration', type=int, default=5,
                        help='Durée en secondes (défaut: 5)')
    parser.add_argument('--out', type=str, default=None,
                        help='Chemin de sortie (défaut: data/videos/)')
    parser.add_argument('--preview', action='store_true',
                        help='Ouvrir une fenêtre de preview en direct')
    args = parser.parse_args()

    if args.preview:
        preview()
    else:
        print(f"Enregistrement vidéo {args.duration}s... (Ctrl+C pour arrêter)")
        path = record_video(duration_s=args.duration, output_path=args.out)
        if path:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"Terminé : {path} ({size_mb:.1f} MB)")
        else:
            print("Échec.")
        cleanup()
