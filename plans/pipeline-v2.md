# Pipeline V2 — Plan d'Architecture

> Date: 2026-06-17 | À valider avant implémentation

---

## 1. Vue d'Ensemble

```
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌─────────────────┐
│  main.py │───▶│  mission │───▶│   data/      │───▶│  web/app.py     │
│ (orchest-│    │ (exec,   │    │ results.json │    │ (Flask dashboard│
│  rateur) │    │  arm,    │    │ + photos/    │    │  auto-launch)   │
│          │    │  sensor, │    └──────┬───────┘    └────────┬────────┘
│          │    │  camera) │          │                     │
└──────────┘    └──────────┘          ▼                     ▼
                                ┌──────────────┐    ┌──────────────┐
                                │ vlm_analyzer │    │  reco_engine │
                                │ (Gemini→Groq)│    │ (Groq LLM)  │
                                └──────┬───────┘    └──────┬───────┘
                                       │                    │
                                       ▼                    ▼
                                ┌──────────────────────────────────┐
                                │         data/results.json       │
                                │  + soil_analysis (VLM)          │
                                │  + recommendations (LLM)        │
                                └──────────────┬───────────────────┘
                                               │
                                               ▼
                                ┌──────────────────────────────┐
                                │         web/app.py          │
                                │  /  /data  /reco  /chat    │
                                │  + TTS endpoint             │
                                │  + chat bubble (coin)       │
                                └──────────────────────────────┘
```

---

## 2. Modules à Créer / Modifier

### 2.1 `src/image_preprocessor.py` (NOUVEAU — renommé de image_processor)

**Philosophie :** Learning by doing — développer nos propres fonctions manuelles de vision classique, ET fournir des fonctions avancées avec bibliothèques établies. Deux modes au choix via paramètre `method='manual'|'advanced'`. Cela permet d'étudier en profondeur les deux approches : comprendre ce qu'on code à la main, puis observer comment les librairies optimisées font mieux.

**Fonctions manuelles (implémentées par nous-mêmes) :**
```python
def rgb_to_hsv_manual(img) -> tuple         # Conversion RGB→HSV sans OpenCV
def grayscale_manual(img) -> ndarray        # Moyenne pondérée (0.299R + 0.587G + 0.114B)
def histogram_manual(img, bins=256) -> dict  # Calcul d'histogramme from scratch
def threshold_otsu_manual(img) -> float     # Algorithme d'Otsu implémenté à la main
def sobel_edges_manual(img) -> ndarray      # Détection de contours Sobel sans librairie
def glcm_manual(img, dist=1, angle=0)       # Matrice de co-occurrence codée nous-mêmes
def haralick_manual(glcm) -> dict           # Calcul des features Haralick sans scikit
def laplacian_var_manual(img) -> float      # Variance Laplacian from scratch
def exg_vegetation_manual(img) -> float     # Excess Green index implémenté main
```

**Fonctions avancées (bibliothèques optimisées) :**
```python
def extract_features_advanced(img) -> dict  # Pipeline complet via OpenCV + skimage
def segment_soil_advanced(img) -> ndarray   # Segmentation via GrabCut / Watershed
def texture_advanced(img) -> dict           # GLCM + LBP + Gabor filters via skimage
def quality_check_advanced(img) -> dict     # Sharpness + BRISQUE score
def color_analysis_advanced(img) -> dict    # CIELAB ΔE + histogrammes multi-canal
```

**Fonction unifiée (dispatcher) :**
```python
def extract_features(img, method='manual') -> dict:
    """
    Extrait toutes les features d'une image de sol.
    method='manual'  → nos propres implémentations (learning by doing)
    method='advanced' → OpenCV/scikit-image optimisées (production)
    """
```

**Méthodologie d'étude :**
1. Coder chaque fonction manuelle en s'appuyant sur la littérature (refs dans `methodes-preprocessing.md`)
2. Comparer les résultats numériques manuel vs advanced (doivent correspondre à ±1% près)
3. Mesurer les performances (temps d'exécution) des deux approches
4. Documenter les écarts et expliquer POURQUOI l'approche avancée est plus rapide (vectorisation, SIMD, code C sous-jacent)

Le module expose `extract_features()` qui retourne un dict structuré utilisé par le VLM en complément de l'image.

### 2.2 `src/reco_engine.py` (NOUVEAU)

Moteur de recommandations agricoles. Architecture évolutive en 2 phases.

**Phase 1 (maintenant) :** envoie les mesures brutes à Groq/Llama.
```python
def recommend(sensor_data, image_analysis=None) -> dict
```
Envoie au LLM : humidité, température, EC, pH + analyse visuelle. Retourne :
```json
{
  "crops": ["riz", "mil", "arachide"],
  "fertilizer": "NPK 15-15-15 à 200 kg/ha",
  "soil_amendments": ["compost", "chaux"],
  "irrigation": "2 fois/semaine, 5mm",
  "warnings": ["pH trop élevé — sol alcalin"],
  "confidence": 0.85
}
```

**Phase 2 (futur) :** enrichit avec une base de données locale.
```
DB (cultures, sols, fertilisants) → lookup initial → + mesures → LLM → reco finale
```
La DB sera une table SQLite/Fichier CSV avec colonnes étiquetées :
- `soil_type`, `ph_min`, `ph_max`, `ec_min`, `ec_max`, `humidity_min`, `humidity_max`
- `crop_name`, `fertilizer_type`, `fertilizer_rate`, `irrigation_freq`
→ `reco_engine` interroge d'abord la DB, puis passe le résultat ET les mesures au LLM.

### 2.3 `src/tts_engine.py` (NOUVEAU)

Synthèse vocale multi-moteur.

```python
def speak(text, engine='auto', lang='fr') -> str  # retourne path fichier audio
def get_available_engines() -> list
def get_available_languages(engine) -> list
```

Moteurs :
| Moteur | Type | Installation |
|--------|------|-------------|
| **espeak-ng** | Offline (local) | `sudo apt install espeak-ng` |
| **piper** | Offline (local, neural) | `pip install piper-tts` + modèles |
| **elvenlabs** | Online (API) | `pip install elevenlabs` + clé |

Configuration dans `config/config.json` :
```json
{
  "tts": {
    "engine": "espeak-ng",
    "language": "fr",
    "offline_fallback": true
  },
  "languages": {
    "fr": "Français",
    "en": "English",
    "bm": "Bamanankan (Bambara)",
    "ar": "العربية (Arabe)",
    "wo": "Wolof",
    "ff": "Fulfulde",
    "ha": "Hausa"
  }
}
```

### 2.4 `src/web/app.py` — Refonte

**Suppression des templates Jinja** → données servies en JSON, rendu côté client (fetch API).

Routes :
| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | SPA dashboard (unique page HTML+JS) |
| `/api/results` | GET | `results.json` complet |
| `/api/recommendations` | GET | Recos générées par reco_engine |
| `/api/chat` | POST | Chat IA (contexte mesures + images) |
| `/api/tts` | POST | Synthèse vocale d'un texte |
| `/api/tts/replay/<lang>` | GET | Rejoue la dernière reco |
| `/photos/<filename>` | GET | Sert les photos |

**Chat bubble :**
- **Icône :** 💬 flottante, fixe en bas à droite de l'écran (`position: fixed; bottom: 20px; right: 20px`)
- **Design :** Bouton rond (56×56px), vert agricole (`#2e7d32`), ombre portée, badge pulsé si nouveau message non lu
- **États :**
  - *Fermé* → icône 💬 seule, discrète
  - *Ouvert* → panneau de chat 380×500px qui remonte du coin, l'icône devient ✕ pour fermer
  - *Notification* → petit point rouge (badge) si l'IA a répondu et que l'utilisateur n'a pas encore vu
- **Fenêtre de chat :**
  - Header : "🌱 Assistant Agricole" + bouton ✕
  - Body : zone de messages (scrollable), bulles style messagerie
  - Footer : input text + bouton envoyer ➤
  - Les messages de l'IA arrivent en streaming (mot par mot) si l'API le supporte
- **Modèle IA :** **Groq + Llama 3.1 8B** (`llama-3.1-8b-instant`) — ~14 400 requêtes/jour de quota gratuit, latence < 1s
- **Fallback :** si Groq down → Gemini 2.0 Flash

**Prompt système du chat :**
```
Tu es un expert agronome spécialisé en agriculture africaine (Sahel, zones tropicales).
Tu as accès aux données de mesure du sol suivantes :
{results_json}

Tu as aussi les analyses visuelles des photos du sol :
{vlm_analysis}

Et les recommandations générées automatiquement :
{reco_json}

Règles :
- Réponds en {language} (langue configurée).
- Sois concis mais complet. Utilise des termes simples compréhensibles par un agriculteur.
- Base-toi UNIQUEMENT sur les données fournies. Ne pas inventer de valeurs.
- Si une question sort du contexte agricole, réponds poliment que tu es spécialisé en agriculture.
- Suggère des cultures adaptées au type de sol mesuré.
- Mentionne les risques (pH extrême, salinité, sécheresse) si pertinent.
```

### 2.5 `src/main.py` — Modifications

Ajouts :
1. **Lancement auto du dashboard** : vérifie si Flask tourne (`pgrep`), sinon le lance en sous-processus.
2. **Pipeline complet** : après `image_processor.enqueue()`, appelle `vlm_analyzer.analyze_soil_ia()`.
3. **Recommandations** : après mesures, appelle `reco_engine.recommend()`.
4. **TTS** : après reco, appelle `tts_engine.speak()` → joue l'audio sur le haut-parleur du Pi.
5. **Sauvegarde enrichie** : `results.json` inclut maintenant `vlm_analysis`, `recommendations`, `tts_audio_path`.

Pseudo-code ajouté dans main.py :
```python
# Après mission
if not _is_flask_running():
    subprocess.Popen(['python', 'web/app.py'])

# Pour chaque waypoint avec photos:
vlm_result = vlm_analyzer.analyze_soil_ia(photo_path)
data_logger.attach_vlm(wp_id, vlm_result)

# Recommandations
reco = reco_engine.recommend(sensor_data, vlm_result)
data_logger.attach_reco(wp_id, reco)

# TTS
audio = tts_engine.speak(reco['summary'], lang=tts_config['language'])
data_logger.attach_audio(wp_id, audio)
```

---

## 3. Structure des Fichiers

```
src/
├── main.py                  ← orchestrateur (modifié)
├── executor.py              ← (inchangé)
├── arm.py                   ← (inchangé, sauf prints "NPK" → nettoyés)
├── sensor_arduino.py        ← (inchangé)
├── camera.py                ← (inchangé)
├── image_preprocessor.py    ← NOUVEAU (renommé de image_processor)
├── vlm_analyzer.py          ← (inchangé)
├── reco_engine.py           ← NOUVEAU
├── tts_engine.py            ← NOUVEAU
├── data_logger.py           ← modifié (nouveaux champs)
├── planner.py               ← (inchangé)
├── web/
│   ├── app.py               ← refondu (SPA, JSON API)
│   └── static/
│       ├── style.css         ← mis à jour (chat bubble, responsive)
│       ├── app.js            ← NOUVEAU (SPA vanilla JS)
│       └── chat.js           ← NOUVEAU (chat bubble logic)
│   └── templates/            ← SUPPRIMÉ (plus de Jinja)

config/
├── config.json              ← NOUVEAU (TTS, langues, chat config)
├── map.json                 ← (inchangé)
├── calibration.json         ← (photo_count supprimé)
└── crops_db.json            ← NOUVEAU (Phase 2 — base cultures/sols)

data/
├── photos/                  ← (inchangé)
├── results.json             ← enrichi: vlm_analysis, recommendations, tts_audio
└── audio/                   ← NOUVEAU (fichiers TTS générés)

plans/
├── pipeline-v2.md           ← ce fichier
└── methodes-preprocessing.md  ← recherche preprocessing images (à créer)
```

---

## 4. Ordre d'Implémentation

| Phase | Tâche | Dépendances |
|-------|-------|-------------|
| **P1** | `config/config.json` — TTS, langues | rien |
| **P2** | `image_preprocessor.py` — renommage + fonctions preprocessing | recherche MD |
| **P3** | `reco_engine.py` — Phase 1 (mesures → LLM) | Groq API |
| **P4** | `tts_engine.py` — espeak-ng + piper | installation paquets |
| **P5** | `data_logger.py` — nouveaux champs | P3, P4 |
| **P6** | `main.py` — pipeline complet + auto-launch Flask | P2, P3, P4, P5 |
| **P7** | `web/app.py` — refonte SPA + API | P5 |
| **P8** | `web/static/app.js` — dashboard client-side | P7 |
| **P9** | `web/static/chat.js` — chat bubble + API /chat | P7 |
| **P10** | TTS endpoint + bouton replay | P4, P7 |
| **P11** | `config/crops_db.json` + DB lookup (Phase 2) | P3 |

---

## 5. Prompt Système du Chat IA

```
Tu es un expert agronome spécialisé en agriculture africaine (Sahel, zones tropicales).
Tu as accès aux données de mesure du sol suivantes :
{results_json}

Tu as aussi les analyses visuelles des photos du sol :
{vlm_analysis}

Et les recommandations générées automatiquement :
{reco_json}

Règles :
- Réponds en {language} (langue configurée).
- Sois concis mais complet. Utilise des termes simples compréhensibles par un agriculteur.
- Base-toi UNIQUEMENT sur les données fournies. Ne pas inventer de valeurs.
- Si une question sort du contexte agricole, réponds poliment que tu es spécialisé en agriculture.
- Suggère des cultures adaptées au type de sol mesuré.
- Mentionne les risques (pH extrême, salinité, sécheresse) si pertinent.
```

---

## 6. Notes Techniques

- **Flask → SPA :** plus de `render_template()`. Le HTML est un fichier statique unique, les données viennent de `/api/*`.
- **TTS offline first :** espeak-ng par défaut (zéro latence, zéro quota). Piper pour meilleure qualité si installé. Elvenlabs en option online.
- **Chat :** WebSocket ou polling ? Pour simplifier : POST `/api/chat` → réponse JSON. Le frontend fait du polling ou SSE.
- **DB crops :** Phase 2 uniquement. Pour l'instant, les recommandations passent directement par le LLM.
- **Nettoyage prints "NPK" :** à faire dans arm.py (`s/NPK/capteur sol/g`) — cosmétique mais propre.
