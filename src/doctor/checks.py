#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batterie de tests de diagnostic hardware et software.
Chaque check est une fonction sans paramètre retournant un dict :

    {"name": "PCA9685", "status": "ok"|"warning"|"error",
     "detail": "...", "value": ..., "suggested_action": "..."}
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent


# ── Helpers ───────────────────────────────────────────────────────

def _run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", "command not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def _ok(name, detail="", value=None):
    return {"name": name, "status": "ok", "detail": detail,
            "value": value, "suggested_action": None}


def _warn(name, detail, value=None, action=None):
    return {"name": name, "status": "warning", "detail": detail,
            "value": value, "suggested_action": action}


def _err(name, detail, value=None, action=None):
    return {"name": name, "status": "error", "detail": detail,
            "value": value, "suggested_action": action}


# ── 1. PCA9685 ─────────────────────────────────────────────────────

def check_pca9685():
    """Vérifie que le PCA9685 répond sur l'adresse I2C 0x5f."""
    rc, out, _ = _run(["i2cdetect", "-y", "1"])
    if rc != 0:
        return _err("PCA9685", "i2cdetect non disponible (sudo requis ?)",
                     action="Installer i2c-tools ou exécuter en root")
    if "5f" in out:
        return _ok("PCA9685", "Répond sur 0x5f")
    # Essai de reset
    _, out2, _ = _run(["i2cset", "-y", "1", "0x5f", "0x00", "0x00"])
    if "Error" not in out2 and out2 != "":
        return _warn("PCA9685", "Réinitialisé par reset I2C",
                      action="Reset I2C exécuté - nouveau check OK")
    return _err("PCA9685", "Non détecté sur 0x5f même après reset",
                 action="Vérifier câblage I2C (SDA/SCL), tension, ou remplacer module")


# ── 2. Moteurs ─────────────────────────────────────────────────────

def check_motors():
    """
    Test rapide des moteurs avant/arrière.
    ATTENTION : le robot peut bouger légèrement.
    """
    try:
        sys.path.insert(0, str(PROJECT_DIR / "src"))
        from executor import MotorController, PCA_AVAILABLE
    except ImportError:
        return _err("Moteurs", "executor.py non importable")
    if not PCA_AVAILABLE:
        return _warn("Moteurs", "Adafruit_PCA9685 non installé - mode simulation",
                      action="pip install Adafruit_PCA9685 sur le Pi")

    mc = MotorController()
    if mc.pwm is None:
        return _err("Moteurs", "Échec init PCA9685 - moteurs non joignables",
                     action="Vérifier PCA9685 + câblage pont H")

    # Vérifier que les moteurs ne sont pas bloqués en envoyant une impulsion
    try:
        mc._set_motor("left_rear", "forward")   # très courte impulsion
        time.sleep(0.05)
        mc.stop_all()
        mc._set_motor("right_rear", "forward")
        time.sleep(0.05)
        mc.stop_all()
        return _ok("Moteurs", "Impulsions OK (0.05s chacun)")
    except Exception as e:
        return _err("Moteurs", f"Exception: {e}",
                     action="Vérifier pont H et alimentation moteurs")


# ── 3. Direction (servo) ──────────────────────────────────────────

def check_steering():
    """Vérifie le servo de direction (CH0)."""
    try:
        sys.path.insert(0, str(PROJECT_DIR / "src"))
        from executor import MotorController, PCA_AVAILABLE, STEERING_PWM
    except ImportError:
        return _err("Direction", "executor.py non importable")
    if not PCA_AVAILABLE:
        return _warn("Direction", "Adafruit_PCA9685 non installé",
                      action="pip install Adafruit_PCA9685")

    mc = MotorController()
    if mc.pwm is None:
        return _err("Direction", "PCA9685 indisponible")
    try:
        mc.center_steering()
        time.sleep(0.2)
        mc.steer_left()
        time.sleep(0.2)
        mc.center_steering()
        return _ok("Direction", "Servo CH0 centre→gauche→centre OK")
    except Exception as e:
        return _err("Direction", f"Exception: {e}",
                     action="Vérifier servo CH0 et alimentation")


# ── 4. Bras robotique ─────────────────────────────────────────────

def check_arm():
    """Vérifie les servos du bras (CH1-CH4)."""
    try:
        sys.path.insert(0, str(PROJECT_DIR / "src"))
        from arm import ArmController, PCA_AVAILABLE
    except ImportError:
        return _err("Bras", "arm.py non importable")
    if not PCA_AVAILABLE:
        return _warn("Bras", "Adafruit_PCA9685 non installé",
                      action="pip install Adafruit_PCA9685")
    arm_ctrl = ArmController()
    if arm_ctrl.pwm is None:
        return _err("Bras", "PCA9685 indisponible pour le bras")
    try:
        arm_ctrl.reset_position()
        arm_ctrl.lower_probe()
        time.sleep(0.3)
        arm_ctrl.raise_probe()
        arm_ctrl.reset_position()
        return _ok("Bras", "CH1-CH4 : reset → descente → remontée → reset OK")
    except Exception as e:
        return _err("Bras", f"Exception: {e}",
                     action="Vérifier servos CH1-CH4 et câblage")


# ── 5. Caméra ──────────────────────────────────────────────────────

def check_camera():
    """Vérifie qu'une caméra est détectée."""
    rc, out, _ = _run(["libcamera-still", "--list-cameras"], timeout=3)
    if rc == 0 and out and "Available cameras" in out:
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return _ok("Caméra", f"Détectée : {len(lines)-1} caméra(s)", value=out[:150])
    # Fallback v4l2
    rc2, out2, _ = _run(["v4l2-ctl", "--list-devices"], timeout=3)
    if rc2 == 0 and "video" in out2.lower():
        return _ok("Caméra", f"Détectée via v4l2", value=out2[:150])
    return _warn("Caméra", "Non détectée par libcamera ni v4l2",
                  action="Vérifier connexion CSI ou USB")


# ── 6. Capteur sol (Arduino) ──────────────────────────────────────

def check_sensor():
    """Vérifie si le capteur série (Arduino) est accessible."""
    # Essayer différents ports
    for port in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0"]:
        if Path(port).exists():
            # Test simple : ouvrir le port et lire
            try:
                import serial
                s = serial.Serial(port, 115200, timeout=1)
                s.write(b"R\r\n")
                line = s.readline().decode(errors="replace").strip()
                s.close()
                if line and ("EC" in line or "pH" in line or "Temp" in line
                             or line[0].isdigit()):
                    return _ok("Capteur sol", f"Port {port} répond OK",
                                value=line[:100])
                return _warn("Capteur sol", f"Port {port} accessible mais données illisibles",
                              value=line[:100],
                              action="Vérifier le baud rate ou le code Arduino")
            except ImportError:
                return _warn("Capteur sol", "pyserial non installé",
                              action="pip install pyserial")
            except Exception as e:
                return _warn("Capteur sol", f"Port {port} : {e}",
                              action="Vérifier connexion USB Arduino")
    return _err("Capteur sol", "Aucun port série trouvé (/dev/ttyACM* ou USB*)",
                 action="Brancher l'Arduino via USB")


# ── 7. Flask ───────────────────────────────────────────────────────

def check_flask():
    """Vérifie si le serveur Flask répond."""
    rc, out, _ = _run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                        "http://127.0.0.1:5000/"])
    if rc == 0 and out == "200":
        return _ok("Flask", "Répond 200 sur port 5000")
    # Vérifier si le processus tourne
    rc2, out2, _ = _run(["pgrep", "-f", "app.py"])
    if rc2 == 0 and out2:
        return _warn("Flask", f"Processus trouvé (PID {out2.split()[0]}) mais ne répond pas",
                      action="Redémarrer app.py")
    return _err("Flask", "Processus introuvable et ne répond pas",
                 action="python src/web/app.py &")


# ── 8. Disque ──────────────────────────────────────────────────────

def check_disk():
    """Vérifie l'espace disque disponible."""
    try:
        stat = os.statvfs("/")
        available = stat.f_frsize * stat.f_bavail // (1024 * 1024)
        total = stat.f_frsize * stat.f_blocks // (1024 * 1024)
        pct = round((total - available) / total * 100, 1)
        detail = f"{available} Mo libre / {total} Mo total ({pct}% utilisé)"
        if available < 100:
            return _err("Disque", f"Plus que {available} Mo !", value=pct,
                        action="Nettoyer : rm -rf data/audio/*.mp3")
        if pct > 90:
            return _warn("Disque", f"{detail} > 90%", value=pct,
                         action="Nettoyer les caches audio")
        return _ok("Disque", detail, value=pct)
    except Exception as e:
        return _warn("Disque", str(e)[:100])


# ── 9. RAM ─────────────────────────────────────────────────────────

def check_ram():
    """Vérifie la mémoire disponible."""
    try:
        lines = Path("/proc/meminfo").read_text().splitlines()
        info = {}
        for l in lines:
            parts = l.split()
            if parts[0].rstrip(":") in ("MemTotal", "MemAvailable"):
                info[parts[0].rstrip(":")] = int(parts[1])
        total_mb = info.get("MemTotal", 0) // 1024
        avail_mb = info.get("MemAvailable", 0) // 1024
        if avail_mb < 128:
            return _err("RAM", f"Plus que {avail_mb} Mo libre sur {total_mb} Mo",
                        value=avail_mb,
                        action="Arrêter les processus lourds (Chromium, VSCode…)")
        if avail_mb < 256:
            return _warn("RAM", f"{avail_mb} Mo libre sur {total_mb} Mo",
                         value=avail_mb,
                         action="Surveiller : risque de swap")
        return _ok("RAM", f"{avail_mb} Mo libre sur {total_mb} Mo", value=avail_mb)
    except Exception:
        return _warn("RAM", "Impossible de lire /proc/meminfo")


# ── 10. Température CPU ────────────────────────────────────────────

def check_cpu_temp():
    """Vérifie la température CPU."""
    temp = None
    for path in ["/sys/class/thermal/thermal_zone0/temp"]:
        try:
            raw = Path(path).read_text().strip()
            temp = round(int(raw) / 1000, 1)
            break
        except Exception:
            continue
    if temp is None:
        rc, out, _ = _run(["vcgencmd", "measure_temp"])
        if rc == 0 and out:
            try:
                temp = float(out.replace("temp=", "").replace("'C", ""))
            except ValueError:
                pass
    if temp is None:
        return _warn("Temp CPU", "Indisponible (pas de capteur)")
    if temp >= 80:
        return _err("Temp CPU", f"{temp}°C → RISQUE DE THROTTLING",
                     value=temp, action="Vérifier ventilation / heaksink / réduire charge")
    if temp >= 70:
        return _warn("Temp CPU", f"{temp}°C → Attention",
                      value=temp, action="Surveiller la ventilation")
    return _ok("Temp CPU", f"{temp}°C", value=temp)


# ── 11. Modèles ML ─────────────────────────────────────────────────

def check_ml_models():
    """Vérifie que les modèles .pkl sont lisibles."""
    model_dir = PROJECT_DIR / "src" / "ml" / "02_models"
    if not model_dir.exists():
        return _err("Modèles ML", "Dossier 02_models introuvable",
                     action="Relancer model_training.py")
    pkl_files = list(model_dir.glob("*.pkl"))
    if not pkl_files:
        return _err("Modèles ML", "Aucun fichier .pkl",
                     action="Relancer model_training.py")
    corrupted = 0
    for f in pkl_files:
        # Vérifier que le fichier n'est pas vide et commence par un pickled object
        data = f.read_bytes()
        if len(data) < 50:
            corrupted += 1
    if corrupted:
        return _warn("Modèles ML", f"{corrupted}/{len(pkl_files)} fichiers suspects",
                      action="Vérifier l'intégrité des .pkl")
    return _ok("Modèles ML", f"{len(pkl_files)} fichiers .pkl OK")


# ── 12. Base référence ─────────────────────────────────────────────

def check_base_reference():
    """Vérifie que la base de référence est lisible."""
    path = PROJECT_DIR / "src" / "ml" / "01_databases" / "base_reference_agricole.json"
    if not path.exists():
        return _err("Base réf.", "base_reference_agricole.json introuvable",
                     action="Relancer eda_preprocessing.py")
    try:
        data = json.loads(path.read_text())
        count = len(data.get("cultures", []))
        if count < 5:
            return _warn("Base réf.", f"Seulement {count} cultures", value=count)
        return _ok("Base réf.", f"{count} cultures chargées", value=count)
    except json.JSONDecodeError:
        return _err("Base réf.", "Fichier JSON corrompu",
                     action="Restaurer depuis backup")


# ── Tous les checks ────────────────────────────────────────────────

ALL_CHECKS = [
    check_pca9685,
    check_motors,
    check_steering,
    check_arm,
    check_camera,
    check_sensor,
    check_flask,
    check_disk,
    check_ram,
    check_cpu_temp,
    check_ml_models,
    check_base_reference,
]


def run_all_checks():
    """Exécute tous les tests, retourne une liste de résultats."""
    results = []
    for check in ALL_CHECKS:
        try:
            result = check()
        except Exception as e:
            result = _err(check.__name__.replace("check_", "").title(),
                          f"Exception: {e}")
        results.append(result)
    return results
