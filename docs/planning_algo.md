Ensemble des calculs mathématiques, pour déplacer le robot d'un point A vers un point B.( module `planner.py` )

---

## Données d'entrée

| Paramètre | Description |
|-----------|-------------|
| $(x_A, y_A)$ | Coordonnées du point de départ A (cm) |
| $(x_B, y_B)$ | Coordonnées du point d'arrivée B (cm) |
| $\theta_{\text{actuel}}$ | Orientation actuelle du robot en degrés (heading, 0° = axe +X) |
| $v_{\text{lin}}$ | Vitesse linéaire du robot (cm/s), issue de `calibration.json` |
| $v_{\text{rot}}$ | Vitesse angulaire du robot (°/s), issue de `calibration.json` |

---

## Étape 1 — Vecteur de déplacement

On calcule d'abord les différences de coordonnées entre B et A :

$$
\Delta x = x_B - x_A
$$

$$
\Delta y = y_B - y_A
$$

---

## Étape 2 — Distance à parcourir

La distance euclidienne entre A et B est :

$$
d = \sqrt{(\Delta x)^2 + (\Delta y)^2}
$$

*En unités : centimètres (cm).*

---

## Étape 3 — Angle cible (cap vers B)

On détermine l'angle absolu que le robot doit avoir pour être orienté vers B. On utilise la fonction `atan2` qui gère tous les quadrants :

$$
\theta_{\text{cible}} = \operatorname{atan2}(\Delta y, \Delta x)
$$

**Conversion en degrés** (car les capteurs et moteurs utilisent des degrés) :

$$
\theta_{\text{cible}}^{\circ} = \theta_{\text{cible}} \times \frac{180}{\pi}
$$

*Résultat entre -180° et +180°.*

---

## Étape 4 — Angle de rotation à effectuer

Le robot doit tourner de la différence entre son orientation actuelle et l'angle cible :

$$
\Delta\theta = \theta_{\text{cible}}^{\circ} - \theta_{\text{actuel}}
$$

---

## Étape 5 — Normalisation de l'angle (optimisation du virage)

Pour que le robot tourne toujours par le chemin le plus court (jamais plus de 180°) :

$$
\Delta\theta_{\text{norm}} = ((\Delta\theta + 180^{\circ}) \bmod 360^{\circ}) - 180^{\circ}
$$

**Interprétation :**
- Si $\Delta\theta_{\text{norm}} > 0$ : tourner à **gauche** (sens trigonométrique / anti-horaire)
- Si $\Delta\theta_{\text{norm}} < 0$ : tourner à **droite** (sens horaire)
- Si $\Delta\theta_{\text{norm}} = 0$ : déjà bien orienté

---

## Étape 6 — Conversion en durées moteur

Grâce aux constantes de calibration, on transforme les grandeurs géométriques en temps de commande moteur.

### Durée de rotation

$$
t_{\text{rot}} = \frac{|\Delta\theta_{\text{norm}}|}{v_{\text{rot}}}
$$

*Unités : secondes (s).*

### Durée d'avance linéaire

$$
t_{\text{avance}} = \frac{d}{v_{\text{lin}}}
$$

*Unités : secondes (s).*

---

## Récapitulatif des formules finales

| Grandeur | Formule |
|----------|---------|
| Écart en X | $\Delta x = x_B - x_A$ |
| Écart en Y | $\Delta y = y_B - y_A$ |
| Distance | $d = \sqrt{\Delta x^2 + \Delta y^2}$ |
| Angle cible | $\theta_{\text{cible}}^{\circ} = \operatorname{atan2}(\Delta y, \Delta x) \times \frac{180}{\pi}$ |
| Rotation requise | $\Delta\theta_{\text{norm}} = ((\theta_{\text{cible}}^{\circ} - \theta_{\text{actuel}} + 180) \bmod 360) - 180$ |
| Temps rotation | $t_{\text{rot}} = \frac{\|\Delta\theta_{\text{norm}}\|}{v_{\text{rot}}}$ |
| Temps avance | $t_{\text{avance}} = \frac{d}{v_{\text{lin}}}$ |

---

## Exemple numérique concret

**Départ A :** $(10, 10)$, orienté à $\theta_{\text{actuel}} = 0^{\circ}$  
**Arrivée B :** $(60, 40)$  
**Calibration :** $v_{\text{lin}} = 20$ cm/s, $v_{\text{rot}} = 36$ °/s

1. $\Delta x = 60 - 10 = 50$ cm
2. $\Delta y = 40 - 10 = 30$ cm
3. $d = \sqrt{50^2 + 30^2} = \sqrt{2500 + 900} = \sqrt{3400} \approx 58.31$ cm
4. $\theta_{\text{cible}} = \operatorname{atan2}(30, 50) \approx 0.5404$ rad $\approx 30.96^{\circ}$
5. $\Delta\theta = 30.96^{\circ} - 0^{\circ} = 30.96^{\circ}$ (déjà normalisé)
6. $t_{\text{rot}} = \frac{30.96}{36} \approx 0.86$ s (rotation gauche)
7. $t_{\text{avance}} = \frac{58.31}{20} \approx 2.92$ s

**Commandes générées :**
- Tourner à gauche pendant **0.86 s**
- Avancer pendant **2.92 s**
- Si le waypoint a `"probe": true` → commande `action` de type `probe` (mesure NPK)
- Si le waypoint a `"photos": N` → commande `action` de type `photo` (N captures)

---

## Nouveaux champs waypoint (map.json)

| Champ | Type | Description |
|-------|------|-------------|
| `probe` | bool | Si `true`, déclenche une mesure NPK (descente capteur → lecture → remontée) |
| `photos` | int | Nombre de photos à prendre du sol à cet arrêt (0 = pas de photo) |

Ces champs remplacent l'ancien champ `action` qui était limité à `"sample"` (prélèvement avec pince, désormais déprécié).

---

## Cas particuliers à gérer dans le code

| Situation | Traitement |
|-----------|------------|
| $d = 0$ | Le point B est identique à A : aucun déplacement, uniquement l'action (mesure NPK + photo) |
| $\Delta\theta_{\text{norm}} = 0$ | Pas de rotation nécessaire, avancer directement |
| $\Delta\theta_{\text{norm}} = \pm 180^{\circ}$ | Demi-tour : le sens (gauche/droite) est indifférent, choisir arbitrairement |
| Points alignés sur un axe | `atan2` gère correctement ($\Delta x = 0$ ou $\Delta y = 0$) |






------------
Ensemble des calculs mathématiques, pour déplacer le robot d'un point A vers un point B.( module `planner.py` )

---

## Données d'entrée

| Paramètre | Description |
|-----------|-------------|
| $(x_A, y_A)$ | Coordonnées du point de départ A (cm) |
| $(x_B, y_B)$ | Coordonnées du point d'arrivée B (cm) |
| $\theta_{\text{actuel}}$ | Orientation actuelle du robot en degrés (heading, 0° = axe +X) |
| $v_{\text{lin}}$ | Vitesse linéaire du robot (cm/s), issue de `calibration.json` |
| $v_{\text{rot}}$ | Vitesse angulaire du robot (°/s), issue de `calibration.json` |

---

## Étape 1 — Vecteur de déplacement

On calcule d'abord les différences de coordonnées entre B et A :

$$
\Delta x = x_B - x_A
$$

$$
\Delta y = y_B - y_A
$$

---

## Étape 2 — Distance à parcourir

La distance euclidienne entre A et B est :

$$
d = \sqrt{(\Delta x)^2 + (\Delta y)^2}
$$

*En unités : centimètres (cm).*

---

## Étape 3 — Angle cible (cap vers B)

On détermine l'angle absolu que le robot doit avoir pour être orienté vers B. On utilise la fonction `atan2` qui gère tous les quadrants :

$$
\theta_{\text{cible}} = \operatorname{atan2}(\Delta y, \Delta x)
$$

**Conversion en degrés** (car les capteurs et moteurs utilisent des degrés) :

$$
\theta_{\text{cible}}^{\circ} = \theta_{\text{cible}} \times \frac{180}{\pi}
$$

*Résultat entre -180° et +180°.*

---

## Étape 4 — Angle de rotation à effectuer

Le robot doit tourner de la différence entre son orientation actuelle et l'angle cible :

$$
\Delta\theta = \theta_{\text{cible}}^{\circ} - \theta_{\text{actuel}}
$$

---

## Étape 5 — Normalisation de l'angle (optimisation du virage)

Pour que le robot tourne toujours par le chemin le plus court (jamais plus de 180°) :

$$
\Delta\theta_{\text{norm}} = ((\Delta\theta + 180^{\circ}) \bmod 360^{\circ}) - 180^{\circ}
$$

**Interprétation :**
- Si $\Delta\theta_{\text{norm}} > 0$ : tourner à **gauche** (sens trigonométrique / anti-horaire)
- Si $\Delta\theta_{\text{norm}} < 0$ : tourner à **droite** (sens horaire)
- Si $\Delta\theta_{\text{norm}} = 0$ : déjà bien orienté

---

## Étape 6 — Conversion en durées moteur

Grâce aux constantes de calibration, on transforme les grandeurs géométriques en temps de commande moteur.

### Durée de rotation

$$
t_{\text{rot}} = \frac{|\Delta\theta_{\text{norm}}|}{v_{\text{rot}}}
$$

*Unités : secondes (s).*

### Durée d'avance linéaire

$$
t_{\text{avance}} = \frac{d}{v_{\text{lin}}}
$$

*Unités : secondes (s).*

---

## Récapitulatif des formules finales

| Grandeur | Formule |
|----------|---------|
| Écart en X | $\Delta x = x_B - x_A$ |
| Écart en Y | $\Delta y = y_B - y_A$ |
| Distance | $d = \sqrt{\Delta x^2 + \Delta y^2}$ |
| Angle cible | $\theta_{\text{cible}}^{\circ} = \operatorname{atan2}(\Delta y, \Delta x) \times \frac{180}{\pi}$ |
| Rotation requise | $\Delta\theta_{\text{norm}} = ((\theta_{\text{cible}}^{\circ} - \theta_{\text{actuel}} + 180) \bmod 360) - 180$ |
| Temps rotation | $t_{\text{rot}} = \frac{\|\Delta\theta_{\text{norm}}\|}{v_{\text{rot}}}$ |
| Temps avance | $t_{\text{avance}} = \frac{d}{v_{\text{lin}}}$ |
