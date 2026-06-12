---
name: rs485-modbus-sensor-troubleshoot
description: Systematic diagnostic procedure for non-responsive Modbus RS485 sensor over UART on Raspberry Pi / Robot HAT
source: auto-skill
extracted_at: '2026-06-12T03:42:25.282Z'
---

# Troubleshooting a non-responsive Modbus RS485 sensor (UART / Raspberry Pi)

When a Modbus RS485 soil/NPK sensor connected via serial UART returns no data, use this layered diagnostic approach. Each layer narrows the problem.

## Layer 1 — Verify the software is valid

1. **Check Python syntax** — scripts often get corrupted when copied through USB drives or text editors
   ```bash
   python3 -m py_compile test_capteur.py && echo "Syntaxe OK"
   ```
2. **Run the script with a foreground timeout** to see initial output without blocking the shell:
   ```bash
   timeout 10 python3 -u test_capteur.py 2>&1
   ```
   The `-u` flag forces unbuffered output so you see prints immediately.

## Layer 2 — Verify the Modbus request is correct

Many NPK/soil sensors use Modbus RTU (9600 8N1). Validate the CRC of the request frame:

```python
def modbus_crc(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

# Example: read 4 holding registers from slave 0x01, starting at 0x0000
data = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x04])
crc = modbus_crc(data)
print(f"CRC: {crc:04X}")  # Must match the last 2 bytes of the request
```

Common request pattern for a 4-parameter soil sensor (humidity, temp, EC, pH):
- `0x01 0x03 0x00 0x00 0x00 0x04 0x44 0x09`

## Layer 3 — Verify serial port accessibility

Check the port exists and the user has permissions:

```bash
ls -la /dev/ttyS0 /dev/ttyAMA0 /dev/ttyUSB* /dev/ttyACM*
groups                    # Must include 'dialout' for serial access
```

On Raspberry Pi, common UART devices:
- `/dev/ttyS0` — mini UART (GPIO 14/15), may have unstable baud rate if core_freq changes
- `/dev/ttyAMA0` — PL011 UART (often used by Bluetooth)
- `/dev/serial0` — symlink to the primary UART (often → ttyS0)

## Layer 4 — Test connectivity: scan baudrates and ports

The sensor might use a non-standard baudrate or be on a different UART. Test systematically:

```python
import serial, time

request = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x04, 0x44, 0x09])

for port in ['/dev/ttyS0', '/dev/ttyAMA0']:
    for baud in [9600, 4800, 19200, 115200, 38400]:
        try:
            ser = serial.Serial(port, baud, timeout=1)
            ser.write(request)
            time.sleep(0.3)
            r = ser.read(20)
            status = r.hex() if r else "(no response)"
            print(f"{port} @ {baud}: {status}")
            ser.close()
        except Exception as e:
            print(f"{port} @ {baud}: ERROR {e}")
```

## Layer 5 — Ask about the physical wiring (often the root cause)

If no response on any baudrate or port, the issue is likely **physical**. Ask the user:

1. **Which sensor model?** (e.g., JXCT, generic Chinese soil NPK sensor)
2. **Is there an RS485 transceiver module** (like MAX485) between the sensor and the Raspberry Pi/HAT? (Most NPK sensors are RS485 differential, not direct UART TTL — they need a converter.)
3. **Which pins are the sensor wires connected to?** On a Raspberry Pi 40-pin header:
   - **Wrong**: Pin 5 (SCL/GPIO3) or Pin 7 (GPIO4) — these are NOT UART
   - **Correct** for UART: Pin 8 (GPIO14/TXD) and Pin 10 (GPIO15/RXD)
   - On Robot HAT V3.2: servo-style 3-pin connectors (GND, +5V, Signal) are for servos/PWM, not UART
4. **How is the sensor powered?** Many soil sensors need 5-24V external power, not just the UART signal lines.

## Typical root causes found in the field

| Symptom | Likely cause |
|---|---|
| No response on any baudrate | Wrong physical pins (e.g., connected to SCL/GPIO4 instead of TXD/RXD) |
| No response on one port, works on another | Wrong UART selected; Bluetooth may be blocking ttyAMA0 |
| Garbage / corrupted response | Baudrate mismatch or missing GND common |
| Response on one baudrate only | Sensor configured to non-standard baudrate |
| No response despite correct wiring | Missing RS485 transceiver; sensor is RS485 but connected directly to TTL UART |
