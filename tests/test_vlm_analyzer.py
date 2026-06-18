#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests VLM analyzer — appels API réels, aucun mock.

Par défaut les appels API sont désactivés (quota). Pour les activer :
    RUN_VLM=1 pytest tests/test_vlm_analyzer.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from src.vlm_analyzer import (
    _get_gemini_key,
    _get_groq_key,
    _call_gemini,
    _call_groq,
    analyze_soil_ia,
)

# Par défaut on ne brûle pas de quota API.
# Mettre RUN_VLM=1 dans l'environnement pour activer les appels réels.
_RUN_VLM = os.environ.get('RUN_VLM') == '1'

# ── Photo de test ─────────────────────────────────────────────────

def _find_any_photo():
    """Cherche n'importe quel .jpg dans data/photos/. Retourne None si aucun."""
    photos_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'photos')
    if not os.path.isdir(photos_dir):
        return None
    for f in os.listdir(photos_dir):
        if f.endswith('.jpg'):
            return os.path.join(photos_dir, f)
    return None

_PHOTO_PATH = _find_any_photo()
_photo_dispo = _PHOTO_PATH is not None


# ── Clés API ──────────────────────────────────────────────────────

class TestApiKeys:
    """Vérifie que les clés sont bien lues depuis l'environnement."""

    def test_gemini_key_est_chargee(self):
        key = _get_gemini_key()
        if key is None:
            pytest.skip("GEMINI_API_KEY non configurée")
        assert key.startswith('AIza') or key.startswith('sk-'), \
            f"Clé Gemini format inattendu: {key[:6]}..."

    def test_groq_key_est_chargee(self):
        key = _get_groq_key()
        if key is None:
            pytest.skip("GROQ_API_KEY non configurée")
        assert key.startswith('gsk_'), \
            f"Clé Groq format inattendu: {key[:6]}..."


# ── Appels réels ──────────────────────────────────────────────────

@pytest.mark.skipif(not _RUN_VLM, reason="RUN_VLM=1 non défini — quota API préservé")
@pytest.mark.skipif(not _photo_dispo, reason="Pas de photo dans data/photos/")
class TestVlmReal:
    """Appels réels aux APIs avec une vraie photo du robot."""

    def test_gemini_analyse_photo(self):
        """Appel Gemini avec photo réelle."""
        if _get_gemini_key() is None:
            pytest.skip("GEMINI_API_KEY absente")

        try:
            result = _call_gemini(_PHOTO_PATH)
        except ConnectionRefusedError:
            pytest.skip("Gemini quota dépassé (429)")

        assert isinstance(result, dict)
        assert 'soil_type' in result or 'type_sol' in result

    def test_groq_analyse_photo(self):
        """Appel Groq avec photo réelle."""
        if _get_groq_key() is None:
            pytest.skip("GROQ_API_KEY absente")

        try:
            result = _call_groq(_PHOTO_PATH)
        except ConnectionRefusedError:
            pytest.skip("Groq quota dépassé (429)")

        assert isinstance(result, dict)
        assert 'soil_type' in result

    def test_analyze_soil_fallback_gemini_primary(self):
        """analyze_soil_ia(primary='gemini') avec fallback si quota."""
        result = analyze_soil_ia(_PHOTO_PATH, primary='gemini')

        # Doit avoir un provider (gemini ou fallback groq) ou erreur explicite
        if result['provider'] is not None:
            assert result['provider'] in ('gemini', 'groq')
            assert result['soil_type'] is not None
        else:
            # Les deux sont down → erreur documentée
            assert 'error' in result

    def test_analyze_soil_fallback_groq_primary(self):
        """analyze_soil_ia(primary='groq') avec fallback si quota."""
        result = analyze_soil_ia(_PHOTO_PATH, primary='groq')

        if result['provider'] is not None:
            assert result['provider'] in ('gemini', 'groq')
            assert result['soil_type'] is not None
        else:
            assert 'error' in result

    def test_normalisation_cles_sortie(self):
        """Vérifie que toutes les clés normalisées sont présentes."""
        result = analyze_soil_ia(_PHOTO_PATH, primary='gemini')

        if result['provider'] is None:
            pytest.skip("Aucun provider dispo — impossible de tester la normalisation")

        # Toutes les clés normalisées doivent exister (FR ou EN acceptées)
        assert 'provider' in result
        assert 'soil_type' in result
        assert 'color' in result
        assert 'texture' in result
        assert 'moisture_estimate' in result
        assert 'vegetation_cover' in result
        assert 'crop_health' in result
        assert 'anomalies' in result
        assert 'recommendations' in result
        assert 'raw' in result
        # recommendations est une liste
        assert isinstance(result['recommendations'], list)


# ── Sans clé ──────────────────────────────────────────────────────

class TestSansCle:
    """Comportement quand aucune clé n'est configurée."""

    def test_call_gemini_sans_cle_leve_erreur(self, monkeypatch):
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
        with pytest.raises(ValueError, match='GEMINI_API_KEY'):
            _call_gemini('/fake/photo.jpg')

    def test_call_groq_sans_cle_leve_erreur(self, monkeypatch):
        monkeypatch.delenv('GROQ_API_KEY', raising=False)
        with pytest.raises(ValueError, match='GROQ_API_KEY'):
            _call_groq('/fake/photo.jpg')

    def test_analyze_soil_ia_sans_cles(self, monkeypatch):
        """Sans aucune clé → dict d'erreur."""
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
        monkeypatch.delenv('GROQ_API_KEY', raising=False)
        result = analyze_soil_ia('/fake/photo.jpg')
        assert result['provider'] is None
        assert 'error' in result
        assert result['recommendations'] == []
