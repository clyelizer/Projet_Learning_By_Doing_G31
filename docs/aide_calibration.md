# Aide à la calibration

Guide pas à pas pour calibrer les paramètres de déplacement du robot  
à l'aide des fichiers de test dans `tests/`.

---

## Prérequis

- Robot posé sur une **surface plane et dégagée**
- Batterie chargée
- Connexion SSH ou terminal sur le Pi
- `calibration.json` ouvert dans un éditeur pour reporter les valeurs

```bash
cd ~/Projet_Learning_By_Doing_G31
nano config/calibration.json   # ou vim, ou vs code
```

---

## 1. Centrage des roues — `test_steering.py`

**Objectif** : vérifier qu'à `center_deg`, les roues sont parfaitement droites.

```bash
python tests/test_steering.py
```

Le script braque les roues à 90° (ou la valeur configurée).  
👉 Si les roues ne sont pas droites, **ajuste `center_deg`** dans `calibration.json` (essaye 85, 88, 92, 95°).

Puis il teste les angles max gauche/droite :  
👉 Si le servo **grince**, réduis `max_left_deg` ou `max_right_deg`.

---

## 2. Angles max précis — `test_steering_diag.py`

**Objectif** : trouver le vrai débattement max sans forcer le servo.

```bash
python tests/test_steering_diag.py
```

Le servo bouge de 5° en 5° vers la gauche, puis vers la droite.  
👉 **Dès que ça grince**, l'angle précédent est le max pour ce côté.

Reporte les valeurs trouvées dans :
- `steering.max_left_deg`
- `steering.max_right_deg`

---

## 3. Décoincement après virage droit — `test_steering_return.py`

**Objectif** : valider le correctif mécanique du lien de direction.

```bash
python tests/test_steering_return.py
```

Séquence : droite max → gauche (centre-50°) → centre.  
👉 Si les roues sont droites à la fin, `center_after_right_turn()` fonctionne.

Ce correctif est **déjà intégré** dans `stop_all()` et `rest_position()`.

---

## 4. Vitesse linéaire — `test_speed_forward.py`

**Objectif** : mesurer `cm_per_sec` (combien de cm le robot parcourt en 1 seconde).

```bash
python tests/test_speed_forward.py
```

1. Marque une **ligne de départ** au sol
2. Le robot avance pendant **2 secondes**
3. Tu mesures la **distance parcourue** en cm
4. Le calcul : `cm_per_sec = distance / 2`

**Exemple** : 16 cm en 2s → `cm_per_sec = 8`

Reporte la valeur dans `calibration.json`.

---

## 5. Vitesse de rotation — `test_turn_rate.py`

**Objectif** : mesurer `deg_per_sec` (combien de degrés le robot tourne en 1 seconde).

```bash
python tests/test_turn_rate.py
```

1. Dégage l'espace devant le robot
2. Le robot tourne à **gauche** pendant **2 secondes**
3. Tu estimes l'**angle parcouru** (90° = quart de tour, 180° = demi-tour, 360° = complet)
4. Le calcul : `deg_per_sec = angle / 2`

**Exemple** : 90° en 2s → `deg_per_sec = 45`

Reporte la valeur dans `calibration.json`.

---

## 6. Test final — `test_rest_position.py`

**Objectif** : vérifier que tout s'arrête correctement.

```bash
python tests/test_rest_position.py
```

Le robot avance 0.5s puis appelle `rest_position()`.  
👉 Vérifie : moteurs arrêtés, roues droites, bras en position neutre.

---

## Résumé des paramètres

| Paramètre | Fichier | Test |
|---|---|---|
| `steering.center_deg` | `calibration.json` | `test_steering.py` |
| `steering.max_left_deg` | `calibration.json` | `test_steering_diag.py` |
| `steering.max_right_deg` | `calibration.json` | `test_steering_diag.py` |
| `cm_per_sec` | `calibration.json` | `test_speed_forward.py` |
| `deg_per_sec` | `calibration.json` | `test_turn_rate.py` |
| `throttle_forward` | `calibration.json` | Ajuster + refaire `test_speed_forward` |

---

## Exemple de résultat final

```json
{
  "throttle_forward": 0.3,
  "throttle_backward": 0.2,
  "cm_per_sec": 8,
  "deg_per_sec": 15,
  "steering": {
    "center_deg": 100,
    "max_left_deg": 40,
    "max_right_deg": 160
  }
}
```
