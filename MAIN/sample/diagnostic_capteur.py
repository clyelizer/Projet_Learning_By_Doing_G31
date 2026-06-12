#!/usr/bin/env python3
"""Diagnostic rapide : envoie une requête et affiche la réponse brute en hexa."""
import serial
import time

ser = serial.Serial(
    port='/dev/ttyS0',
    baudrate=9600,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=2
)

requete = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x04, 0x44, 0x09])

print("Envoi :", requete.hex())
ser.write(requete)
time.sleep(0.5)

reponse = ser.read(20)
print("Réponse brute :", reponse.hex() if reponse else "(vide)")
print("Longueur :", len(reponse), "octets")

if reponse:
    print("\nDécodage :")
    print(f"  Adresse esclave : {reponse[0]}")
    print(f"  Fonction        : {reponse[1]}")
    print(f"  Nb octets donnés: {reponse[2]}")
    if len(reponse) >= 11:
        data = list(reponse)
        print(f"  Humidité    : {(data[3] << 8 | data[4]) / 10.0} %")
        print(f"  Température : {(data[5] << 8 | data[6]) / 10.0} °C")
        print(f"  EC          : {(data[7] << 8 | data[8]) / 10.0} mS/cm")
        print(f"  pH          : {(data[9] << 8 | data[10]) / 10.0}")

ser.close()
