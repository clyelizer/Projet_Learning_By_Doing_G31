#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyseur VLM (Vision Language Model) pour photos de sol.

Deux providers :
  - Gemini 2.0 Flash (Google AI Studio, free tier)
  - Groq + Llama 4 Scout (OpenAI-compatible)

La fonction analyze_soil_ia() gère le fallback automatique :
  Gemini → si quota épuisé → Groq → si échec → message d'erreur.

Configuration des clés API (variables d'environnement) :
  export GEMINI_API_KEY="votre_cle"
  export GROQ_API_KEY="votre_cle"
"""

import base64
import json
import os
import time

import requests

# Charger .env si présent (dotenv optionnel)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Prompt système pour l'analyse de sol ──────────────────────────

SOIL_PROMPT = (
    "Tu es un expert en agronomie. Analyse cette photo de sol et retourne UNIQUEMENT du JSON. "
    "Ne mets JAMAIS null : fais toujours une estimation visuelle basée sur ce que tu vois "
    "(couleur, texture, humidité apparente, végétation).\n"
    "{\n"
    '  "soil_type": "type de sol (argileux, limoneux, sableux, organique, etc.)",\n'
    '  "color": "couleur dominante du sol",\n'
    '  "texture": "texture perçue (fine, moyenne, grossière)",\n'
    '  "moisture_estimate": "sec, humide, ou détrempé",\n'
    '  "vegetation_cover": pourcentage de végétation visible (0-100),\n'
    '  "crop_health": "bonne, moyenne, mauvaise, ou aucune culture",\n'
    '  "anomalies": "cailloux, racines, insectes, moisissures, ou rien à signaler",\n'
    '  "recommendations": ["conseil personnalisé 1", "conseil 2"]\n'
    "}\n"
    "Tu dois TOUJOURS remplir tous les champs. Si tu n'es pas sûr, donne la meilleure estimation possible."
)


# ── Récupération des clés ────────────────────────────────────────

def _get_gemini_key():
    return os.environ.get('GEMINI_API_KEY')


def _get_groq_key():
    return os.environ.get('GROQ_API_KEY')


# ── Appels providers ─────────────────────────────────────────────

def _call_gemini(image_path):
    """
    Appelle Gemini 2.0 Flash via Google AI Studio API.
    Retourne le dict parsé ou lève une exception.
    """
    key = _get_gemini_key()
    if not key:
        raise ValueError("GEMINI_API_KEY non configurée")

    with open(image_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    params = {"key": key}
    headers = {"Content-Type": "application/json"}

    payload = {
        "contents": [{
            "parts": [
                {"text": SOIL_PROMPT},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": img_b64
                }}
            ]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2,
            "maxOutputTokens": 512,
        }
    }

    resp = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
    data = resp.json()

    if resp.status_code == 429:
        raise ConnectionRefusedError("Gemini : quota dépassé (429)")

    if resp.status_code != 200:
        err_msg = data.get('error', {}).get('message', str(resp.status_code))
        raise RuntimeError(f"Gemini : {err_msg}")

    # Extraire le texte de la réponse Gemini
    try:
        text = data['candidates'][0]['content']['parts'][0]['text']
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Gemini : réponse invalide : {e}")


def _call_groq(image_path):
    """
    Appelle Groq + Llama 4 Scout (API OpenAI-compatible).
    Retourne le dict parsé ou lève une exception.
    """
    key = _get_groq_key()
    if not key:
        raise ValueError("GROQ_API_KEY non configurée")

    with open(image_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": SOIL_PROMPT},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{img_b64}"
                }}
            ]
        }],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 512,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    data = resp.json()

    if resp.status_code == 429:
        raise ConnectionRefusedError("Groq : quota dépassé (429)")

    if resp.status_code != 200:
        err_msg = data.get('error', {}).get('message', str(resp.status_code))
        raise RuntimeError(f"Groq : {err_msg}")

    try:
        text = data['choices'][0]['message']['content']
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Groq : réponse invalide : {e}")


# ── Orchestrateur avec fallback ───────────────────────────────────

def analyze_soil_ia(image_path, primary='gemini'):
    """
    Analyse une photo de sol via VLM, avec fallback automatique.

    Args:
        image_path: chemin de l'image JPEG
        primary: provider principal ('gemini' ou 'groq')

    Returns:
        dict : résultat structuré de l'analyse, ou dict d'erreur

    Structure de retour (succès) :
        {
            'provider': 'gemini' | 'groq',
            'soil_type': str,
            'color': str,
            'texture': str,
            'moisture_estimate': str,
            'vegetation_cover': float | null,
            'crop_health': str | null,
            'anomalies': str | null,
            'recommendations': list[str],
            'raw': dict  # réponse brute du VLM
        }
    """
    providers_order = ['gemini', 'groq'] if primary == 'gemini' else ['groq', 'gemini']
    errors = []

    for provider in providers_order:
        try:
            if provider == 'gemini':
                result = _call_gemini(image_path)
            else:
                result = _call_groq(image_path)

            # Normaliser : accepter anglais ET français
            # Note: utiliser des helper pour ne pas perdre les valeurs 0
            def _val(*keys):
                for k in keys:
                    v = result.get(k)
                    if v is not None:
                        return v
                return None

            return {
                'provider': provider,
                'soil_type': _val('soil_type', 'type_sol', 'soiltype', 'type_de_sol'),
                'color': _val('color', 'couleur', 'dominant_color'),
                'texture': _val('texture', 'texture_sol'),
                'moisture_estimate': _val('moisture_estimate', 'moisture',
                                          'humidite', 'humidité'),
                'vegetation_cover': _val('vegetation_cover', 'vegetation',
                                         'couverture_vegetale'),
                'crop_health': _val('crop_health', 'crophealth',
                                    'sante_cultures', 'santé'),
                'anomalies': _val('anomalies', 'anomalies_observées', 'observations'),
                'recommendations': (_val('recommendations', 'recommandations',
                                         'advice', 'conseils') or []),
                'raw': result,
            }

        except ConnectionRefusedError as e:
            # Quota dépassé → essayer le suivant
            errors.append(str(e))
            continue
        except Exception as e:
            errors.append(str(e))
            continue

    return {
        'provider': None,
        'error': '; '.join(errors),
        'soil_type': None,
        'recommendations': [],
    }


# ── Test direct ───────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vlm_analyzer.py <image_path> [provider]")
        print("       provider: gemini (default) | groq")
        sys.exit(1)

    path = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else 'gemini'

    if not os.path.exists(path):
        print(f"Fichier introuvable : {path}")
        sys.exit(1)

    print(f"Analyse VLM via {provider}...")
    print(f"Image : {path}")
    print("-" * 50)

    result = analyze_soil_ia(path, primary=provider)

    if result.get('provider'):
        print(f"✅ Provider : {result['provider']}")
        print(f"🌱 Type sol  : {result['soil_type']}")
        print(f"🎨 Couleur   : {result['color']}")
        print(f"🔬 Texture   : {result['texture']}")
        print(f"💧 Humidité  : {result['moisture_estimate']}")
        print(f"🌿 Végétation: {result['vegetation_cover']}%")
        print(f"🍃 Santé     : {result['crop_health']}")
        if result.get('anomalies'):
            print(f"⚠️  Anomalies : {result['anomalies']}")
        if result.get('recommendations'):
            print(f"\n💡 Recommandations :")
            for r in result['recommendations']:
                print(f"   • {r}")
        # Afficher la réponse brute (pour debug si champs absents)
        if result.get('raw'):
            print(f"\n📦 Réponse brute du modèle :")
            print(json.dumps(result['raw'], indent=2, ensure_ascii=False)[:500])
    else:
        print(f"❌ Échec : {result.get('error', 'inconnu')}")
