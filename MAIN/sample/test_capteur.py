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

print("Test capteur démarré...")

while True:
    ser.write(requete)
    time.sleep(0.5)
    reponse = ser.read(20)

    if len(reponse) >= 11:
        data = list(reponse)
        humidite = (data[3] << 8 | data[4]) / 10.0
        temperature = (data[5] << 8 | data[6]) / 10.0
        ec = (data[7] << 8 | data[8]) / 10.0
        ph = (data[9] << 8 | data[10]) / 10.0

        print(f"Humidit\u00e9 : {humidite} %")
        print(f"Temp\u00e9rature : {temperature} \u00b0C")
        print(f"EC : {ec} mS/cm")
        print(f"pH : {ph}")
        print("\u2500" * 17)
    else:
        print("Pas de r\u00e9ponse")

    time.sleep(3)
