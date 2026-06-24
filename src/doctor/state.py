#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capture l'état global du robot : matériel, système, services.
Toutes les fonctions retournent des dict sérialisables en JSON.
"""

import os
import subprocess
import time
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # src/../

# ── Helpers ───────────────────────────────────────────────────────

def _run(cmd, timeout=5):
    """Exécute une commande, retourne stdout ou None."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def _run_rc(cmd, timeout=5):
    """Exécute une commande, retourne (code, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", "command not found"
    except Exception as e:
        return -1, "", str(e)


# ── CPU / Température ─────────────────────────────────────────────

def cpu_temp():
    """Température CPU en °C (None si indisponible)."""
    for path in ["/sys/class/thermal/thermal_zone0/temp",
                  "/sys/devices/platform/soc/soc:firmware/get_throttled"]:
        try:
            raw = Path(path).read_text().strip()
            return round(int(raw) / 1000, 1)
        except Exception:
            continue
    # Fallback vcgencmd
    out = _run(["vcgencmd", "measure_temp"])
    if out:
        try:
            return float(out.replace("temp=", "").replace("'C", ""))
        except ValueError:
            pass
    return None

def cpu_freq():
    """Fréquence CPU en MHz."""
    out = _run(["vcgencmd", "measure_clock", "arm"])
    if out:
        try:
            return round(int(out.split("=")[1]) / 1_000_000, 1)
        except Exception:
            pass
    # Fallback /proc
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if "BogoMIPS" in line:
                return float(line.split(":")[1].strip())
    except Exception:
        pass
    return None

def cpu_usage():
    """Charge CPU en pourcentage (moyenne simplifiée)."""
    try:
        lines = Path("/proc/stat").read_text().splitlines()
        parts = lines[0].split()
        total = sum(int(x) for x in parts[1:])
        idle = int(parts[4])
        return round((1 - idle / total) * 100, 1)
    except Exception:
        return None

def cpu_throttled():
    """Vérifie si le CPU est en throttling (sous-voltage / surchauffe)."""
    out = _run(["vcgencmd", "get_throttled"])
    if out and "0x" in out:
        try:
            val = int(out.split("=")[1], 16)
            flags = []
            if val & 0x1: flags.append("under-voltage")
            if val & 0x2: flags.append("arm-frequency-capped")
            if val & 0x4: flags.append("currently-throttled")
            if val & 0x8: flags.append("soft-temperature-limit-active")
            if val & 0x10000: flags.append("under-voltage-occurred")
            if val & 0x20000: flags.append("arm-frequency-capped-occurred")
            if val & 0x40000: flags.append("throttling-occurred")
            if val & 0x80000: flags.append("soft-temp-limit-occurred")
            return {"throttled_now": bool(val & 0xF), "flags": flags}
        except Exception:
            pass
    return None


# ── Mémoire ────────────────────────────────────────────────────────

def memory():
    """RAM totale, utilisée, libre en MB."""
    try:
        lines = Path("/proc/meminfo").read_text().splitlines()
        info = {}
        for l in lines:
            parts = l.split()
            if parts[0].rstrip(":") in ("MemTotal", "MemAvailable", "MemFree"):
                info[parts[0].rstrip(":")] = int(parts[1]) // 1024
        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)
        free = info.get("MemFree", 0)
        return {
            "total_mb": total,
            "available_mb": available,
            "free_mb": free,
            "used_pct": round((total - available) / total * 100, 1) if total else None,
        }
    except Exception:
        return None


# ── Disque ─────────────────────────────────────────────────────────

def disk():
    """Espace disque de la partition principale."""
    try:
        stat = os.statvfs("/")
        total = stat.f_frsize * stat.f_blocks // (1024 * 1024)
        free = stat.f_frsize * stat.f_bfree // (1024 * 1024)
        available = stat.f_frsize * stat.f_bavail // (1024 * 1024)
        used = total - free
        return {
            "total_mb": total,
            "used_mb": used,
            "available_mb": available,
            "used_pct": round(used / total * 100, 1) if total else None,
        }
    except Exception:
        # Fallback df
        rc, out, _ = _run_rc(["df", "-m", "/"])
        if rc == 0 and out:
            lines = out.splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 4:
                    return {
                        "total_mb": int(parts[1]),
                        "used_mb": int(parts[2]),
                        "available_mb": int(parts[3]),
                        "used_pct": float(parts[4].rstrip("%")),
                    }
        return None

def disk_audio_cache():
    """Taille du cache audio en MB."""
    audio_dir = PROJECT_DIR / "data" / "audio"
    if not audio_dir.exists():
        return 0
    total = sum(f.stat().st_size for f in audio_dir.iterdir() if f.is_file())
    return round(total / (1024 * 1024), 1)


# ── Uptime ─────────────────────────────────────────────────────────

def uptime():
    """Temps depuis le démarrage en secondes (et format lisible)."""
    try:
        raw = Path("/proc/uptime").read_text().strip()
        secs = float(raw.split()[0])
        h, m = divmod(int(secs), 3600)
        m, s = divmod(m, 60)
        return {"seconds": round(secs, 0), "human": f"{h}h {m:02d}m {s:02d}s"}
    except Exception:
        return None


# ── Réseau ─────────────────────────────────────────────────────────

def network():
    """Adresses IP et état réseau."""
    info = {"interfaces": []}
    try:
        rc, out, _ = _run_rc(["ip", "-4", "addr", "show"])
        if rc == 0:
            current_iface = None
            for line in out.splitlines():
                line = line.strip()
                if line.startswith(("eth", "wlan", "lo")):
                    current_iface = line.split(":")[1].strip() if ":" in line else line.split()[1].rstrip(":")
                if "inet " in line and current_iface and current_iface != "lo":
                    ip = line.split()[1]
                    info["interfaces"].append({"name": current_iface, "ip": ip})
    except Exception:
        pass
    # Ping test
    rc, _, _ = _run_rc(["ping", "-c1", "-W2", "8.8.8.8"])
    info["internet"] = rc == 0
    return info


# ── Services ───────────────────────────────────────────────────────

def flask_health():
    """Vérifie si le serveur Flask répond."""
    rc, out, _ = _run_rc(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                           "http://127.0.0.1:5000/"])
    if rc == 0 and out == "200":
        return {"running": True, "port": 5000, "http": int(out)}
    return {"running": False, "port": 5000, "http": None}


# ── I2C / PCA9685 ─────────────────────────────────────────────────

def i2c_devices():
    """Liste les périphériques I2C détectés via i2cdetect."""
    rc, out, _ = _run_rc(["i2cdetect", "-y", "1"])
    if rc != 0:
        return None
    devices = []
    for line in out.splitlines()[1:]:  # skip header
        parts = line.split()
        for p in parts[1:]:
            if p not in ("--", "UU"):
                try:
                    addr = int(p, 16)
                    hex_str = f"0x{p}"
                    names = {0x5f: "PCA9685 (PWM/Servo)"}
                    devices.append({"addr": hex_str, "id": addr,
                                    "name": names.get(addr, "inconnu")})
                except ValueError:
                    pass
    return devices

def pca9685_health():
    """Vérifie si le PCA9685 répond sur l'adresse 0x5f."""
    from .checks import check_pca9685
    return check_pca9685()


# ── Caméra ─────────────────────────────────────────────────────────

def camera_available():
    """Vérifie si une caméra est détectée."""
    for cmd in [["libcamera-still", "--list-cameras"],
                ["v4l2-ctl", "--list-devices"]]:
        rc, out, _ = _run_rc(cmd, timeout=3)
        if rc == 0 and out:
            return {"detected": True, "output": out[:200]}
    return {"detected": False, "output": None}


# ── Capture complète ───────────────────────────────────────────────

def capture_state():
    """Retourne un dict complet de l'état actuel du robot."""
    return {
        "timestamp": time.time(),
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": {
            "temp_c": cpu_temp(),
            "freq_mhz": cpu_freq(),
            "usage_pct": cpu_usage(),
            "throttled": cpu_throttled(),
        },
        "memory": memory(),
        "disk": disk(),
        "uptime": uptime(),
        "network": network(),
        "services": {"flask": flask_health()},
        "hardware": {
            "i2c": i2c_devices(),
            "pca9685": pca9685_health(),
            "camera": camera_available(),
        },
    }
