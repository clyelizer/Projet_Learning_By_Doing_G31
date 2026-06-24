#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Correctifs auto et manuels pour les problèmes détectés.
Chaque heal est une fonction prenant check_result en paramètre,
retournant {"status": "ok"|"failed"|"skipped", "detail": "...", "safe": bool}
"""

import os
import signal
import subprocess
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def _safe(detail):
    return {"status": "ok", "detail": detail, "safe": True}

def _unsafe(detail):
    return {"status": "skipped", "detail": f"MANUEL : {detail}", "safe": False}

def _failed(detail):
    return {"status": "failed", "detail": detail, "safe": True}


# ── Healers ────────────────────────────────────────────────────────

def heal_pca9685(check):
    """Reset le PCA9685 via I2C."""
    if check["status"] != "error":
        return _safe("PCA9685 déjà OK, rien à faire")
    rc, out, err = _run(["i2cset", "-y", "1", "0x5f", "0x00", "0x00"])
    if rc != 0:
        return _failed(f"Reset I2C échoué: {err}")
    time.sleep(0.5)
    # Vérifier
    rc2, out2, _ = _run(["i2cdetect", "-y", "1"])
    if "5f" in out2:
        return _safe("Reset PCA9685 réussi (0x5f de nouveau visible)")
    return _failed("Reset I2C exécuté mais PCA9685 toujours invisible")


def heal_camera(check):
    """Redémarre le driver caméra (libcamera)."""
    # Un simple cleanup/réinit côté Python est suffisant
    import importlib
    try:
        sys.path.insert(0, str(PROJECT_DIR / "src"))
        import camera
        if hasattr(camera, 'cleanup'):
            camera.cleanup()
        # Réinitialiser
        importlib.reload(camera)
        return _safe("Caméra nettoyée et réinitialisée")
    except Exception as e:
        # Tentative plus agressive
        _run(["sudo", "modprobe", "-r", "bcm2835-v4l2"], timeout=5)
        time.sleep(0.5)
        rc, out, err = _run(["sudo", "modprobe", "bcm2835-v4l2"], timeout=5)
        if rc == 0:
            return _safe("Module caméra reloadé via modprobe")
        return _failed(f"Échec reset caméra: {err}")


def heal_flask(check):
    """Redémarre le serveur Flask."""
    # Tuer les processus app.py existants
    rc, out, _ = _run(["pgrep", "-f", "app.py"])
    if rc == 0 and out:
        pids = out.strip().splitlines()
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass
        time.sleep(1)
    # Relancer
    app_path = str(PROJECT_DIR / "src" / "web" / "app.py")
    rc2, out2, _ = _run(["python3", app_path, "&"])
    time.sleep(2)
    # Vérifier
    rc3, http, _ = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                          "http://127.0.0.1:5000/"])
    if rc3 == 0 and http == "200":
        return _safe("Flask redémarré et répond 200")
    return _failed("Flask relancé mais ne répond pas")


def heal_disk(check):
    """Nettoie le cache audio."""
    audio_dir = PROJECT_DIR / "data" / "audio"
    if not audio_dir.exists():
        return _safe("Aucun cache audio à nettoyer")
    count = 0
    for f in audio_dir.iterdir():
        if f.is_file() and f.suffix in (".mp3", ".wav"):
            f.unlink()
            count += 1
    return _safe(f"Cache audio nettoyé : {count} fichier(s) supprimé(s)")


def heal_sensor(check):
    """Reset de la connexion série Arduino via DTR."""
    try:
        import serial
        for port in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"]:
            if Path(port).exists():
                s = serial.Serial(port, 115200, timeout=0.5)
                # Toggle DTR pour reset Arduino
                s.setDTR(False)
                time.sleep(0.1)
                s.setDTR(True)
                time.sleep(1)
                s.close()
                return _safe(f"Reset DTR sur {port} effectué")
        return _failed("Aucun port série trouvé pour le reset")
    except ImportError:
        return _failed("pyserial non installé")
    except Exception as e:
        return _failed(f"Reset DTR échoué: {e}")


# ── Auto-heal dispatcher ──────────────────────────────────────────

HEAL_MAP = {
    "PCA9685": heal_pca9685,
    "Caméra": heal_camera,
    "Flask": heal_flask,
    "Disque": heal_disk,
    "Capteur sol": heal_sensor,
}


def auto_heal(checks):
    """
    Exécute les correctifs automatiques pour les checks en erreur.
    Retourne la liste des résultats de healing.
    """
    results = []
    for check in checks:
        if check["status"] not in ("error", "warning"):
            continue
        if not check.get("suggested_action"):
            continue
        name = check["name"]
        healer = HEAL_MAP.get(name)
        if healer:
            try:
                result = healer(check)
                result["check_name"] = name
            except Exception as e:
                result = {"status": "failed", "detail": str(e),
                          "safe": True, "check_name": name}
            results.append(result)
    return results
