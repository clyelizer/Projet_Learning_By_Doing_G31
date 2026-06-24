# TODO — AgroScan

## Court terme

- [x] Robot Doctor : diagnostic 12 tests + auto-healing intégré au dashboard
- [ ] **Tester le Doctor sur le Pi** :
  - [ ] `i2cdetect -y 1` → PCA9685 0x5f détecté
  - [ ] Impulsions moteurs OK (sans roues)
  - [ ] Balayage servo direction OK
  - [ ] `libcamera-still --list-cameras` → caméra détectée
  - [ ] Port série Arduino (/dev/ttyACM0) accessible
  - [ ] 15 modèles .pkl lisibles
  - [ ] Analyse LLM via Qwen Code (optionnel)
- [ ] Tester le pipeline complet sur le Pi (vérifier les 4 bugs corrigés)
- [ ] Vérifier calibration capteurs (pH, EC) sur le terrain

## Moyen terme

- [ ] **Refonte UX agriculteur** : interface trop technique/developeur, pas adaptée à un agriculteur ou non-initié. Revoir le design, les libellés, les explications, le parcours utilisateur pour le rendre accessible au terrain
- [ ] Ajouter un mode "replay" dans le dashboard (voir l'historique des missions)
- [ ] Améliorer les graphiques d'impact SHAP dans la page Test analyse
- [ ] Ajouter l'export PDF des recommandations
- [ ] Notification push sur WhatsApp à la fin d'une mission

## Long terme

- [ ] Implémenter l'évitement d'obstacles (VFH+) avec l'ultrason
- [ ] Base de données persistante (SQLite/PostgreSQL) pour l'historique
- [ ] Apprentissage automatique continu (retraining avec les nouvelles données terrain)
- [ ] Mode multi-robot / flotte
- [ ] Interface mobile native (iOS/Android)
