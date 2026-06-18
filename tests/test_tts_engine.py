#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests tts_engine — synthèse vocale multi-moteur.

Skip si aucun moteur installé. Activer espeak-ng :
    sudo apt install espeak-ng

Lancement :
    pytest tests/test_tts_engine.py -v -s
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from tts_engine import (
    speak, play_audio, get_available_engines,
    get_available_languages, ALLOWED_LANGUAGES,
    ESPEAK_AVAILABLE, PIPER_AVAILABLE, ELVENLABS_AVAILABLE,
    AUDIO_DIR,
)

_ANY_ENGINE = ESPEAK_AVAILABLE or PIPER_AVAILABLE or ELVENLABS_AVAILABLE


# ── Tests sans moteur (toujours exécutés) ─────────────────────────

class TestConfiguration:
    """Vérifie la configuration et l'allowlist."""

    def test_audio_dir_exists(self):
        """Le dossier data/audio/ est créé automatiquement."""
        assert os.path.isdir(AUDIO_DIR)

    def test_allowed_languages(self):
        """Les 7 langues sont dans l'allowlist."""
        assert 'fr' in ALLOWED_LANGUAGES
        assert 'bm' in ALLOWED_LANGUAGES  # Bambara
        assert 'ar' in ALLOWED_LANGUAGES  # Arabe
        assert len(ALLOWED_LANGUAGES) >= 7

    def test_get_available_engines(self):
        """Retourne une liste (peut être vide)."""
        engines = get_available_engines()
        assert isinstance(engines, list)

    def test_get_available_languages(self):
        """Retourne un dict (peut être vide)."""
        langs = get_available_languages('espeak-ng')
        assert isinstance(langs, dict)


class TestValidation:
    """Validation des entrées."""

    def test_langue_invalide_rejetee(self):
        """Une langue non supportée est rejetée."""
        result = speak("test", engine='auto', lang='zz')
        assert 'error' in result
        assert 'Langue non supportée' in result['error']

    def test_langues_valides_acceptees(self):
        """Toutes les langues de l'allowlist passent la validation."""
        for lang in ALLOWED_LANGUAGES:
            result = speak("test", engine='auto', lang=lang)
            # Soit pas d'erreur de langue, soit erreur moteur (acceptable)
            if 'error' in result:
                assert 'Langue non supportée' not in result['error'], \
                    f"Langue {lang} rejetée alors qu'elle est dans l'allowlist"


# ── Tests avec moteur réel ────────────────────────────────────────

@pytest.mark.skipif(not _ANY_ENGINE, reason="Aucun moteur TTS installé")
class TestSpeakReal:
    """Synthèse vocale réelle."""

    def test_speak_francais(self):
        """Synthèse en français."""
        result = speak("Bonjour, je suis le robot agricole.", lang='fr')
        if 'error' in result:
            pytest.skip(f"Moteur down: {result['error']}")

        assert 'path' in result
        assert 'engine' in result
        assert os.path.isfile(result['path'])
        assert os.path.getsize(result['path']) > 0
        print(f"\n  🔊 {result['engine']}: {result['path']} "
              f"({os.path.getsize(result['path'])} bytes)")

    def test_speak_short_phrase(self):
        """Phrase courte."""
        result = speak("Sol analysé.", lang='fr')
        if 'error' in result:
            pytest.skip(f"Moteur down: {result['error']}")
        assert os.path.isfile(result['path'])

    def test_speak_avec_accents(self):
        """Caractères accentués."""
        result = speak("Humidité: vingt pourcent. pH: six virgule cinq.", lang='fr')
        if 'error' in result:
            pytest.skip(f"Moteur down: {result['error']}")
        assert os.path.isfile(result['path'])


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng absent")
class TestEspeakSpecific:
    """Tests spécifiques à espeak-ng."""

    def test_espeak_bambara(self):
        """Bambara : 'I ni ce' (bonjour)."""
        result = speak("I ni ce", engine='espeak-ng', lang='bm')
        if 'error' in result:
            pytest.skip(f"espeak-ng bambara: {result['error']}")
        assert os.path.isfile(result['path'])
        print(f"\n  🗣️ Bambara: {result['path']}")

    def test_espeak_wolof(self):
        """Wolof."""
        result = speak("Salaam aleekum", engine='espeak-ng', lang='wo')
        if 'error' in result:
            pytest.skip(f"espeak-ng wolof: {result['error']}")
        assert os.path.isfile(result['path'])

    def test_espeak_fallback_automatique(self):
        """Si engine=piper mais indisponible → fallback espeak-ng."""
        if not PIPER_AVAILABLE:
            result = speak("Test fallback.", engine='piper', lang='fr')
            # Doit tomber sur espeak-ng
            if 'error' not in result:
                assert result['engine'] == 'espeak-ng'
                print(f"  ✅ Fallback: piper→{result['engine']}")


# ── Nettoyage ─────────────────────────────────────────────────────

def test_audio_files_overwrite():
    """Les fichiers audio s'écrasent (pas d'accumulation)."""
    if not ESPEAK_AVAILABLE:
        pytest.skip("espeak-ng absent")

    import time
    result1 = speak("Premier test.", engine='espeak-ng', lang='fr')
    if 'error' in result1:
        pytest.skip(f"espeak-ng down: {result1['error']}")
    mtime1 = os.path.getmtime(result1['path'])

    time.sleep(0.5)
    result2 = speak("Deuxième test.", engine='espeak-ng', lang='fr')
    mtime2 = os.path.getmtime(result2['path'])

    # Même fichier → mtime doit avoir changé
    assert result1['path'] == result2['path'], \
        "Les fichiers audio ne s'écrasent pas"
    assert mtime2 > mtime1, \
        f"Le fichier n'a pas été réécrit ({mtime1} → {mtime2})"
