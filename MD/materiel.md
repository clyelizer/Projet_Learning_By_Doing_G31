# Matériel et composants — PiCar-Pro V2

> Guide complet des capteurs, servomoteurs et électronique du robot.

---

## Vue d'ensemble du système

![PiCar-Pro V2 - Vue d'ensemble](images/picar-pro-v2-overview.jpg)

Le **Adeept PiCar-Pro V2** est un robot mobile autonome basé sur une architecture **2WD** (2 roues motrices arrière) avec direction servo avant. C'est un système mécatronique complet alliant :

- **Capteurs** — percevoir l'environnement
- **Actionneurs** — agir sur le monde physique
- **Unité de contrôle** — traiter l'information et décider

### Architecture générale

```
    ┌──────────┐     commandes     ┌─────────────┐
    │ Contrôle │ ────────────────► │ Actionneurs  │
    │  (RPi)   │                   │ (moteurs,    │
    └──────────┘                   │  servos)     │
          ▲                        └──────┬───────┘
          │                               │
          └───────────────────────────────┘
              capteurs (ultrason,
              suiveur de ligne, etc.)
```

---

## 1. Unité de contrôle : Raspberry Pi

![Raspberry Pi](images/raspberry-pi.jpg)

Le **Raspberry Pi** est un mini-ordinateur qui pilote l'ensemble du système. Modèles compatibles :

- Raspberry Pi 5 (recommandé — plus rapide)
- Raspberry Pi 4B (excellent rapport qualité/prix)
- Raspberry Pi 3B+ (fonctionne, mais plus lent)

### Spécifications

| Paramètre | Valeur |
|-----------|--------|
| **Processeur** | ARM Cortex (1.5 à 3 GHz selon modèle) |
| **RAM** | 2 à 8 GB |
| **Stockage** | microSD (32 GB minimum) |
| **GPIO** | 40 broches (digital I/O) |
| **Ports USB** | 2–4 selon modèle |
| **Alimentación** | 5V USB-C |
| **Connectivité** | WiFi + Bluetooth (sauf Pi 3B) |

### Installation du système d'exploitation

```bash
# Sur la microSD via Raspberry Pi Imager
# Installer : Raspberry Pi OS (32-bit Lite)
# Configurer WiFi + SSH directement dans l'imager

# Première démarrage
ssh pi@<IP_ROBOT>
sudo raspi-config

# Activer I2C (bus pour le PCA9685)
# → Interface Options → I2C → Yes
# → Reboot
```

---

## 2. Carte d'extension : Robot HAT V3.2

![Robot HAT V3.2](images/robot-hat-v3.2.jpg)

Le **Robot HAT V3.2** se connecte directement sur les 40 GPIO du Raspberry Pi. C'est le cerveau électronique du robot.

### Composants intégrés

| Composant | Rôle | Détails |
|-----------|------|---------|
| **PCA9685** | Contrôleur PWM 16 canaux | Pilote 16 servos/moteurs simultanément via I2C |
| **Ponts en H** | Commutation moteurs DC | Contrôle direction + vitesse des moteurs |
| **Connecteurs servo** | Sorties CH0–CH15 | 16 canaux PWM (3 broches : GND, +5V, Signal) |
| **Connecteur ultrason** | X9 | Branchement du capteur HC-SR04 |
| **Connecteur suivi de ligne** | X8 | 3 capteurs IR (S1, S2, S3) |
| **Buzzer intégré** | Signal sonore | Alertes programmables |
| **Récepteur IR** | Télécommande | Recevoir commands infrarouge |
| **LED1, LED2, LED3** | Signalisation visuelle | 3 LEDs programmables |

### Brochage GPIO utilisé

| GPIO | Composant | Fonction |
|------|-----------|----------|
| GPIO9 | LED1 | Sortie digitale |
| GPIO25 | LED2 | Sortie digitale |
| GPIO11 | LED3 | Sortie digitale |
| GPIO18 | Buzzer | PWM / Tonale |
| GPIO23 | Ultrason | Trigger (entrée) |
| GPIO24 | Ultrason | Echo (sortie) |
| GPIO17 | Capteur S1 | Entrée digitale (droite) |
| GPIO27 | Capteur S2 | Entrée digitale (milieu) |
| GPIO22 | Capteur S3 | Entrée digitale (gauche) |
| SCL / SDA | PCA9685 | Bus I2C (adresse 0x5f) |

### Vérifier la connexion I2C

```bash
# Installer l'outil de diagnostic
sudo apt install i2c-tools -y

# Vérifier la présence du PCA9685
i2cdetect -y 1

# Sortie attendue (la case 5f contient un numéro) :
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 50: -- -- -- -- -- -- -- -- -- -- 5f -- -- -- -- --
# 60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 70: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
```

---

## 3. Contrôleur PWM : PCA9685

![PCA9685 Détail](images/pca9685-detail.jpg)

Le **PCA9685** est un circuit intégré piloté en I2C générant **16 signaux PWM indépendants** avec une résolution de 12 bits (4096 pas).

### Caractéristiques

- **Adresse I2C** : 0x5f (configurable)
- **Tension d'alimentation** : 5V DC
- **Fréquence PWM** : jusqu'à 1.6 kHz (50 Hz pour servos)
- **Résolution** : 12 bits (0–4095)
- **Canaux** : 16 (CH0–CH15)

### Distribution des canaux sur PiCar-Pro

| Canaux | Usage |
|--------|-------|
| **CH0** | Servo direction (roues avant) |
| **CH1** | Servo ultrason (orientation du capteur) |
| **CH2** | Servo bras — Coude (mouvement vertical) |
| **CH3** | Servo bras — Épaule |
| **CH4** | Servo pince (ouverture/fermeture) |
| **CH5–CH7** | Réservés (extensions futures) |
| **CH8–CH11** | Réservés |
| **CH12–CH13** | Moteur 2 (roues arrière droite) |
| **CH14–CH15** | Moteur 1 (roues arrière gauche) |

### Signal PWM pour servos

Un servo standard reçoit un signal PWM à **50 Hz** (période 20 ms) :

```
     ┌──┐
     │  │ largeur d'impulsion
─────┤  ├─────────────────────── (répété tous les 20 ms)
     │  │
     └──┘
     
   500 µs  →  0°
  1500 µs  → 90°
  2500 µs  → 180°
```

---

## 4. Capteurs

### 4.1 Capteur ultrason HC-SR04

![HC-SR04 Ultrason](images/hc-sr04-ultrasonic.jpg)

Le **HC-SR04** mesure les distances par **écholocation ultrasonique** (principe du sonar).

#### Principe de fonctionnement

1. Le Raspberry Pi envoie une **impulsion de 10 µs** sur TRIGGER
2. Le capteur émet une **salve de 8 impulsions à 40 kHz**
3. Les ondes se propagent dans l'air à ~340 m/s
4. Elles sont réfléchies par les obstacles
5. Le capteur détecte l'écho et émet un signal sur ECHO dont la durée est proportionnelle à la distance

#### Calcul de la distance

La relation entre le temps d'aller-retour $t$ et la distance $d$ :

$$d = \frac{340 \times t}{2} = \frac{t}{58} \text{ (en cm)}$$

#### Spécifications

| Paramètre | Valeur |
|-----------|--------|
| Tension d'alimentation | 5V DC |
| Consommation | 15 mA |
| **Portée minimale** | 2 cm |
| **Portée maximale** | 4 m |
| **Angle de détection** | ~15° |
| Fréquence ultrason | 40 kHz |
| Précision | ±3% |

#### Brochage

| Pin | Raspberry Pi | Fonction |
|-----|--------------|----------|
| VCC | 5V | Alimentation |
| GND | GND | Masse |
| TRIG | GPIO23 | Trigger (entrée RPi) |
| ECHO | GPIO24 | Echo (sortie du capteur) |

> **Attention :** Le HC-SR04 fonctionne en 5V. Le HAT gère automatiquement l'adaptation de niveau logique (Echo 5V → GPIO 3.3V compatible).

#### Code de mesure

```python
import time
from gpiozero import MCP3008
import board
import busio
import adafruit_ads1x15.analog_in as AnalogIn
from adafruit_ads1x15.analog_in import AnalogIn

TRIG = 23
ECHO = 24

def mesurer_distance():
    """Retourne la distance en cm."""
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)  # 10 µs
    GPIO.output(TRIG, GPIO.LOW)
    
    while GPIO.input(ECHO) == 0:
        debut = time.time()
    while GPIO.input(ECHO) == 1:
        fin = time.time()
    
    duree = fin - debut
    distance_cm = duree * 17000  # 340 m/s / 2
    return distance_cm
```

### 4.2 Capteurs de suivi de ligne (IR)

![Capteurs IR Suivi de ligne](images/ir-line-sensors.jpg)

Le PiCar-Pro embarque un **module à 3 capteurs infrarouges** alignés transversalement pour suivre une ligne noire au sol.

#### Principe

1. **LED infrarouge** émet un faisceau vers le sol
2. **Surface blanche** → forte réflexion → phototransistor reçoit beaucoup de signal
3. **Surface noire** → absorption → phototransistor reçoit peu de signal
4. Résultat : **0 = noir**, **1 = blanc**

#### Positionnement des 3 capteurs

```
     ┌──────────────────────────┐
     │ Capteur gauche (GPIO22)  │ ← S3
     │ Capteur milieu (GPIO27)  │ ← S2
     │ Capteur droit  (GPIO17)  │ ← S1
     └──────────────────────────┘
         (vue de dessus du robot)
```

#### Brochage

| Capteur | GPIO | Position |
|---------|------|----------|
| S1 | GPIO17 | Droite |
| S2 | GPIO27 | Milieu |
| S3 | GPIO22 | Gauche |

#### Logique de décision

| S3 (G) | S2 (M) | S1 (D) | Interprétation | Action |
|:---:|:---:|:---:|---|---|
| 0 | 0 | 0 | Aucune ligne | Chercher |
| 0 | 0 | 1 | Ligne à droite | Tourner à droite |
| 0 | 1 | 0 | Ligne au centre | Avancer droit |
| 0 | 1 | 1 | Centre + droite | Tourner à droite |
| 1 | 0 | 0 | Ligne à gauche | Tourner à gauche |
| 1 | 0 | 1 | Gauche + droite (fourche) | Tout droit |
| 1 | 1 | 0 | Gauche + centre | Tourner à gauche |
| 1 | 1 | 1 | Ligne partout | Tout droit |

---

### 4.3 Caméra USB

![Caméra USB](images/usb-camera.jpg)

La **caméra USB** permet la vision par ordinateur, le suivi de couleur et la transmission vidéo en temps réel.

#### Caractéristiques

- Résolution : 1280×960 (ou mieux)
- Format : USB 2.0
- FPS : 30 fps en 640×480
- Microphone intégré : reconnaissance vocale possible

#### Utilisation

```python
import cv2

cap = cv2.VideoCapture(0)  # 0 = première caméra USB

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Traitement d'image
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    cv2.imshow('Camera', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 5. Actionneurs

### 5.1 Servomoteurs

![Servomoteurs variés](images/servos-variety.jpg)

Un **servomoteur** est un actionneur capable de **positionner son axe à un angle précis** (généralement 0°–180°). Contrairement à un moteur qui tourne continûment, un servo **maintient sa position** même sans signal.

#### Les 5 servos du PiCar-Pro

| Servo | Canal | Angle | Fonction |
|-------|-------|-------|----------|
| **A** | CH0 | 45°–128° | Direction roues avant |
| **B** | CH1 | 0°–180° | Orientation module ultrason |
| **C** | CH2 | Variable | Coude du bras (vertical) |
| **D** | CH3 | Variable | Épaule du bras |
| **E** | CH4 | 0°–180° | Pince (ouverture/fermeture) |

#### Angles de contrôle du servo de direction (CH0)

```
    Vg
45°  ╱  95°   128°  Vd
    ╱    │      ╲
  ┌─────┼────────┐
  │     │ AVANT  │
  │     │ (droit)│
  └─────┴────────┘
  Gauche Centre  Droite
```

| Angle | Direction |
|-------|-----------|
| **45°** | Virage à gauche maximal |
| **85°–90°** | Légèrement à gauche |
| **95°–100°** | Droit (neutre) |
| **110°–115°** | Légèrement à droite |
| **128°** | Virage à droite maximal |

#### Code de contrôle

```python
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50  # 50 Hz pour servos

def set_angle(canal, angle):
    """Positionne le servo du canal à l'angle (0–180°)."""
    s = servo.Servo(
        pca.channels[canal],
        min_pulse_width=0.001,  # 1 ms
        max_pulse_width=0.002   # 2 ms
    )
    s.angle = angle

# Exemple : braquer les roues à droite
set_angle(0, 128)
```

### 5.2 Moteurs DC

![Moteurs DC](images/dc-motors.jpg)

Les **moteurs à courant continu (MCC)** convertissent l'énergie électrique en rotation mécanique. Sur le PiCar-Pro, **2 moteurs** entraînent les 4 roues arrière via une chaîne mécanique.

#### Caractéristiques

| Paramètre | Valeur |
|-----------|--------|
| Tension | 5–7.4V (batterie) |
| Puissance | ~5W par moteur |
| Vitesse à vide | ~300 RPM |
| Sens de rotation | Réversible (via pont en H) |

#### Contrôle : Le pont en H

Pour contrôler à la fois **sens** et **vitesse**, on utilise un **pont en H** :

```
        Vcc
         │
    ┌────┼────┐
    │    │    │
   S1   S2   S3   S4
    │    M    │
    └────┼────┘
        GND
```

| État | Effet |
|------|-------|
| S1+S4 ON | Moteur tourne vers AVANT |
| S2+S3 ON | Moteur tourne vers ARRIÈRE |
| S1+S3 ON | **Freinage** (court-circuit) |
| Tous OFF | Roue libre |

Le Robot HAT intègre les ponts en H — le PCA9685 les pilote directement.

#### Brochage des moteurs

| Moteur | IN1 (canal) | IN2 (canal) |
|--------|-------------|-------------|
| **M1** (gauche) | CH14 | CH15 |
| **M2** (droite) | CH13 | CH12 |

#### Code de contrôle

```python
from adafruit_motor import motor
from adafruit_pca9685 import PCA9685
import busio
from board import SCL, SDA

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

# Créer les objets moteur
motor1 = motor.DCMotor(
    pca.channels[14],  # IN1
    pca.channels[15]   # IN2
)
motor2 = motor.DCMotor(
    pca.channels[13],  # IN1
    pca.channels[12]   # IN2
)

# Freinage progressif
motor1.decay_mode = motor.SLOW_DECAY
motor2.decay_mode = motor.SLOW_DECAY

# Commandes : throttle entre -1.0 (arrière max) et +1.0 (avant max)
motor1.throttle = 0.5   # Moteur 1 à 50% avant
motor2.throttle = 0.5   # Moteur 2 à 50% avant
motor1.throttle = 0.0   # Arrêt
motor1.throttle = -1.0  # Arrière maximum
```

---

## 6. Énergie

### 6.1 Batterie

![Batterie lithium](images/battery-7.4v.jpg)

| Élément | Spécification |
|---------|---------------|
| **Type** | 2 cellules lithium ion 18650 en série |
| **Voltage** | 7.4V nominal (pleine charge ~8.4V) |
| **Capacité** | 2000–2600 mAh |
| **Autonomie** | ~2–3 heures d'utilisation active |
| **Connecteur** | JST (polarité correcte obligatoire) |
| **Sécurité** | Protection court-circuit BMS intégrée |

### 6.2 Distribution d'énergie

```
Batterie 7.4V
      │
      ├──→ Régulateur 5V → Raspberry Pi (USB-C)
      ├──→ Robot HAT (alimentation directe)
      │    ├─→ PCA9685
      │    ├─→ Moteurs DC
      │    └─→ Servos + Capteurs
      │
      └──→ Chargeur USB-C
```

> **Conseil** : Charger la batterie via USB-C du HAT pendant que le robot est immobile.

---

## 7. Signalisation et retours

### 7.1 LEDs

![LEDs RGB](images/leds.jpg)

Trois **LEDs de signalisation** programmables :

| LED | GPIO | Couleur typique | Usage |
|-----|------|-----------------|-------|
| LED1 | GPIO9 | Rouge | Erreur / Critique |
| LED2 | GPIO25 | Vert | Normal / OK |
| LED3 | GPIO11 | Bleu | Mode autonome |

#### Code

```python
from gpiozero import LED
from time import sleep

led2 = LED(25)
led2.on()                      # Allumer
led2.off()                     # Éteindre
led2.blink(on_time=0.5, off_time=0.5)  # Clignoter
```

### 7.2 Buzzer

![Buzzer piézoélectrique](images/buzzer.jpg)

Le **buzzer piézoélectrique** produit des sons de fréquence variable.

| Fréquence | Note | Usage |
|-----------|------|-------|
| 261 Hz | Do | Signal standard |
| 440 Hz | La | Référence d'accordage |
| 1000 Hz | Aigu | Alerte |

#### Code

```python
from gpiozero import TonalBuzzer
import time

buzzer = TonalBuzzer(18)

buzzer.play("C4")    # Do 4e octave
time.sleep(0.5)
buzzer.stop()
```

### 7.3 Écran OLED

![Écran OLED 128×64](images/oled-display.jpg)

Un **petit écran OLED I2C** (128×64 pixels) affiche l'état du robot en temps réel.

---

## 8. Installation logicielle

### 8.1 Prérequis système

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer les outils essentiels
sudo apt install -y \
    git \
    python3-pip \
    python3-dev \
    i2c-tools \
    python3-smbus
```

### 8.2 Bibliothèques Python

```bash
# Adafruit (moteurs, servos, PCA9685)
pip3 install adafruit-circuitpython-pca9685
pip3 install adafruit-circuitpython-motor

# Contrôle GPIO haut niveau
pip3 install gpiozero

# Communication I2C/SPI
pip3 install adafruit-blinka

# Vision par ordinateur (optionnel)
pip3 install opencv-python

# Reconnaissance vocale (optionnel)
pip3 install pyaudio SpeechRecognition
```

### 8.3 Clone du dépôt Adeept

```bash
git clone https://github.com/adeept/Adeept_PiCar-Pro.git
cd Adeept_PiCar-Pro
sudo python3 setup.py
```

---

## 9. Dépannage

### Problème : L'adresse I2C 0x5f n'apparaît pas

```bash
# Vérifier que I2C est activé
sudo raspi-config
# → Interface Options → I2C → Yes

# Puis rebooter
sudo reboot

# Vérifier à nouveau
i2cdetect -y 1
```

### Problème : Les servos ne répondent pas

1. Vérifier l'alimentation 5V du HAT
2. Vérifier que les câbles servo sont bien connectés (GND, +5V, Signal)
3. Tester avec le script minimal :

```python
from adafruit_pca9685 import PCA9685
import busio
from board import SCL, SDA

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
print("PCA9685 détecté à l'adresse", hex(pca.address))
```

### Problème : Les moteurs tournent à l'envers

Inverser les deux canaux du moteur dans le code.

---

## Références

- [Adeept PiCar-Pro GitHub](https://github.com/adeept/Adeept_PiCar-Pro)
- [Adafruit Motor Library](https://docs.adafruit.com/guides/adafruit-motor-selection-guide)
- [HC-SR04 Documentation](https://www.electronicwings.com/sensors/ultrasonic-sensor-hc-sr04)
- [PCA9685 Datasheet](https://www.nxp.com/documents/data_sheet/PCA9685.pdf)
- [Raspberry Pi GPIO Reference](https://www.raspberrypi.com/documentation/computers/gpio.html)
