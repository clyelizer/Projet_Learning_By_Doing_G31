#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moteur de synthèse vocale (TTS) multi-moteur.

3 moteurs :
  espeak-ng  — offline, rapide, qualité basique (install: sudo apt install espeak-ng)
  piper      — offline, neuronal, qualité supérieure (install: pip install piper-tts)
  elvenlabs  — online, qualité premium (install: pip install elevenlabs + clé API)

Priorité : moteur configuré → fallback offline si échec.

Usage:
    python tts_engine.py "Bonjour le monde"
    python tts_engine.py --lang bm "I ni ce"    # Bambara
"""

import json
import os
import subprocess
import tempfile
import time

from config_loader import load_config as _load_config

# Dossier audio persistant (évite la fuite de fichiers temporaires)
AUDIO_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Langues autorisées (allowlist pour validation)
ALLOWED_LANGUAGES = {'fr', 'en', 'bm', 'ar', 'wo', 'ff', 'ha'}

# Vérification disponibilité des moteurs
try:
    subprocess.run(['espeak-ng', '--version'], capture_output=True, timeout=2)
    ESPEAK_AVAILABLE = True
except (FileNotFoundError, subprocess.TimeoutExpired):
    ESPEAK_AVAILABLE = False

try:
    import piper.voice
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

try:
    from elevenlabs import play, save
    from elevenlabs.client import ElevenLabs
    ELVENLABS_AVAILABLE = True
except ImportError:
    ELVENLABS_AVAILABLE = False


# ── Configuration ─────────────────────────────────────────────────

def _load_config():
    """Délégué à config_loader. Conservé pour rétrocompatibilité interne."""
    from config_loader import load_config
    return load_config()


def get_available_engines():
    """Liste les moteurs disponibles."""
    engines = []
    if ESPEAK_AVAILABLE:
        engines.append('espeak-ng')
    if PIPER_AVAILABLE:
        engines.append('piper')
    if ELVENLABS_AVAILABLE and os.environ.get('ELEVENLABS_API_KEY'):
        engines.append('elvenlabs')
    return engines


def get_available_languages(engine):
    """Langues supportées par moteur."""
    all_langs = {
        'fr': 'Français', 'en': 'English', 'bm': 'Bamanankan',
        'ar': 'العربية', 'wo': 'Wolof', 'ff': 'Fulfulde', 'ha': 'Hausa',
    }
    if engine == 'elvenlabs':
        # Elvenlabs supporte ~30 langues
        return all_langs
    elif engine == 'espeak-ng':
        # espeak-ng supporte ~100 langues
        return all_langs
    elif engine == 'piper':
        # Piper: dépend des modèles installés. Fallback fr/en.
        return {k: v for k, v in all_langs.items() if k in ('fr', 'en')}
    return {}


# ── Moteurs ───────────────────────────────────────────────────────

def _speak_espeak(text, lang='fr', speed=150):
    """
    Synthèse via espeak-ng.
    Sauvegarde dans data/audio/ avec nettoyage des anciens fichiers.
    """
    config = _load_config()
    tts_cfg = config.get('tts', {})
    speed = tts_cfg.get('espeak_speed', speed)
    voice = tts_cfg.get('espeak_voice', lang)

    # Nom prédictible → écrasé à chaque appel (pas de fuite disque)
    out_path = os.path.join(AUDIO_DIR, f'espeak_{lang}.wav')

    cmd = [
        'espeak-ng', '-v', voice, '-s', str(speed),
        '-w', out_path, '--', text
    ]
    subprocess.run(cmd, capture_output=True, timeout=10)
    return out_path


def _speak_piper(text, lang='fr'):
    """
    Synthèse via Piper TTS (neuronal).
    """
    config = _load_config()
    tts_cfg = config.get('tts', {})
    model_name = tts_cfg.get('piper_model', 'fr_FR-siwis-medium')

    voice = piper.voice.PiperVoice.load(model_name)
    out_path = os.path.join(AUDIO_DIR, f'piper_{lang}.wav')

    with open(out_path, 'wb') as wav_file:
        for audio_bytes in voice.synthesize_stream_raw(text):
            wav_file.write(audio_bytes)

    return out_path


def _speak_elvenlabs(text, lang='fr'):
    """
    Synthèse via ElevenLabs API.
    Qualité premium, nécessite clé API.
    """
    api_key = os.environ.get('ELEVENLABS_API_KEY')
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY non configurée")

    client = ElevenLabs(api_key=api_key)
    audio = client.generate(text=text, voice="Rachel")
    out_path = os.path.join(AUDIO_DIR, f'elvenlabs_{lang}.mp3')
    save(audio, out_path)
    return out_path


# ── API Publique ──────────────────────────────────────────────────

def speak(text, engine='auto', lang='fr'):
    """
    Synthétise un texte en audio.

    Args:
        text: str — texte à prononcer
        engine: 'auto' (détection auto), 'espeak-ng', 'piper', 'elvenlabs'
        lang: code langue ('fr', 'en', 'bm', 'ar', 'wo', 'ff', 'ha')

    Returns:
        dict: {'path': chemin_fichier, 'engine': moteur_utilisé, 'lang': langue}
        ou {'error': message} en cas d'échec total
    """
    config = _load_config()
    tts_cfg = config.get('tts', {})
    offline_fallback = tts_cfg.get('offline_fallback', True)

    # Valider la langue contre l'allowlist
    if lang not in ALLOWED_LANGUAGES:
        return {'error': f'Langue non supportée: {lang}. '
                         f'Langues disponibles: {sorted(ALLOWED_LANGUAGES)}'}

    if engine == 'auto':
        engine = tts_cfg.get('engine', 'espeak-ng')

    # Ordre de priorité : moteur demandé → fallback offline
    priority = [engine]
    if offline_fallback and engine != 'espeak-ng':
        priority.append('espeak-ng')
    if offline_fallback and engine != 'piper':
        priority.append('piper')

    errors = []
    for eng in priority:
        try:
            if eng == 'espeak-ng' and ESPEAK_AVAILABLE:
                path = _speak_espeak(text, lang=lang)
                return {'path': path, 'engine': 'espeak-ng', 'lang': lang}
            elif eng == 'piper' and PIPER_AVAILABLE:
                path = _speak_piper(text, lang=lang)
                return {'path': path, 'engine': 'piper', 'lang': lang}
            elif eng == 'elvenlabs' and ELVENLABS_AVAILABLE:
                path = _speak_elvenlabs(text, lang=lang)
                return {'path': path, 'engine': 'elvenlabs', 'lang': lang}
        except Exception as e:
            errors.append(f"{eng}: {e}")

    return {'error': '; '.join(errors) if errors else 'Aucun moteur TTS disponible'}


def play_audio(audio_path):
    """
    Joue un fichier audio sur le haut-parleur du Pi.

    Args:
        audio_path: chemin vers un .wav ou .mp3
    """
    try:
        subprocess.run(['aplay', audio_path], capture_output=True, timeout=30)
    except FileNotFoundError:
        try:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', audio_path],
                         capture_output=True, timeout=30)
        except FileNotFoundError:
            print(f"[TTS] Impossible de jouer {audio_path}: aucun lecteur audio trouvé")


# ── Test ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    lang = 'fr'
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Bonjour, je suis le robot agricole."

    print(f"TTS Engine Test")
    print(f"  Disponibles: {get_available_engines()}")
    print(f"  Texte: \"{text}\"")
    print(f"  Langue: {lang}")
    print()

    result = speak(text, engine='auto', lang=lang)

    if 'error' in result:
        print(f"❌ {result['error']}")
    else:
        print(f"✅ Audio: {result['path']}")
        print(f"   Moteur: {result['engine']}")
        play_audio(result['path'])
        # Nettoyage
        time.sleep(3)
        os.remove(result['path'])
        print("   Fichier nettoyé.")
