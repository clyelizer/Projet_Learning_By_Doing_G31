#!/bin/bash
# ============================================================
# Configuration Pi — mDNS + Auto-démarrage du dashboard
# ============================================================
# À exécuter UNE FOIS sur le Raspberry Pi
#
# Usage:
#   ssh kit13@<IP_DU_PI>
#   bash setup_pi.sh
# ============================================================

set -e

echo "========================================"
echo "  Configuration AgroScan — IP & mDNS"
echo "========================================"

# ── 1. Installer Avahi (mDNS / Zeroconf) ────────────────
echo ""
echo "[1/4] Installation d'Avahi (mDNS)..."
sudo apt update -qq
sudo apt install -y -qq avahi-daemon avahi-utils

# ── 2. Créer le service Avahi pour AgroScan ─────────────
echo ""
echo "[2/4] Configuration du service mDNS..."
sudo tee /etc/avahi/services/agroscan.service > /dev/null << 'EOF'
<?xml version="1.0" standalone="no"?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name>AgroScan Dashboard</name>
  <service>
    <type>_http._tcp</type>
    <port>5000</port>
  </service>
</service-group>
EOF

# ── 3. Créer le service systemd pour le dashboard ───────
echo ""
echo "[3/4] Création du service systemd..."
sudo tee /etc/systemd/system/agroscan-web.service > /dev/null << 'EOF'
[Unit]
Description=AgroScan Dashboard (Flask)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=kit13
WorkingDirectory=/home/kit13/Bureau/n
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/python3 /home/kit13/Bureau/n/src/web/app.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# ── 4. Activer les services ─────────────────────────────
echo ""
echo "[4/4] Activation des services..."
sudo systemctl daemon-reload
sudo systemctl enable avahi-daemon
sudo systemctl enable agroscan-web.service

echo ""
echo "========================================"
echo "  ✅ Configuration terminée !"
echo "========================================"
echo ""
echo "Redémarre le Pi pour tester :"
echo "  sudo reboot"
echo ""
echo "Après redémarrage, attends 20s puis :"
echo "  http://agroscan.local:5000"
echo "  (ou l'IP affichée dans la console)"
echo "========================================"
