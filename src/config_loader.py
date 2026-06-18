#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chargeur de configuration partagé.
Évite la duplication de _load_config() dans tous les modules.
"""

import json
import os


_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'config', 'config.json'
)


def load_config():
    """Charge config/config.json. Retourne {} si absent."""
    if os.path.exists(_CONFIG_PATH):
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    return {}
