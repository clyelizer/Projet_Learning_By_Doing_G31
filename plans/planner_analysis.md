# Rapport d'analyse — Planner (`src/planner.py`)

Exécuté le 2026-06-13 avec `config/map.json` et `config/calibration.json`.

---

## 1. Plan généré (12 commandes)

| # | Type | Détail | Durée |
|---|------|--------|-------|
| 1 | ROTATION LEFT | 38.66° | 2.58 s |
| 2 | AVANCE | 64.03 cm | 4.27 s |
| 3 | PROBE | Waypoint 1 (50, 40) | — |
| 4 | PHOTO (x2) | Waypoint 1 | — |
| 5 | ROTATION LEFT | 77.91° | 5.19 s |
| 6 | AVANCE | 44.72 cm | 2.98 s |
| 7 | PROBE | Waypoint 2 (30, 80) | — |
| 8 | PHOTO (x2) | Waypoint 2 | — |
| 9 | ROTATION RIGHT | 100.62° | 6.71 s |
| 10 | AVANCE | 72.80 cm | 4.85 s |
| 11 | PROBE | Waypoint 2 (100, 100) | — |
| 12 | PHOTO (x2) | Waypoint 2 | — |

**Temps total estimé :** ~26.6 s de mouvement + actions (probe ~1.5s × 3, photos ~0.5s × 6).

---

## 2. Trajectoire vérifiée (mathématiquement correcte)

```
Départ (0, 0) heading 0°
  │
  ├─[1]─► (50, 40)   dist=64.03 cm  angle=38.66°
  │
  ├─[2]─► (30, 80)   dist=44.72 cm  angle=116.57°
  │
  └─[3]─► (100,100)  dist=72.80 cm  angle=15.95°
```

Tous les calculs `atan2` + `normalize_angle` sont exacts. La règle « tourner par le chemin le plus court » est respectée (ex: 100.62° RIGHT au lieu de 259.38° LEFT).

---

## 3. Qualité du code

### Points positifs
- `normalize_angle()` choisit toujours le virage le plus court ([-180°, +180°])
- Seuils de 0.5° et 0.5 cm évitent les micro-commandes inutiles
- Rétrocompatibilité avec l'ancien champ `action`
- Sortie lisible via `print_plan()`

### Améliorations possibles
| # | Fichier | Ligne | Problème |
|---|---------|-------|----------|
| 1 | `planner.py` | 135 | `current_heading = move['target_angle_deg']` ne tient pas compte qu'une rotation < 0.5° est ignorée → dérive angulaire max 0.5° par waypoint |
| 2 | `planner.py` | 73 | Aucune validation des IDs de waypoints (doublons non détectés) |
| 3 | `planner.py` | 87-136 | Pas de vérification que les waypoints sont dans la zone `table` |
| 4 | `planner.py` | 12-15 | `load_json` ne fait que `open/load` — pas de vérification de schéma |

---

## 4. Problèmes dans les fichiers de configuration

### 🔴 `config/map.json` — IDs dupliqués

```json
{"id": 2, "x": 30, "y": 80, ...},   // waypoint 2
{"id": 2, "x": 100, "y": 100, ...}   // waypoint 3 ← MÊME ID !
```

Les étapes 7, 8, 11, 12 rapportent toutes `Waypoint ID: 2`. Dans `data_logger.py`, `log_waypoint()` écrase les données du waypoint 2 avec celles du waypoint 3. **À corriger :** mettre `"id": 3` pour le 3ᵉ waypoint.

### 🟡 `config/calibration.json`

- `motor_speed: 0.1` → seulement 10% de puissance PWM. Le robot sera très lent.
- `photo_count: 0` → inoffensif ici car les waypoints spécifient `photos: 2`, mais ce champ n'est utilisé que comme fallback dans `main.py`.

---

## 5. Algorithme pas à pas

```
generate_plan(map_file, calib_file)
  │
  ├─ load map.json   → start (x,y,heading) + waypoints[]
  ├─ load calib.json → cm_per_sec, deg_per_sec
  │
  └─ for each waypoint:
       │
       ├─ calculate_movement(pos_actuelle, wp, heading_actuel)
       │    ├─ delta = (dx, dy)
       │    ├─ distance = √(dx² + dy²)
       │    ├─ angle_cible = atan2(dy, dx)
       │    ├─ rotation = normalize(angle_cible − heading)
       │    └─ direction = left si rotation ≥ 0, sinon right
       │
       ├─ if |rotation| > 0.5°  → ajouter commande ROTATE
       ├─ if distance > 0.5 cm  → ajouter commande FORWARD
       ├─ if probe  → ajouter commande PROBE
       ├─ if photos > 0 → ajouter commande PHOTO
       │
       └─ mise à jour : pos = wp, heading = angle_cible
```

---

## 6. Conclusion

Le planneur est **mathématiquement correct** et produit une trajectoire valide. Les 2 problèmes à corriger :

1. **🔴 Critique** : `config/map.json` — changer `"id": 2` en `"id": 3` pour le 3ᵉ waypoint
2. **🟡 Mineur** : Ajouter une validation d'unicité des IDs dans `generate_plan()`
