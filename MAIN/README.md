# Projet_Learning_By_Doing_G31

## Description du robot: (s'en baser ds le cas de necessite d'infos supplementaires)
Informations  sur le **robot Adeept PiCar Pro V2.0** disponible au Maroc :

## 📍 Disponibilité au Maroc

Le PiCar Pro V2 est vendu au Maroc chez **Electronique Morocco** (site web marocain) au prix de **1 900 DH**. [electroniquemorocco](https://electroniquemorocco.com/index.php?route=product%2Fproduct&product_id=656)

## 🔧 Caractéristiques principales

| catégorie | détails |
|-----------|---------|
| **Type** | Voiture robot intelligente 2-en-1 : châssis 4WD + bras robotique 4-DOF  [electroniquemorocco](https://electroniquemorocco.com/index.php?route=product%2Fproduct&product_id=656) |
| **Compatible** | Raspberry Pi 5, 4B, 3B+, 3B (**Pi non inclus**)  [fr.aliexpress](https://fr.aliexpress.com/i/1005002610457149.html) |
| **Caméra** | USB 1080P HD pour projets AI/OpenCV  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **Châssis** | Alliage d'aluminium  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **Bras robotique** | 4 degrés de liberté (4-DOF) en acrylique  [fr.aliexpress](https://fr.aliexpress.com/i/1005002610457149.html) |
| **Carte de contrôle** | Adeept Robot HAT V3.2 (driver moteur + contrôleur servo)  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **Batterie** | 7.4V, charge via USB-C (câble inclus)  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **Capteurs** | Ultrasons, suivi de ligne IR, détecteurs divers  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **Moteurs** | 4 moteurs DC (4WD) + servomoteurs pour le bras  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **LEDs** | 12 LED RGB WS2812 pour feedback visuel  [galaxus](https://www.galaxus.ch/en/s1/product/adeept-picar-pro-raspberry-pi-smart-robot-car-kit-robotics-kit-46448826) |

## 🚀 Fonctionnalités AI/Robotique

- **Reconnaissance d'objets** basée sur OpenCV [aytoo](https://aytoo.ma/produit/robot-educatif-adeept-picar-b-voiture-intelligente-pour-raspberry-pi/)
- **Suivi d'objets** (forme/couleur spécifique) [aytoo](https://aytoo.ma/produit/robot-educatif-adeept-picar-b-voiture-intelligente-pour-raspberry-pi/)
- **Suivi de ligne** par réflexion infrarouge [aytoo](https://aytoo.ma/produit/robot-educatif-adeept-picar-b-voiture-intelligente-pour-raspberry-pi/)
- **Évitement automatique d'obstacles** (capteur ultrason) [aytoo](https://aytoo.ma/produit/robot-educatif-adeept-picar-b-voiture-intelligente-pour-raspberry-pi/)
- **Transmission vidéo en temps réel** [aytoo](https://aytoo.ma/produit/robot-educatif-adeept-picar-b-voiture-intelligente-pour-raspberry-pi/)
- **Reconnaissance vocale** (commandes vocales) [aytoo](https://aytoo.ma/produit/robot-educatif-adeept-picar-b-voiture-intelligente-pour-raspberry-pi/)
- **Contrôle** : Python/GPIO + interface web [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E)

## ⚠️ Points importants

| à savoir | détail |
|----------|--------|
| **Assemblage requis** | Pièces détachées, montage DIY nécessaire  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **Raspberry Pi** | **NON inclus** – à acheter séparément  [fr.aliexpress](https://fr.aliexpress.com/i/1005002610457149.html) |
| **Batteries 18650** | NON incluses  [galaxus](https://www.galaxus.ch/en/s1/product/adeept-picar-pro-raspberry-pi-smart-robot-car-kit-robotics-kit-46448826) |
| **Compétences requises** | Électronique basique (soudure non nécessaire)  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |
| **Tutoriels** | inclus (PDF + code Python open-source)  [youtube](https://www.youtube.com/watch?v=j9Q5xvUMl9E) |

## 🎯 Usage recommandé

- Éducation STEM et apprentissage Python [adeept](https://www.adeept.com/picar-pro_p0246.html)
- Projets AI/OpenCV et robotique avancée [fr.aliexpress](https://fr.aliexpress.com/i/1005002610457149.html)
- Pour adolescents et adultes (DIY électronique) [galaxus](https://www.galaxus.ch/en/s1/product/adeept-picar-pro-raspberry-pi-smart-robot-car-kit-robotics-kit-46448826)
- Développement de compétences en cinématique robotique et fusion de capteurs [youtube](https://www.youtube.com/watch?v=VbwkWI6Wkw0)

##Fonctionnement du robot autonome


## Vue globale

Le projet fonctionne en deux grandes étapes :

1. **Préparation avant la démonation**
2. **Exécution autonome pendant la démonation**

L’idée est simple :
on prépare une carte du terrain et les paramètres du robot à l’avance, puis le robot suit automatiquement les points de prélèvement pendant la démo.

---

# 1. Préparation avant la démonstration

Cette partie se fait une seule fois sur le PC.

---

## Étape 1 — Définir la carte du terrain

On mesure les positions des points de prélèvement sur la table.

Chaque position est définie par des coordonnées `(x, y)` en centimètres, en prenant comme référence le point de départ du robot.

Toutes ces informations sont enregistrées dans `map.json`.

Exemple :

```json
{
  "table": {"width_cm": 150, "height_cm": 100},

  "start": {
    "x": 10,
    "y": 10,
    "heading_deg": 0
  },

  "waypoints": [
    {
      "id": 1,
      "x": 60,
      "y": 40,
      "action": "sample"
    },

    {
      "id": 2,
      "x": 120,
      "y": 70,
      "action": "sample"
    }
  ]
}
```

Ici :

* le robot démarre en `(10,10)`
* il doit aller au point 1
* effectuer un prélèvement
* puis aller au point 2
* effectuer un autre prélèvement

---

## Étape 2 — Calibration du robot

Le robot ne connaît pas naturellement :

* combien de centimètres il parcourt par seconde
* combien de degrés il tourne par seconde

On mesure donc ces valeurs expérimentalement sur le vrai terrain.

Les résultats sont stockés dans `calibration.json`.

Exemple :

```json
{
  "cm_per_sec": 20,
  "deg_per_sec": 36
}
```

Cela signifie par exemple :

* avance de 20 cm en 1 seconde
* rotation de 36° en 1 seconde

Ces constantes permettront de transformer une distance ou un angle en temps moteur.

---

## Étape 3 — Génération automatique du plan de déplacement

Le fichier `planner.py` lit :

* la carte (`map.json`)
* les constantes de calibration (`calibration.json`)

Puis il calcule automatiquement :

* les angles à tourner
* les distances à parcourir
* les durées exactes des mouvements

Exemple :

### Départ → Point 1

Le programme calcule :

* tourner de 32°
* avancer de 55 cm

Avec la calibration :

* rotation gauche pendant 0.88 s
* avance pendant 2.75 s

Puis :

* arrêt
* prélèvement

---

### Point 1 → Point 2

Le programme calcule :

* rotation droite de 18°
* avance de 72 cm

Donc :

* rotation pendant 0.5 s
* avance pendant 3.6 s

Puis :

* arrêt
* prélèvement

---

# 2. Démonstration autonome

Pendant la démonstration, il suffit :

1. de poser le robot au point de départ
2. de lancer :

```bash
python main.py
```

Ensuite tout est automatique.

Le robot va :

1. se tourner vers le premier point
2. avancer jusqu’au point
3. s’arrêter précisément
4. effectuer le prélèvement avec le bras
5. repartir vers le point suivant
6. refaire l’opération
7. éventuellement revenir au point de départ

Aucune intervention humaine n’est nécessaire pendant l’exécution.

---

# Organisation des fichiers

```text
picar-agri/
├── map.json
├── calibration.json
├── planner.py
├── executor.py
├── arm.py
└── main.py
```

---

# Rôle de chaque fichier

## `map.json`

Contient :

* les dimensions du terrain
* la position de départ
* les points de prélèvement

C’est la “carte” du robot.

---

## `calibration.json`

Contient les constantes mesurées :

* vitesse d’avance
* vitesse de rotation

Ces valeurs permettent au robot de convertir une distance en durée moteur.

---

## `planner.py`

C’est le module de planification.

Il calcule :

* où tourner
* combien avancer
* combien de temps exécuter chaque mouvement

Il transforme la carte en une suite d’ordres exploitables par le robot.

---

## `executor.py`

C’est le module d’exécution.

Il reçoit des commandes comme :

```python
{"type": "forward", "duration": 2.75}
```

et contrôle directement les moteurs pendant le temps demandé.

---

## `arm.py`

Contrôle le bras robotique.

La séquence de prélèvement est prédéfinie :

```text
descendre → pause → remonter
```

C’est la partie visible et démonstrative du projet.

---

## `main.py`

C’est le point d’entrée principal.

Il coordonne tout le système.

Exemple simplifié :

```python
plan = planner.generate("map.json", "calibration.json")

for command in plan:
    executor.run(command)
```

---

# Résultat final visible pendant la démo

Le jury voit un robot qui :

* démarre seul
* se déplace vers plusieurs points du terrain
* s’arrête avec précision
* effectue automatiquement un prélèvement avec son bras
* repart vers le point suivant
* termine sa mission sans intervention humaine

Le comportement donne l’impression d’un système agricole autonome miniature.
