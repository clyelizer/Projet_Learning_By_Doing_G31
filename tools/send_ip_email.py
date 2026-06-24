#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envoie l'IP du robot + lien dashboard par email au démarrage.
Utilise la config dans config/email_config.json et le mot de passe
dans .env (EMAIL_PASSWORD).

Usage :
  python3 tools/send_ip_email.py

Retourne 0 si envoyé, 1 si pas configuré, 2 si erreur.
"""

import json
import os
import socket
import smtplib
import sys
import pathlib
from email.mime.text import MIMEText

# Chemins
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PROJECT_DIR / 'config' / 'email_config.json'
ENV_FILE = PROJECT_DIR / '.env'


def get_local_ip():
    """Récupère l'IP locale non-loopback."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def load_env_password():
    """Lit EMAIL_PASSWORD depuis .env."""
    if not ENV_FILE.exists():
        return None
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith('EMAIL_PASSWORD='):
            val = line.split('=', 1)[1].strip().strip('"').strip("'")
            return val if val else None
    return None


def send_ip_email():
    """Envoie l'email avec l'IP."""
    # Charger config
    if not CONFIG_FILE.exists():
        print("email_config.json introuvable", file=sys.stderr)
        return 1

    config = json.loads(CONFIG_FILE.read_text())
    recipient = config.get('recipient_email', '').strip()
    smtp_user = config.get('smtp_user', '').strip()
    smtp_server = config.get('smtp_server', 'smtp.gmail.com')
    smtp_port = config.get('smtp_port', 587)
    use_tls = config.get('use_tls', True)

    if not recipient or not smtp_user:
        print("Email non configuré (recipient ou smtp_user vide)", file=sys.stderr)
        return 1

    smtp_pass = load_env_password()
    if not smtp_pass:
        print("EMAIL_PASSWORD non défini dans .env", file=sys.stderr)
        return 1

    # IP + hostname
    ip = get_local_ip()
    hostname = socket.gethostname()
    link = f"http://{ip}:5000"

    sujet = f"🌱 AgroScan connecté — {hostname}"
    if '--test' in sys.argv:
        sujet = f"🧪 Test AgroScan — {hostname} ({ip})"
    corps = f"""Bonjour,

Le robot AgroScan est en ligne.

  Adresse : {link}
  IP      : {ip}
  Hostname : {hostname}.local

Tu peux aussi essayer : http://{hostname}.local:5000

🌾 Bonne mission !
"""

    msg = MIMEText(corps, _charset='utf-8')
    msg['Subject'] = sujet
    msg['From'] = smtp_user
    msg['To'] = recipient

    try:
        if smtp_port == 465:
            # SSL direct
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as s:
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
        else:
            # STARTTLS
            with smtplib.SMTP(smtp_server, smtp_port) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
        print(f"Email envoyé à {recipient} — {link}")
        return 0
    except Exception as e:
        print(f"Erreur envoi email : {e}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(send_ip_email())
