#include <SoftwareSerial.h>
#include <ModbusMaster.h>

#define RX_PIN 8
#define TX_PIN 9
#define CONTROL_PIN 7

SoftwareSerial mySerial(RX_PIN, TX_PIN);
ModbusMaster node;

void preTransmission() {
  digitalWrite(CONTROL_PIN, HIGH);
}

void postTransmission() {
  digitalWrite(CONTROL_PIN, LOW);
}

void setup() {
  pinMode(CONTROL_PIN, OUTPUT);
  digitalWrite(CONTROL_PIN, LOW);

  Serial.begin(9600);
  mySerial.begin(4800);

  node.begin(1, mySerial);
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  Serial.println(F("--- RAW REGISTER DUMP ---"));
  Serial.println(F("Humidity_raw | Humidity_scaled | Temp_raw | Temp_scaled | EC_raw | EC_scaled | pH_raw | pH_scaled"));
}

void loop() {
  uint8_t result = node.readHoldingRegisters(0x0000, 4);

  if (result == node.ku8MBSuccess) {
    uint16_t raw_hum = node.getResponseBuffer(0);
    uint16_t raw_temp = node.getResponseBuffer(1);
    uint16_t raw_ec   = node.getResponseBuffer(2);
    uint16_t raw_ph   = node.getResponseBuffer(3);

    // Affichage avec precision maximale pour voir s'il y a des decimales cachees
    Serial.print(raw_hum); Serial.print(" | ");
    Serial.print(raw_hum / 10.0, 4); Serial.print(" | ");
    Serial.print(raw_temp); Serial.print(" | ");
    Serial.print(raw_temp / 10.0, 4); Serial.print(" | ");
    Serial.print(raw_ec); Serial.print(" | ");
    Serial.print(raw_ec / 10.0, 4); Serial.print(" | ");
    Serial.print(raw_ph); Serial.print(" | ");
    Serial.println(raw_ph / 10.0, 4);
  } else {
    Serial.print(F("Erreur Modbus: 0x"));
    Serial.println(result, HEX);
  }

  delay(2000);
}
