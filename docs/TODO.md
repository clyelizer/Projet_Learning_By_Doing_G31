# TODO — Projet Robot 2WD + Bras + Capteur Sol + Vision

## Documentation
- [ ] renommer tous les .md avec des noms clairs
- [ ] reprendre correctement tous les .md (ce sont des brouillons)
- [ ] ajouter les images au .md présentant le robot
- [ ] mettre à jour `MD/Planning.md` avec les nouveaux champs waypoint

## Évitement (VFH+)
- [ ] décider emplacement : dans MAIN/ ou dossier séparé ?
- [ ] implémenter le sweep ultrason + VFH+
- [ ] implémenter la FSM orchestrateur

## Base de données
- [ ] rechercher/choisir la solution DB
- [ ] intégrer les résultats capteur dans la DB

## Nouvelle Architecture — Implémentation

### Phase 1 : Modules de base
- [ ] Réécrire `MAIN/cam.py` → `MAIN/camera.py` (corriger bugs: import guard, chemin relatif, fallback)
- [x] Créer `src/sensor_arduino.py` (Arduino + MAX485 bridge, port `/dev/ttyACM0`)
- [ ] Modifier `MAIN/arm.py` (remplacer pince par fonctions `lower_probe()` / `raise_probe()`)

### Phase 2 : Pipeline
- [ ] Simplifier `MAIN/executor.py` (retirer `import arm`, mouvement uniquement)
- [ ] Étendre `MAIN/planner.py` (nouveaux champs waypoint: `probe`, `photos`)
- [ ] Créer `MAIN/image_processor.py` (pipeline asynchrone, placeholder modèle IA)
- [ ] Créer `MAIN/data_logger.py` (agrégation JSON des données mission)

### Phase 3 : Orchestration
- [ ] Restructurer `MAIN/main.py` (nouveau pipeline: plan → mouvement → probe → photo → log → process)
- [ ] Étendre `Config/map.json` (champs `probe` et `photos` par waypoint)
- [ ] Étendre `Config/calibration.json` (constantes caméra, capteur)

### Phase 4 : Tests
- [ ] Tester chaque module individuellement (`if __name__ == '__main__'`)
- [ ] Tester le pipeline complet en mode dry-run
- [ ] Tester avec hardware (Pi + robot)
