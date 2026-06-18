#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests config_loader — chargement de config/config.json.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from config_loader import load_config


class TestConfigLoader:
    """Tests du chargeur de configuration partagé."""

    def test_load_returns_dict(self):
        """Retourne un dict (jamais None)."""
        config = load_config()
        assert isinstance(config, dict)

    def test_tts_section(self):
        """Section TTS présente."""
        config = load_config()
        assert 'tts' in config
        assert 'engine' in config['tts']

    def test_languages_section(self):
        """Section langues avec au moins 7 entrées."""
        config = load_config()
        assert 'languages' in config
        assert len(config['languages']) >= 7

    def test_chat_section(self):
        """Section chat avec modèle Groq."""
        config = load_config()
        assert 'chat' in config
        assert 'llama' in config['chat']['model']

    def test_reco_section(self):
        """Section reco avec température."""
        config = load_config()
        assert 'reco' in config
        assert 'temperature' in config['reco']

    def test_tts_engine_value(self):
        """Le moteur TTS par défaut est espeak-ng."""
        config = load_config()
        assert config['tts']['engine'] == 'espeak-ng'

    def test_offline_fallback_enabled(self):
        """Le fallback offline est activé."""
        config = load_config()
        assert config['tts']['offline_fallback'] is True

    def test_languages_include_bambara(self):
        """Le Bambara est dans les langues supportées."""
        config = load_config()
        assert 'bm' in config['languages']
        assert 'Bambara' in config['languages']['bm']
