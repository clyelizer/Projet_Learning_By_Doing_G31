# Électronique Robotique — Adeept PiCar-Pro

> **Documentation de référence** — Décembre 2025
>
> Guide complet de programmation du robot PiCar-Pro sous Raspberry Pi.
> Couvre l'ensemble de la chaîne : capteurs, actionneurs, moteurs, suivi de ligne,
> contrôle à distance et résolution de problèmes.

---

## Table des matières

1. [Présentation générale](#présentation-générale)
2. [Architecture du robot](#architecture-du-robot)
3. [Inventaire des capteurs et modules](#inventaire-des-capteurs-et-modules)
4. [Installation et premiers pas](#installation-et-premiers-pas)
5. [Contrôle des LEDs](#contrôle-des-leds)
6. [Le Buzzer](#le-buzzer)
7. [Le capteur ultrason HC-SR04](#le-capteur-ultrason-hc-sr04)
8. [Les servomoteurs](#les-servomoteurs)
9. [Le bus I2C et le contrôleur PCA9685](#le-bus-i2c-et-le-contrôleur-pca9685)
10. [Les moteurs DC](#les-moteurs-dc)
11. [Le suiveur de ligne](#le-suiveur-de-ligne)
12. [Cas d'usages avancés](#cas-dusages-avancés)
13. [Pilotage à distance (SSH et VNC)](#pilotage-à-distance-ssh-et-vnc)
14. [Projet final — Application complète](#projet-final--application-complète)
15. [Référence rapide des broches](#référence-rapide-des-broches)

---

## Présentation générale

### Qu'est-ce qu'un robot ?

Un robot est un **système mécatronique** — c'est-à-dire une machine alliant mécanique,
électronique et informatique — capable d'exécuter automatiquement une ou plusieurs
tâches physiques. Il repose sur trois piliers fondamentaux :

| Pilier | Rôle | Exemples |
|--------|------|----------|
| **Capteurs** | Percevoir l'environnement | Ultrason, caméra, capteurs infrarouges |
| **Actionneurs** | Agir sur le monde physique | Moteurs, servomoteurs, vérins |
| **Unité de contrôle** | Traiter l'information et décider | Raspberry Pi, Arduino |

Ces trois éléments forment une **boucle de contrôle** : les capteurs informent l'unité
de contrôle, qui commande les actionneurs en retour.

```
    ┌──────────┐     commandes     ┌─────────────┐
    │ Contrôle │ ────────────────► │ Actionneurs  │
    │  (RPi)   │                   │ (moteurs,    │
    └──────────┘                   │  servos)     │
          ▲                        └──────┬───────┘
          │        mesures                │
          │    ┌─────────────┐            │
          └─── │  Capteurs   │ ◄──────────┘
               │ (ultrason,  │    actions physiques
               │  IR, …)     │
               └─────────────┘
```

### La robotique, un domaine pluridisciplinaire

La robotique se situe à l'intersection de nombreuses disciplines :
mécanique, électronique, informatique, automatique, intelligence artificielle,
physique, mathématiques, éthique et science des matériaux.

### Le PiCar-Pro Adeept

Le robot utilisé dans ce cours est le **PiCar-Pro de Adeept**, un robot mobile
à quatre roues équipé :

- d'une carte **Raspberry Pi** comme unité de contrôle
- d'un **Robot HAT V3.2** (carte d'extension) pour le pilotage des périphériques
- d'un **bras articulé** à plusieurs degrés de liberté
- de **capteurs** : ultrason, suiveur de ligne, détection d'obstacles

---

## Architecture du robot

### La carte Robot HAT V3.2

Le Robot HAT est une carte d'extension qui se connecte directement sur le GPIO
du Raspberry Pi. Elle intègre :

| Composant | Rôle |
|-----------|------|
| **PCA9685** | Contrôleur PWM 16 canaux, pilote les servos et moteurs DC |
| **Ponts en H** | Permettent de commander le sens de rotation des moteurs |
| **Connecteurs servos** | Sorties CH0 à CH15 pour les servomoteurs du bras |
| **Connecteurs capteurs** | Entrées pour ultrason, suiveur de ligne |

### Le PCA9685

Le PCA9685 est un circuit intégré piloté en I2C. Il génère 16 signaux PWM
indépendants, ce qui permet de contrôler jusqu'à 16 servomoteurs simultanément
avec une seule connexion I2C (2 fils). Sur le PiCar-Pro, les canaux sont répartis
entre les servos du bras (CH0–CH7) et les moteurs DC (CH12–CH15).

### Les composants du robot

| Composant | Broche / Canal | Fonction |
|-----------|---------------|----------|
| LED1, LED2, LED3 | GPIO9, GPIO25, GPIO11 | Signalisation visuelle |
| Buzzer | GPIO18 | Signal sonore |
| Ultrason HC-SR04 | GPIO23 (Trig), GPIO24 (Echo) | Mesure de distance |
| Capteurs IR (×3) | GPIO17, GPIO27, GPIO22 | Suivi de ligne |
| Servo direction | PCA9685 CH0 | Orientation des roues avant |
| Servo ultrasons | PCA9685 CH1 | Orientation du capteur ultrason |
| Servos bras | PCA9685 CH2, CH3 | Articulations du bras |
| Servo pince | PCA9685 CH4 | Ouverture/fermeture de la pince |
| Moteur DC 1 | PCA9685 CH14, CH15 | Roues arrière gauche |
| Moteur DC 2 | PCA9685 CH12, CH13 | Roues arrière droite |

---

## Inventaire des capteurs et modules

Le PiCar-Pro V2 est équipé d'une gamme complète de périphériques :

| Composant | Description |
|-----------|-------------|
| Caméra USB + Microphone | Capture vidéo et audio pour la vision par ordinateur |
| 8 servomoteurs PCA9685 | Mobilité et contrôle des articulations du bras |
| Module ultrasonique HC-SR04 | Détection de distance et d'obstacles (2 cm à 4 m) |
| Capteurs de ligne (×3) | Suivi de ligne infrarouge (S1, S2, S3) |
| LEDs indicatrices (×3) | Signalisation visuelle (LED1, LED2, LED3) |
| Buzzer passif | Alertes sonores et mélodies |
| Moteurs à courant continu (×2) | Propulsion (M1, M2, 4 roues via chaîne mécanique) |
| Écran OLED | Affichage d'informations |
| LED RGB WS2812 | Éclairage d'ambiance programmable |
| Récepteur IR | Réception de signaux infrarouges (télécommande) |
| Connecteur batterie | Alimentation du robot |

### Tableau des fonctionnalités du Robot HAT V3.2

| Interface | Description |
|-----------|-------------|
| **Power** | Alimentation externe |
| **Switch** | Interrupteur ON/OFF du HAT |
| **Type-C USB** | Alimentation de la carte mère ou charge de la batterie |
| **Buzzer** | Buzzer passif intégré |
| **IR** | Récepteur infrarouge intégré |
| **Servo port** | Connecteurs pour servomoteurs (CH0–CH15) |
| **Motor** | 2 ports moteurs : M1, M2 |
| **X8 : Line Tracking** | Connecteur pour le module suiveur de ligne 3 canaux |
| **X9 : Ultrasonic** | Connecteur pour le capteur ultrason HC-SR04 |
| **LED1~3** | Trois LEDs avec interface interrupteur, utilisables pour connecter LEDs ou autres équipements |

---

## Installation et premiers pas

### Prérequis logiciels

Sur le Raspberry Pi, exécuter une fois le script d'installation :

```bash
sudo apt update
sudo apt install git -y
git clone https://github.com/adeept/Adeept_PiCar-Pro.git
cd Adeept_PiCar-Pro
sudo python3 setup.py
```

Ce script installe toutes les dépendances nécessaires :
- `adafruit-circuitpython-pca9685` — pilote du contrôleur PWM
- `adafruit-circuitpython-motor` — contrôle des moteurs DC et servos
- `gpiozero` — abstraction haut niveau pour les GPIO
- `RPi.GPIO` — contrôle bas niveau des broches

### Avant chaque séance

1. **Lancer le programme SETUP** sur le robot avant toute manipulation
2. Vérifier que le PCA9685 est détecté :

```bash
i2cdetect -y 1
```

L'adresse `0x5f` doit apparaître dans la grille. Si elle est absente, vérifier
la connexion du HAT.

### Règles de travail

- Deux groupes partagent un robot — organiser l'utilisation
- Supprimer vos programmes du robot à la fin de chaque séance
- Sauvegarder votre travail sur clé USB ou espace personnel
- Nommer les fichiers : `EX1-PLBDX` (X = numéro de groupe)

---

## Contrôle des LEDs

### Principe

Une LED (diode électroluminescente) est un composant qui émet de la lumière
lorsqu'un courant le traverse. Le Raspberry Pi peut commander une LED via
ses broches GPIO en fournissant une tension de 3.3V (état HIGH) ou 0V (état LOW).

Le Robot HAT embarque trois LEDs de signalisation.

### La bibliothèque gpiozero

`gpiozero` est une bibliothèque Python conçue pour simplifier le contrôle des
composants électroniques sur Raspberry Pi. Elle fournit des objets Python
intuitifs pour chaque type de périphérique.

```python
from gpiozero import LED
from time import sleep

led = LED(17)        # LED connectée au GPIO17

led.on()             # Allumer
led.off()            # Éteindre
led.toggle()         # Inverser l'état
led.blink()          # Clignoter indéfiniment
led.blink(on_time=0.5, off_time=0.5)  # Clignoter avec durée
led.blink(n=3)       # Clignoter 3 fois
print(led.is_lit)    # True si allumée, False sinon
```

### Exercice — Alternance de LEDs

**Objectif :** Contrôler LED2 et LED3 selon une séquence définie.

**Consigne :**
1. Allumer LED2 et LED3 alternativement (1 seconde de pause entre chaque)
2. Puis allumer les deux simultanément pendant 2 secondes
3. Puis éteindre les deux pendant 1 seconde
4. Recommencer indéfiniment
5. Afficher l'état des LEDs dans le terminal à chaque étape

**Solution avec gpiozero (recommandée) :**

```python
from gpiozero import LED
from time import sleep

led2 = LED(25)
led3 = LED(11)

while True:
    # Phase 1 : alternance
    led2.on(); led3.off()
    print("LED2 ON, LED3 OFF")
    sleep(1)

    led2.off(); led3.on()
    print("LED2 OFF, LED3 ON")
    sleep(1)

    # Phase 2 : les deux allumées
    led2.on(); led3.on()
    print("LED2 ON, LED3 ON")
    sleep(2)

    # Phase 3 : extinction
    led2.off(); led3.off()
    print("LED2 OFF, LED3 OFF")
    sleep(1)
```

**Solution avec RPi.GPIO (niveau plus bas) :**

```python
import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)       # Numérotation BCM (GPIOxx)
GPIO.setup(25, GPIO.OUT)     # LED2
GPIO.setup(11, GPIO.OUT)     # LED3

try:
    while True:
        GPIO.output(25, GPIO.HIGH); GPIO.output(11, GPIO.LOW)
        sleep(1)
        GPIO.output(25, GPIO.LOW);  GPIO.output(11, GPIO.HIGH)
        sleep(1)
        GPIO.output(25, GPIO.HIGH); GPIO.output(11, GPIO.HIGH)
        sleep(2)
        GPIO.output(25, GPIO.LOW);  GPIO.output(11, GPIO.LOW)
        sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()            # Libère les GPIO
```

> **Pourquoi deux versions ?** gpiozero est plus simple et plus lisible.
> RPi.GPIO donne un contrôle plus fin et est utile pour comprendre le
> fonctionnement bas niveau des broches.

---

## Le Buzzer

### Principe

Un buzzer piézoélectrique convertit un signal électrique en vibration mécanique,
produisant un son. La fréquence du signal électrique détermine la hauteur de la
note produite.

### Commandes de base

```python
from gpiozero import TonalBuzzer
import time

tb = TonalBuzzer(18)    # GPIO18
tb.play("C4")           # Joue un Do (4e octave)
time.sleep(0.5)
tb.stop()
```

### Fréquences des notes musicales

| Note | Octave 3 (grave) | Octave 4 (médium) | Octave 5 (aigu) |
|------|-----------------|-------------------|-----------------|
| Do (C) | 131 Hz | 261 Hz | 523 Hz |
| Ré (D) | 147 Hz | 294 Hz | 587 Hz |
| Mi (E) | 165 Hz | 330 Hz | 659 Hz |
| Fa (F) | 175 Hz | 349 Hz | 698 Hz |
| Sol (G) | 196 Hz | 392 Hz | 784 Hz |
| La (A) | 220 Hz | 440 Hz | 880 Hz |
| Si (B) | 247 Hz | 494 Hz | 988 Hz |

> L'octave 4 correspond aux notes médium. Le La 440 Hz est la référence
> d'accordage standard.

### Exercice

1. Faire sonner le buzzer trois fois avec des notes différentes
2. Faire sonner le buzzer en faisant clignoter les deux LEDs pendant 5 secondes

---

## Le capteur ultrason HC-SR04

### Principe de fonctionnement

Le HC-SR04 mesure les distances par **écholocation ultrasonique**, sur le même
principe que le sonar des chauves-souris :

1. Le Raspberry Pi envoie une **impulsion de 10 µs** sur la broche TRIGGER
2. Le capteur émet alors une **salve de 8 impulsions ultrasoniques à 40 kHz**
3. Ces ondes se propagent dans l'air à environ **340 m/s**
4. Lorsqu'elles rencontrent un obstacle, elles sont réfléchies vers le capteur
5. Le capteur détecte l'écho et émet un signal sur la broche ECHO dont la durée
   est proportionnelle à la distance parcourue

```
    TRIGGER  ──┐               ┌──
               └───────────────┘   impulsion 10 µs
               
    ULTRASONS      ┊┊┊┊┊┊┊┊        8 cycles à 40 kHz
                        ↓
              ╔═══════════════╗
              ║   OBSTACLE    ║
              ╚═══════════════╝
                        ↓
    ECHO      ──────────┐       ┌──
                        └───────┘   durée ∝ distance
```

### Calcul de la distance

La distance $d$ est liée au temps $t$ par la relation :

$$t = \frac{2d}{V}$$

où $V = 340 \text{ m/s}$ est la vitesse du son dans l'air.

En unités pratiques :

$$ d_{(\text{cm})} = \frac{t_{(\mu s)}}{58} $$

> **Pourquoi diviser par 58 ?**
>
> $d = \dfrac{340 \times t}{2} = \dfrac{34000 \text{ cm/s}}{2} \times t_{(s)}$
>
> $= \dfrac{34000}{2 \times 10^6} \times t_{(\mu s)} = \dfrac{17}{1000} \times t_{(\mu s)}$
>
> $= \dfrac{t_{(\mu s)}}{58.8} \approx \dfrac{t_{(\mu s)}}{58}$

### Caractéristiques techniques

| Paramètre | Valeur |
|-----------|--------|
| Tension d'alimentation | 5V DC |
| Consommation | 15 mA |
| Portée maximale | 4 mètres |
| Portée minimale | 2 cm |
| Angle de détection | ~15° |
| Fréquence ultrason | 40 kHz |

### Brochage

| Raspberry Pi | HC-SR04 |
|-------------|---------|
| GPIO23 | Trig |
| GPIO24 | Echo |
| 5V | VCC |
| GND | GND |

> **Attention :** Le HC-SR04 fonctionne en 5V. Le HAT gère l'adaptation de
> niveau logique automatiquement. Ne pas connecter directement l'Echo (5V)
> sur un GPIO du Raspberry Pi sans adaptateur de niveau.

### Exercice 3 — Mesure continue et alerte de proximité

1. Développer un programme qui effectue une mesure continue de la distance
   entre le capteur et un obstacle, puis affiche la valeur lue en cm et en mm.
2. Développer un programme qui fait sonner le Buzzer et allumer les LEDs si
   un obstacle se trouve à 5 cm ou moins du robot.

---

## Les servomoteurs

### Qu'est-ce qu'un servomoteur ?

Un servomoteur est un actionneur capable de **positionner son axe à un angle
précis** (généralement entre 0° et 180°). Contrairement à un moteur classique
qui tourne continûment, un servo **maintient sa position** même sans signal.

Le contrôle s'effectue par **modulation de largeur d'impulsion (PWM)** :
- Une impulsion de 500 µs correspond à 0°
- Une impulsion de 1500 µs correspond à 90°
- Une impulsion de 2500 µs correspond à 180°

Le signal PWM doit être émis à une fréquence de **50 Hz** (période de 20 ms).

```
     ┌──┐                              ┌──┐
     │  │ 500 µs  →  0°                │  │
  ───┘  └──────────────────────────────┘  └─────
     ┌─────┐                           ┌─────┐
     │     │ 1500 µs → 90°             │     │
  ───┘     └───────────────────────────┘     └──
     ┌──────────┐                      ┌──────────┐
     │          │ 2500 µs → 180°       │          │
  ───┘          └──────────────────────┘          └
     |← 20 ms →|
```

### Les servos du PiCar-Pro

Le robot utilise cinq servomoteurs, tous pilotés par le PCA9685 :

| Servo | Canal PCA9685 | Fonction |
|-------|--------------|----------|
| Servo A | CH0 | Direction des roues avant (0°–180°) |
| Servo B | CH1 | Orientation du module ultrason |
| Servo C | CH2 | Coude du bras (mouvement vertical) |
| Servo D | CH3 | Épaule du bras |
| Servo E | CH4 | Pince (ouverture/fermeture) |

### API de contrôle

```python
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

# Initialisation du bus I2C et du PCA9685
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50               # Fréquence PWM pour servos

def set_angle(canal, angle):
    """Positionne le servo du canal spécifié à l'angle donné."""
    s = servo.Servo(
        pca.channels[canal],
        min_pulse=500,            # Largeur d'impulsion à 0°
        max_pulse=2400,           # Largeur d'impulsion à 180°
        actuation_range=180
    )
    s.angle = angle
```

### Exercice — Rotation synchronisée de deux servos

**Objectif :** Piloter simultanément le servo des roues (CH0) et le servo
du module ultrason (CH1).

**Comportement attendu :**
1. Les deux servos tournent de 0° à 180° simultanément, puis attendent 0.5s
2. Les deux servos tournent de 180° à 0° simultanément, puis attendent 0.5s
3. La séquence se répète indéfiniment
4. Lorsque l'utilisateur interrompt le programme (Ctrl+C), les deux servos
   reviennent automatiquement à 90° (position neutre)

```python
import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

def set_angle(canal, angle):
    s = servo.Servo(pca.channels[canal],
                    min_pulse=500, max_pulse=2400,
                    actuation_range=180)
    s.angle = angle

def set_multiple_angles(canaux, angle):
    """Applique le même angle à plusieurs canaux."""
    for c in canaux:
        set_angle(c, angle)

def tourner(canaux):
    """Effectue un cycle complet 0°→180°→0°."""
    for angle in range(180):
        set_multiple_angles(canaux, angle)
        time.sleep(0.01)
    time.sleep(0.5)
    for angle in range(180, 0, -1):
        set_multiple_angles(canaux, angle)
        time.sleep(0.01)
    time.sleep(0.5)

if __name__ == "__main__":
    canaux = [0, 1]  # CH0 = roues, CH1 = ultrason
    try:
        print(f"Servos {canaux} — rotation continue (Ctrl+C pour arrêter)")
        while True:
            tourner(canaux)
    except KeyboardInterrupt:
        print("\nRetour à 90° et libération des ressources.")
        set_multiple_angles(canaux, 90)
        pca.deinit()
```

### Exercice — Pince asservie à l'ultrason

**Objectif :** Utiliser la distance mesurée par l'ultrason pour commander
le servo de la pince.

- Si la distance est **inférieure à 5 cm** → ouvrir la pince
- Sinon → fermer la pince

---

## Le bus I2C et le contrôleur PCA9685

### Qu'est-ce que le bus I2C ?

**I2C** (Inter-Integrated Circuit) est un bus de communication série conçu
pour faire dialoguer un microcontrôleur avec plusieurs périphériques en
n'utilisant que **deux fils** :

| Signal | Rôle |
|--------|------|
| **SDA** (Serial Data) | Ligne de données bidirectionnelle |
| **SCL** (Serial Clock) | Horloge de synchronisation |

Une **résistance de pull-up** ($R_p$) relie chaque ligne à la tension
d'alimentation ($V_{dd}$). Sans ces résistances, les lignes seraient flottantes
et la communication impossible.

Chaque périphérique I2C possède une **adresse unique** (7 bits). Le PCA9685
du PiCar-Pro répond à l'adresse **0x5f**.

```
          Vdd
           │
          ┌┴┐ Rp
          │ │
          ├─┴─────┬──────────┬──────────┐
         SDA       │          │          │
          ├────────┼──────────┼──────────┤
         SCL       │          │          │
          │         │          │          │
       ┌──┴──┐  ┌──┴──┐   ┌──┴──┐   ┌──┴──┐
       │MASTER│  │SLAVE│   │SLAVE│   │SLAVE│
       │ (RPi)│  │  #1  │   │  #2  │   │  #3  │
       └─────┘  └─────┘   └─────┘   └─────┘
```

### Vérification de la connexion I2C

```bash
i2cdetect -y 1
```

La sortie affiche une grille. L'adresse `0x5f` (ou `5f` en hexadécimal) doit
être marquée d'un numéro. Si ce n'est pas le cas :
- Vérifier que le HAT est bien connecté au Raspberry Pi
- Vérifier que le câble d'alimentation est branché
- Vérifier que l'I2C est activé dans `raspi-config`

### Le PCA9685 en détail

Le PCA9685 est un **générateur PWM 16 canaux**. Chaque canal peut produire
un signal PWM indépendant avec une résolution de 12 bits (4096 pas).

Les canaux sont répartis en deux groupes :

| Canaux | Usage sur le PiCar-Pro |
|--------|----------------------|
| CH0–CH7 | Servomoteurs (bras, direction, pince) |
| CH12–CH15 | Moteurs DC (via ponts en H, M1+M2) |

---

## Les moteurs DC

### Principe

Un moteur à courant continu (MCC) transforme l'énergie électrique en énergie
mécanique de rotation. Pour le piloter, on a besoin de :

1. **Contrôler la vitesse** → via un signal PWM (rapport cyclique variable)
2. **Contrôler le sens de rotation** → via un **pont en H**

### Le pont en H

Un pont en H est un circuit composé de 4 interrupteurs (transistors) disposés
en forme de H autour du moteur :

```
        Vcc
         │
    ┌────┴────┐
    │ S1   S3 │
    ├───┐ ┌───┤
    │   │ │   │
    │  ┌┴┴┐  │
    │  │ M │  │   M = Moteur
    │  └┬┬┘  │
    │   │ │   │
    ├───┘ └───┤
    │ S2   S4 │
    └────┴────┘
         │
        GND
```

| État | Effet |
|------|-------|
| S1+S4 fermés, S2+S3 ouverts | Le moteur tourne dans un sens |
| S2+S3 fermés, S1+S4 ouverts | Le moteur tourne dans l'autre sens |
| S1+S3 fermés (ou S2+S4) | **Freinage** (le moteur est court-circuité) |
| Tous ouverts | Roue libre (le moteur n'est pas alimenté) |

Le Robot HAT V3.2 intègre les ponts en H. Vous n'avez pas à les câbler —
le PCA9685 les pilote directement.

### Comment tourne le robot

Le PiCar-Pro tourne par **braquage des roues avant**, pas par différentiel moteur :
- Le servo CH0 oriente les roues (45° = gauche, 95° = droit, 128° = droite)
- Les 2 moteurs tournent à la **même vitesse** (avant ou arrière)
- Le virage = braquage + avance simultanée des deux roues

### Brochage des moteurs

| Moteur | IN1 | IN2 |
|--------|-----|-----|
| Moteur 1 (gauche) | CH14 | CH15 |
| Moteur 2 (droite) | CH13 | CH12 |

> **Note sur le câblage :** selon le lot, les paires IN1/IN2 peuvent être
> inversées. Si un moteur tourne à l'envers, échanger les deux canaux.

### Initialisation des moteurs

```python
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor

# Bus I2C
i2c = busio.I2C(SCL, SDA)
pwm = PCA9685(i2c, address=0x5f)
pwm.frequency = 50

# Définition des canaux
MOTOR_M1_IN1 = 14; MOTOR_M1_IN2 = 15   # Moteur 1
MOTOR_M2_IN1 = 13; MOTOR_M2_IN2 = 12   # Moteur 2

# Création des objets moteur
motor1 = motor.DCMotor(pwm.channels[MOTOR_M1_IN1],
                       pwm.channels[MOTOR_M1_IN2])
motor2 = motor.DCMotor(pwm.channels[MOTOR_M2_IN1],
                       pwm.channels[MOTOR_M2_IN2])

# Mode de décélération : SLOW_DECAY = freinage progressif
motor1.decay_mode = motor.SLOW_DECAY
motor2.decay_mode = motor.SLOW_DECAY
```

### Contrôle de la vitesse

La vitesse est contrôlée par l'attribut `throttle`, compris entre −1.0 et +1.0 :

```
  +1.0 ████████████████████  Vitesse maximale, AVANT
  +0.5 ██████████            Moitié vitesse, AVANT
   0.0                       ARRÊT
  -0.5           ██████████  Moitié vitesse, ARRIÈRE
  -1.0           ████████████████████  Vitesse max, ARRIÈRE
```

### Fonctions de mouvement

Le robot se pilote avec deux fonctions : `steer(angle)` pour braquer, `drive(throttle)` pour avancer. **Pas de différentiel** — les deux roues tournent toujours à la même vitesse.

```python
SERVO_STEER = 0
STEER_CENTER = 95
STEER_LEFT   = 45
STEER_RIGHT  = 128

_servo = None

def steer(angle):
    """Braque les roues : 45=gauche, 95=droit, 128=droite."""
    global _servo
    if _servo is None:
        _servo = servo.Servo(pwm.channels[SERVO_STEER],
                             min_pulse=500, max_pulse=2400,
                             actuation_range=180)
    _servo.angle = angle

def drive(throttle):
    """Les 2 moteurs à la même vitesse. -1.0 arrière .. +1.0 avant."""
    motor1.throttle = throttle
    motor2.throttle = throttle

def arret():
    motor1.throttle = 0.0
    motor2.throttle = 0.0
```

### Exercice — Mouvements de base

Écrire un programme qui enchaîne : avancer 1s → reculer 1s → tourner à droite
et avancer → tourner à gauche et avancer.

### Exercice — Trajet complet avec transport

Écrire un programme qui effectue un trajet du point A au point B comprenant :
- Une phase d'avancement en ligne droite
- Un virage (droite ou gauche selon le parcours)
- Une nouvelle ligne droite jusqu'au point B
- Puis le transport d'une pièce avec le bras (du point A au point B)

Le code complet intégrant moteurs et servos est donné ci-dessous. La fonction
`set_angle(0, angle)` contrôle le servo de direction (CH0). Pour tourner,
on combine la rotation des moteurs avec une orientation des roues :

```python
import time
from board import SCL, SDA
import busio
from adafruit_motor import motor, servo
from adafruit_pca9685 import PCA9685

# ── Initialisation ──────────────────────────────────────────────
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=0x5f)
pca.frequency = 50

def set_angle(canal, angle):
    s = servo.Servo(pca.channels[canal],
                    min_pulse=500, max_pulse=2400,
                    actuation_range=180)
    s.angle = angle

MOTOR_M1_IN1 = 14; MOTOR_M1_IN2 = 15
MOTOR_M2_IN1 = 13; MOTOR_M2_IN2 = 12

motor1 = motor.DCMotor(pca.channels[MOTOR_M1_IN1],
                       pca.channels[MOTOR_M1_IN2])
motor2 = motor.DCMotor(pca.channels[MOTOR_M2_IN1],
                       pca.channels[MOTOR_M2_IN2])
motor1.decay_mode = motor.SLOW_DECAY
motor2.decay_mode = motor.SLOW_DECAY

steer(STEER_CENTER)  # Roues droites

# ── Fonctions de mouvement ──────────────────────────────────────
def avancer(v=0.5):
    motor1.throttle = v; motor2.throttle = v
    steer(STEER_CENTER)

def reculer(v=0.5):
    motor1.throttle = -v; motor2.throttle = -v
    steer(STEER_CENTER)

def tourner_gauche(v=0.5):
    motor1.throttle = v; motor2.throttle = v
    steer(STEER_LEFT)        # Roues braquées à gauche

def tourner_droite(v=0.5):
    motor1.throttle = v; motor2.throttle = v
    steer(STEER_RIGHT)       # Roues braquées à droite

def arret():
    motor1.throttle = 0.0; motor2.throttle = 0.0
    steer(STEER_CENTER)

# ── Programme principal ─────────────────────────────────────────
try:
    while True:
        avancer(0.5);  time.sleep(2)
        reculer(0.5);  time.sleep(2)
        tourner_gauche(0.5); time.sleep(2)
        tourner_droite(0.5); time.sleep(2)
        arret(); time.sleep(2)
except KeyboardInterrupt:
    arret()
    pca.deinit()
```

---

## Le suiveur de ligne

### Principe

Le suivi de ligne repose sur la différence de **réflectivité infrarouge** entre
une surface noire et une surface blanche :

1. Une **LED infrarouge** émet un faisceau vers le sol
2. Une surface **blanche** réfléchit fortement le faisceau → le phototransistor
   reçoit un signal important
3. Une surface **noire** absorbe le faisceau → le phototransistor ne reçoit
   quasiment rien
4. Le capteur traduit cette différence en signal logique : **0 = ligne noire**,
   **1 = surface blanche**

```
      ┌─────────────┐
      │ LED IR       │───► faisceau émis
      └─────────────┘
              │
              ▼
   ════════════════════════════  surface
        noir     blanc
   ════════════════════════════
              │
              ▼
      ┌─────────────┐
      │ Phototrans.  │◄─── faisceau réfléchi
      └─────────────┘
```

### Les trois capteurs

Le PiCar-Pro embarque un **module à trois capteurs** alignés transversalement.
Ces capteurs permettent de savoir si la ligne noire est centrée sous le robot
ou décalée à gauche ou à droite.

```
     ┌──────────────────────────┐
     │      ROBOT (vue dessus)  │
     │                          │
     │    [S3]   [S2]   [S1]    │ ← 3 capteurs IR alignés
     │   gauche milieu droite   │
     └──────────────────────────┘
     ═══════════╗               ← ligne noire à suivre
                ║
                ╚═══════════════
```

### Brochage

| Capteur | GPIO Raspberry Pi | Position |
|---------|------------------|----------|
| S1 | GPIO17 | Droite |
| S2 | GPIO27 | Milieu |
| S3 | GPIO22 | Gauche |

### Lecture des capteurs

```python
import time
from gpiozero import InputDevice

capteur_droite = InputDevice(pin=17)     # S1
capteur_milieu = InputDevice(pin=27)     # S2
capteur_gauche = InputDevice(pin=22)     # S3

def lire_capteurs():
    """Retourne l'état des trois capteurs (0 = noir, 1 = blanc)."""
    L = capteur_gauche.value
    M = capteur_milieu.value
    R = capteur_droite.value
    return L, M, R

while True:
    gauche, milieu, droite = lire_capteurs()
    print(f"G:{gauche} M:{milieu} D:{droite}")
    time.sleep(0.1)
```

> **Note :** Les capteurs retournent 0 quand ils sont au-dessus de la ligne
> noire (pas de réflexion) et 1 sur une surface blanche.

### Logique de décision

À partir de l'état des trois capteurs, le robot choisit une action :

| Gauche (S3) | Milieu (S2) | Droite (S1) | Interprétation | Action |
|:---:|:---:|:---:|---|---|
| 0 | 0 | 0 | Aucune ligne détectée | Chercher la ligne |
| 0 | 0 | 1 | Ligne à droite | Tourner à droite |
| 0 | 1 | 0 | Ligne au centre | Avancer droit |
| 0 | 1 | 1 | Ligne centre + droite | Tourner à droite |
| 1 | 0 | 0 | Ligne à gauche | Tourner à gauche |
| 1 | 0 | 1 | Ligne gauche + droite (fourche) | Aller tout droit |
| 1 | 1 | 0 | Ligne gauche + centre | Tourner à gauche |
| 1 | 1 | 1 | Ligne sur les trois | Aller tout droit |

**Algorithme de décision :**

```python
L, M, R = lire_capteurs()

if M == 0:                          # Ligne sous le capteur central
    if L == 0 and R == 1:
        tourner_droite()            # Ligne dérive à droite
    elif L == 1 and R == 0:
        tourner_gauche()            # Ligne dérive à gauche
    else:
        avancer()                   # Ligne centrée
else:                               # Pas de ligne au centre
    if L == 0 and R == 1:
        tourner_droite()
    elif L == 1 and R == 0:
        tourner_gauche()
    else:
        avancer()                   # Continue (ou cherche)
```

### Le parcours

Le parcours final comporte deux phases :

**Phase 1 — Parcours linéaire :**
Le robot part de l'entrepôt A, suit une ligne noire sinueuse, marque un arrêt
au panneau STOP, puis continue jusqu'à la zone de déchargement B.

**Phase 2 — Parcours avec embranchements :**
Le robot navigue dans un environnement plus complexe comprenant :
- Des stations de couleur (rouge, bleu, vert) au point C
- Une zone de stockage en hauteur D (avec panneau STOP)
- Une zone de chargement de camion E
- Une boucle avec engrenage et une zone délimitée par un carré jaune

### Exercice — Suiveur de ligne complet

1. Développer le programme de contrôle des moteurs et suivi de ligne noire
2. Ajouter la détection d'obstacle : le robot doit s'arrêter lorsqu'un obstacle
   est détecté, puis reprendre une fois l'obstacle retiré
3. Ajouter le transport de pièce : le robot transporte un objet du point A au
   point B tout en suivant la ligne

---

## Cas d'usages avancés

Au-delà des fonctions de base, le PiCar-Pro permet d'explorer des cas d'usage
avancés, notamment grâce à sa caméra USB et son microphone.

### Suivi de ligne par vision (Machine Vision Line Tracking)

En complément des capteurs infrarouges, la caméra permet un suivi de ligne plus
robuste par traitement d'image. La caméra filme la ligne au sol et un algorithme
de vision par ordinateur (OpenCV) détermine la position du robot par rapport à
celle-ci.

### Évitement d'obstacles (Obstacle Avoidance)

Combinant le capteur ultrason et la caméra, le robot peut détecter et contourner
les obstacles sur son chemin. L'ultrason fournit la distance, la caméra identifie
la nature de l'obstacle.

### Suivi de couleur (Color Tracking)

La caméra permet de suivre un objet d'une couleur spécifique. Un algorithme de
traitement d'image segmente les pixels par plage de couleur (HSV) et guide le
robot vers la cible.

### Transmission vidéo en temps réel

La caméra USB du robot peut streamer la vidéo en direct vers un poste distant,
permettant un pilotage à vue même sans ligne de vue directe.

### Reconnaissance vocale (Speech Recognition)

Le microphone intégré permet de capter des commandes vocales. Couplé à un moteur
de reconnaissance (type Google Speech API ou Vosk), le robot peut obéir à des
ordres simples (« avance », « tourne à gauche »).

### Éclairage d'ambiance WS2812

Le robot embarque une LED RGB WS2812 programmable. Chaque LED peut afficher une
couleur indépendante parmi 16 millions de combinaisons, pour des effets lumineux
ou un retour visuel d'état.

### Résumé des capacités

- Suivi de ligne
- Vision par ordinateur et reconnaissance d'objets
- Reconnaissance vocale
- Détection et évitement d'obstacles
- Bras robotique et automatisation simple
- Contrôle à distance (SSH / VNC)
- Transmission vidéo en temps réel

---

## Pilotage à distance (SSH et VNC)

### Pourquoi SSH ?

SSH (Secure Shell) permet de se connecter au Raspberry Pi du robot sans écran,
clavier ni souris. Depuis un ordinateur portable connecté au même réseau WiFi,
vous pouvez éditer et exécuter du code directement sur le robot.

### Connexion au robot

**Étape 1 — Sur le Raspberry Pi (à faire une fois) :**

```bash
# Vérifier que SSH est actif
sudo systemctl status ssh

# Si ce n'est pas le cas, l'activer
sudo systemctl enable ssh
sudo systemctl start ssh

# Obtenir l'adresse IP du robot
hostname -I
# Exemple de sortie : 172.22.2.212
```

**Étape 2 — Depuis votre ordinateur :**

```bash
# Connexion SSH
ssh pi@172.22.2.212

# Première connexion : accepter l'empreinte
# Are you sure you want to continue connecting? → yes
# Mot de passe : pi
```

### Commandes essentielles une fois connecté

```bash
ls                                  # Lister les fichiers et dossiers
cd Desktop/RobotCode               # Se déplacer dans un dossier
cd ..                               # Remonter d'un niveau
sudo python3 Desktop/RobotCode/led.py   # Exécuter un programme
nano led.py                         # Créer ou modifier un fichier
# Dans nano : Ctrl+O → Enter → Ctrl+X  pour enregistrer et quitter
#             Ctrl+A puis Ctrl+K        pour couper une ligne
```

### Flux de travail recommandé

1. Écrire le code sur votre ordinateur
2. Le transférer sur le robot (via `scp`, clé USB, ou directement dans nano)
3. Exécuter le programme sur le robot via SSH
4. Observer le comportement du robot
5. Corriger et répéter

### Connexion via VNC Viewer

VNC (Virtual Network Computing) permet de prendre le contrôle du **bureau complet**
du Raspberry Pi. Vous voyez l'écran du robot comme si vous étiez devant.

**Configuration sur le Raspberry Pi :**

```bash
# Activer VNC dans raspi-config
sudo raspi-config
# → Interface Options → VNC → Yes → OK → Finish

# Ou en ligne de commande
sudo systemctl enable vncserver-x11-serviced
sudo systemctl start vncserver-x11-serviced
```

**Depuis l'ordinateur :**

1. Installer VNC Viewer (gratuit sur realvnc.com)
2. Se connecter à l'adresse IP du robot (même IP que pour SSH)
3. S'authentifier avec le login `pi` et le mot de passe du Raspberry Pi

**Quand utiliser SSH vs VNC ?**

| SSH | VNC |
|-----|-----|
| Terminal texte uniquement | Bureau graphique complet |
| Plus léger, plus rapide | Plus lourd, nécessite plus de bande passante |
| Idéal pour éditer/exécuter du code | Idéal pour voir la caméra, l'interface graphique |
| Fonctionne même sur réseau lent | Préférer un bon WiFi |

---

## Projet final — Application complète

L'objectif est de développer un programme combinant l'ensemble des composants
étudiés :

**Fonctionnalités obligatoires :**

1. **Détection d'objet :** le capteur ultrason détecte un objet à 10 cm du robot
2. **Transport :** les servomoteurs du bras saisissent l'objet et le déplacent
   d'une position A à une position B
3. **Signal sonore :** le buzzer émet un son pendant 3 secondes une fois la pièce
   déposée en B
4. **Retour au neutre :** le bras revient à sa position initiale après le dépôt
5. **Comptage :** le nombre de pièces déplacées est affiché dans le terminal

**Bonus :**
L'ultrason balaie une zone (par rotation du servo CH1) et s'arrête dès qu'un
objet est détecté. Le robot se positionne, saisit l'objet et le transporte
vers une destination prédéfinie.

---

## Référence rapide des broches

### GPIO Raspberry Pi

| GPIO | Composant | Signal |
|------|-----------|--------|
| GPIO9 | LED1 | Sortie digitale |
| GPIO25 | LED2 | Sortie digitale |
| GPIO11 | LED3 | Sortie digitale |
| GPIO18 | Buzzer | Sortie PWM/tonale |
| GPIO23 | Ultrason HC-SR04 | Trigger (entrée) |
| GPIO24 | Ultrason HC-SR04 | Echo (sortie) |
| GPIO17 | Suiveur ligne S1 | Entrée digitale (capteur droit) |
| GPIO27 | Suiveur ligne S2 | Entrée digitale (capteur milieu) |
| GPIO22 | Suiveur ligne S3 | Entrée digitale (capteur gauche) |

### PCA9685 (adresse I2C 0x5f, fréquence 50 Hz)

| Canal | Destination | Rôle |
|-------|------------|------|
| CH0 | Servo A | Direction des roues |
| CH1 | Servo B | Orientation module ultrason |
| CH2 | Servo C | Coude du bras |
| CH3 | Servo D | Épaule du bras |
| CH4 | Servo E | Pince |
| CH12 | Moteur 2 IN1 | Roue droite, entrée 1 |
| CH13 | Moteur 2 IN2 | Roue droite, entrée 2 |
| CH14 | Moteur 1 IN1 | Roue gauche, entrée 1 |
| CH15 | Moteur 1 IN2 | Roue gauche, entrée 2 |

### Bibliothèques Python utilisées

| Bibliothèque | Usage |
|-------------|-------|
| `gpiozero` | Contrôle haut niveau des GPIO (LED, Buzzer, InputDevice) |
| `RPi.GPIO` | Contrôle bas niveau des GPIO |
| `adafruit_pca9685` | Pilote du contrôleur PWM PCA9685 |
| `adafruit_motor` | Classes DCMotor et Servo |
| `busio` | Bus I2C |
| `board` | Définition des broches SCL/SDA |
