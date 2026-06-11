#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnostic I2C pour le PiCar-Pro.
Vérifie la présence des composants sur le bus I2C.

Usage:
    python Tools/i2c_diagnostic.py
"""

import os
import sys
import subprocess

# Bus I2C principal sur Raspberry Pi
I2C_BUS = 1

# Composants attendus sur le PiCar-Pro
EXPECTED_DEVICES = {
    0x40: ("PCA9685", "PWM Motor/Servo Controller"),
    0x48: ("ADS7830", "ADC Battery Voltage"),
    0x3c: ("SSD1306", "OLED Display"),
    0x70: ("I2C Hub", "I2C Multiplexer/Switch"),
}

# Couleurs terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check_i2c_enabled():
    """Vérifie si l'I2C est activé sur le système."""
    print(f"\n{BOLD}[1] Vérification I2C systeme{RESET}")
    print("-" * 40)

    # Vérifier le module i2c-dev
    try:
        result = subprocess.run(
            ["lsmod"], capture_output=True, text=True, timeout=5
        )
        if "i2c_dev" in result.stdout or "i2c_bcm" in result.stdout:
            print(f"  {GREEN}OK{RESET} Module I2C charge")
        else:
            print(f"  {YELLOW}WARN{RESET} Module I2C non detecte dans lsmod")
    except Exception:
        print(f"  {YELLOW}WARN{RESET} Impossible de verifier lsmod")

    # Vérifier /dev/i2c-*
    i2c_devs = [d for d in os.listdir("/dev/") if d.startswith("i2c-")]
    if i2c_devs:
        print(f"  {GREEN}OK{RESET} Bus I2C trouves: {', '.join(i2c_devs)}")
    else:
        print(f"  {RED}ERREUR{RESET} Aucun bus I2C trouve!")
        print(f"  → Active I2C: sudo raspi-config → Interface Options → I2C")
        return False

    # Vérifier le bus principal
    i2c_path = f"/dev/i2c-{I2C_BUS}"
    if os.path.exists(i2c_path):
        print(f"  {GREEN}OK{RESET} Bus principal {i2c_path} accessible")
        return True
    else:
        print(f"  {RED}ERREUR{RESET} Bus {i2c_path} introuvable")
        return False


def scan_i2c_bus(bus_num=I2C_BUS):
    """Scanne le bus I2C et retourne la liste des adresses trouvees."""
    print(f"\n{BOLD}[2] Scan du bus I2C-{bus_num}{RESET}")
    print("-" * 40)

    try:
        import smbus
        bus = smbus.SMBus(bus_num)
    except ImportError:
        print(f"  {RED}ERREUR{RESET} Module smbus non disponible")
        return []
    except OSError as e:
        print(f"  {RED}ERREUR{RESET} Impossible d'acceder au bus I2C: {e}")
        return []

    found = []
    for addr in range(0x03, 0x78):
        try:
            bus.read_byte(addr)
            found.append(addr)
        except OSError:
            pass  # Aucun peripherique a cette adresse

    bus.close()
    return found


def display_results(found_addresses):
    """Affiche les peripheriques trouves et manquants."""
    print(f"\n{BOLD}[3] Resultats{RESET}")
    print("-" * 40)

    all_ok = True

    for addr, (name, desc) in sorted(EXPECTED_DEVICES.items()):
        if addr in found_addresses:
            print(f"  {GREEN}OK   {RESET}0x{addr:02X}  {name:12s}  ({desc})")
        else:
            print(f"  {RED}MANQUE{RESET} 0x{addr:02X}  {name:12s}  ({desc})")
            all_ok = False

    # Afficher les peripheriques non reconnus
    unknown = [a for a in found_addresses if a not in EXPECTED_DEVICES]
    if unknown:
        print(f"\n  {YELLOW}Non reconnus:{RESET}")
        for addr in unknown:
            print(f"    0x{addr:02X}  (peripherique inconnu)")

    return all_ok


def diagnose_problems(all_ok, found_addresses):
    """Donne des conseils de depannage."""
    print(f"\n{BOLD}[4] Diagnostic{RESET}")
    print("-" * 40)

    pca9685_found = 0x40 in found_addresses

    if all_ok:
        print(f"  {GREEN}{BOLD}TOUT VA BIEN !{RESET} Tous les composants sont detectes.")
        print(f"\n  Si le robot ne bouge toujours pas :")
        print(f"    1. Vérifie l'alimentation des moteurs (batterie 12V)")
        print(f"    2. Vérifie les fusibles sur la carte motor shield")
        print(f"    3. Teste les moteurs individuellement")
        return

    print(f"  {RED}Probleme detecte : au moins un composant est manquant.{RESET}\n")

    if not pca9685_found:
        print(f"  {BOLD}PCA9685 MANQUANT !{RESET} (adresse 0x40)")
        print(f"  → C'est la raison pour laquelle le robot ne bouge pas.\n")
        print(f"  Causes possibles :")
        print(f"    🪫  {BOLD}Batterie eteinte ou dechargee{RESET}")
        print(f"        Le PCA9685 est alimente par la batterie 12V,")
        print(f"        pas par le GPIO du Raspberry Pi.")
        print(f"        → Allume le robot (switch ON)")
        print(f"        → Recharge la batterie si necessaire\n")
        print(f"    🔌  {BOLD}Carte motor shield mal enfichée{RESET}")
        print(f"        → Deconnecte le Raspberry Pi de l'alimentation")
        print(f"        → Re-enfice correctement la carte sur le GPIO\n")
        print(f"    🧪  {BOLD}Developpement sans le robot{RESET}")
        print(f"        → Utilise l'option --simulate avec main.py")
        print(f"        → python main.py --simulate\n")

    # Verifier si le probleme est generalise
    if len(found_addresses) <= 1:
        print(f"  {YELLOW}Note:{RESET} Seulement {len(found_addresses)} peripherique(s) trouve(s)")
        print(f"  L'I2C semble fonctionner mais le robot n'est pas alimente")
        print(f"  ou la carte principale n'est pas connectee.")


def main():
    print(f"\n{CYAN}{BOLD}=== Diagnostic I2C - PiCar-Pro ==={RESET}")
    print(f"Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Plateforme: {sys.platform}")

    # Vérifier les permissions
    if os.geteuid() != 0:
        print(f"\n  {YELLOW}ATTENTION:{RESET} Les permissions root peuvent etre necessaires")
        print(f"  pour acceder au bus I2C.")
        print(f"  → Lance avec: sudo python Tools/i2c_diagnostic.py\n")

    # Étape 1: Vérifier que l'I2C est activé
    i2c_ok = check_i2c_enabled()
    if not i2c_ok:
        print(f"\n{RED}L'I2C n'est pas accessible. Active-le avec raspi-config.{RESET}")
        sys.exit(1)

    # Étape 2: Scanner le bus
    found = scan_i2c_bus()
    if not found:
        print(f"  {YELLOW}Aucun peripherique trouve sur le bus I2C{RESET}")
        print(f"  → Verifie que le robot est allume et correctement branche")

    # Étape 3: Afficher les résultats
    all_ok = display_results(found)

    # Étape 4: Diagnostic
    diagnose_problems(all_ok, found)

    print(f"\n{CYAN}{'='*50}{RESET}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
