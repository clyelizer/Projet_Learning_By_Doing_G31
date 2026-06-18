#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moteur de recommandations agricoles.

Phase 1 : envoie les mesures brutes au LLM (Groq Llama 8B)
Phase 2 (future) : enrichit avec base de données cultures/sols

Usage:
    python reco_engine.py          # test avec données simulées
"""

import json
import os
import sys

import requests
from config_loader import load_config as _load_config

# Charger .env si présent
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── Configuration ─────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"


# ── Prompt système ────────────────────────────────────────────────

def _build_system_prompt(language='fr'):
    """Construit le prompt système pour les recommandations agricoles."""
    prompts = {
        'fr': (
            "Tu es un expert agronome spécialisé en agriculture africaine "
            "(zones sahéliennes et tropicales). "
            "Analyse les mesures de sol fournies et donne des recommandations "
            "concrètes et actionnables pour un agriculteur.\n\n"
            "RÈGLES :\n"
            "- Réponds UNIQUEMENT en JSON valide, sans texte avant ni après.\n"
            "- Sois précis : nomme des cultures spécifiques adaptées, pas des généralités.\n"
            "- Mentionne les quantités (kg/ha, mm d'eau, etc.) quand c'est pertinent.\n"
            "- Si une valeur est hors norme, explique le risque.\n"
            "- Utilise un langage simple, compréhensible par un agriculteur.\n"
        ),
        'en': (
            "You are an agronomy expert specialized in African agriculture "
            "(Sahelian and tropical zones). "
            "Analyze the soil measurements provided and give concrete, "
            "actionable recommendations for a farmer.\n\n"
            "RULES:\n"
            "- Answer ONLY in valid JSON, no text before or after.\n"
            "- Be specific: name specific suitable crops, not generalities.\n"
            "- Mention quantities (kg/ha, mm of water, etc.) when relevant.\n"
            "- If a value is out of range, explain the risk.\n"
            "- Use simple language understandable by a farmer.\n"
        ),
    }
    return prompts.get(language, prompts['fr'])


def _build_user_message(sensor_data, image_analysis=None):
    """Construit le message utilisateur avec les mesures."""
    msg = "Voici les mesures du sol :\n"
    msg += f"- Humidité : {sensor_data.get('humidity_pct', '?')} %\n"
    msg += f"- Température : {sensor_data.get('temperature_c', '?')} °C\n"
    msg += f"- Conductivité (EC) : {sensor_data.get('ec_us_cm', '?')} µS/cm\n"
    msg += f"- pH : {sensor_data.get('ph', '?')}\n"

    if image_analysis:
        vlm = image_analysis
        msg += f"\nAnalyse visuelle du sol :\n"
        msg += f"- Type de sol : {vlm.get('soil_type', 'inconnu')}\n"
        msg += f"- Couleur : {vlm.get('color', 'inconnue')}\n"
        msg += f"- Texture : {vlm.get('texture', 'inconnue')}\n"
        msg += f"- Humidité apparente : {vlm.get('moisture_estimate', 'inconnue')}\n"
        msg += f"- Couverture végétale : {vlm.get('vegetation_cover', '?')}%\n"

    msg += (
        "\nRetourne UNIQUEMENT ce JSON :\n"
        '{\n'
        '  "crops": ["culture1", "culture2", "culture3"],\n'
        '  "fertilizer": {"type": "...", "rate": "...", "frequency": "..."},\n'
        '  "soil_amendments": ["amendement1", "amendement2"],\n'
        '  "irrigation": {"frequency": "...", "amount": "..."},\n'
        '  "warnings": ["risque1", "risque2"],\n'
        '  "summary": "résumé en une phrase"\n'
        '}'
    )
    return msg


# ── Appel API ─────────────────────────────────────────────────────

def recommend(sensor_data, image_analysis=None, language='fr'):
    """
    Génère des recommandations agricoles via Groq Llama 8B.

    Args:
        sensor_data: dict — mesures du capteur {humidity_pct, temperature_c, ec_us_cm, ph}
        image_analysis: dict ou None — résultat de vlm_analyzer.analyze_soil_ia()
        language: 'fr' ou 'en'

    Returns:
        dict structuré ou dict avec 'error' en cas d'échec
    """
    if not GROQ_API_KEY:
        return {'error': 'GROQ_API_KEY non configurée'}

    config = _load_config()
    model = config.get('reco', {}).get('model', DEFAULT_MODEL)
    temperature = config.get('reco', {}).get('temperature', 0.2)
    max_tokens = config.get('reco', {}).get('max_tokens', 512)

    system_prompt = _build_system_prompt(language)
    user_message = _build_user_message(sensor_data, image_analysis)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        data = resp.json()

        if resp.status_code == 429:
            return {'error': 'Quota Groq dépassé (429) — réessayer plus tard'}

        if resp.status_code != 200:
            err = data.get('error', {}).get('message', str(resp.status_code))
            return {'error': f'Groq: {err}'}

        choices = data.get('choices', [])
        if not choices:
            return {'error': 'Groq: aucune réponse (choices vide)'}
        content = choices[0].get('message', {}).get('content', '')
        if not content:
            return {'error': 'Groq: contenu vide'}

        result = json.loads(content)
        result['_model'] = model
        result['_provider'] = 'groq'
        return result

    except requests.exceptions.Timeout:
        return {'error': 'Timeout — le serveur Groq ne répond pas'}
    except json.JSONDecodeError:
        return {'error': 'Réponse Groq invalide (JSON malformé)'}
    except Exception as e:
        return {'error': str(e)}


# ── Test ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Test reco_engine (données simulées)\n")

    fake_sensor = {
        'humidity_pct': 21.5,
        'temperature_c': 23.4,
        'ec_us_cm': 62.0,
        'ph': 8.2,
    }

    print(f"Mesures: {json.dumps(fake_sensor, indent=2)}")
    print(f"\nEnvoi à Groq ({DEFAULT_MODEL})...\n")

    result = recommend(fake_sensor, language='fr')

    if 'error' in result:
        print(f"❌ {result['error']}")
    else:
        print("✅ Recommandations :")
        print(json.dumps(result, indent=2, ensure_ascii=False))
