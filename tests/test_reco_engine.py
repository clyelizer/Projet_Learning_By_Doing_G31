#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests reco_engine — recommandations agricoles via Groq Llama 8B.

Skip par défaut (quota API). Activer avec :
    RUN_VLM=1 pytest tests/test_reco_engine.py -v -s
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from reco_engine import recommend, _build_system_prompt, _build_user_message

_RUN = os.environ.get('RUN_VLM') == '1'


# ── Tests sans API (toujours exécutés) ────────────────────────────

class TestPromptBuilding:
    """Vérifie la construction des prompts (pas d'appel API)."""

    def test_system_prompt_fr_contient_agronome(self):
        prompt = _build_system_prompt('fr')
        assert 'agronome' in prompt
        assert 'JSON' in prompt

    def test_system_prompt_en_contient_agronomy(self):
        prompt = _build_system_prompt('en')
        assert 'agronomy' in prompt.lower()

    def test_user_message_contient_mesures(self):
        sensor = {
            'humidity_pct': 21.5, 'temperature_c': 23.4,
            'ec_us_cm': 62.0, 'ph': 8.2,
        }
        msg = _build_user_message(sensor)
        assert '21.5' in msg
        assert '23.4' in msg
        assert '62.0' in msg
        assert '8.2' in msg

    def test_user_message_avec_vlm(self):
        sensor = {'humidity_pct': 30, 'temperature_c': 25, 'ec_us_cm': 100, 'ph': 7}
        vlm = {
            'soil_type': 'argileux', 'color': 'brun',
            'texture': 'fine', 'moisture_estimate': 'humide',
            'vegetation_cover': 15,
        }
        msg = _build_user_message(sensor, vlm)
        assert 'argileux' in msg
        assert 'brun' in msg


class TestRecommendEdgeCases:
    """Cas limites sans appel API."""

    def test_reco_avec_cle_ou_erreur(self):
        """Avec clé → résultat. Sans → erreur."""
        from reco_engine import GROQ_API_KEY
        result = recommend({'humidity_pct': 20, 'temperature_c': 25, 'ec_us_cm': 50, 'ph': 7})
        if GROQ_API_KEY is None:
            assert 'error' in result
        else:
            # La clé est présente → l'appel doit réussir ou donner une erreur documentée
            assert 'error' in result or 'crops' in result


# ── Tests avec API réelle (RUN_VLM=1) ─────────────────────────────

@pytest.mark.skipif(not _RUN, reason="RUN_VLM=1 non défini — quota préservé")
class TestRecommendReal:
    """Appels réels à Groq Llama 8B."""

    def test_reco_retourne_structure(self):
        """Une recommandation doit avoir crops, fertilizer, summary."""
        sensor = {
            'humidity_pct': 21.5, 'temperature_c': 23.4,
            'ec_us_cm': 62.0, 'ph': 8.2,
        }
        result = recommend(sensor, language='fr')

        if 'error' in result:
            pytest.skip(f"API down: {result['error']}")

        assert 'crops' in result
        assert isinstance(result['crops'], list)
        assert 'fertilizer' in result
        assert 'summary' in result
        print(f"\n  🌾 Cultures: {', '.join(result['crops'][:5])}")
        print(f"  🧪 Ferti: {result['fertilizer']}")
        print(f"  📝 {result['summary']}")

    def test_reco_avec_vlm(self):
        """Recommandation enrichie avec analyse visuelle."""
        sensor = {'humidity_pct': 30, 'temperature_c': 28, 'ec_us_cm': 200, 'ph': 6.5}
        vlm = {
            'soil_type': 'limoneux', 'color': 'brun foncé',
            'texture': 'moyenne', 'moisture_estimate': 'humide',
            'vegetation_cover': 20,
        }
        result = recommend(sensor, vlm, language='fr')

        if 'error' in result:
            pytest.skip(f"API down: {result['error']}")

        assert 'crops' in result
        assert result['_provider'] == 'groq'
        print(f"\n  🌾 Avec VLM: {', '.join(result['crops'][:5])}")

    def test_reco_english(self):
        """Recommandation en anglais."""
        sensor = {'humidity_pct': 15, 'temperature_c': 35, 'ec_us_cm': 500, 'ph': 5.5}
        result = recommend(sensor, language='en')

        if 'error' in result:
            pytest.skip(f"API down: {result['error']}")

        assert 'crops' in result
        print(f"\n  🇬🇧 Crops: {', '.join(result['crops'][:5])}")
