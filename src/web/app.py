#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Agricole — SPA (Single Page Application)

Routes API :
  GET  /                    → SPA (unique page HTML)
  GET  /api/results         → data/results.json
  GET  /api/recommendations → reco engine (dernières)
  POST /api/chat            → chat IA (Groq Llama 8B)
  POST /api/tts             → synthèse vocale
  GET  /api/tts/replay/<lang> → rejoue dernière reco
  GET  /photos/<filename>   → sert les photos

Pas de templates Jinja. Tout le rendu est côté client (app.js + chat.js).
"""

import json
import os
import sys
import pathlib
import subprocess

from flask import Flask, request, jsonify, send_from_directory, abort

# Ajouter src/ au path pour importer les modules
SRC_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))

from reco_engine import recommend
from tts_engine import speak, get_available_engines, get_available_languages

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent

app = Flask(__name__, static_folder='static', static_url_path='')


# ── Helpers ───────────────────────────────────────────────────────

def load_json(rel_path):
    path = PROJECT_DIR / rel_path
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ── SPA (unique page) ─────────────────────────────────────────────

@app.route('/')
def index():
    """Sert l'application SPA."""
    return send_from_directory(str(SCRIPT_DIR / 'static'), 'index.html')


# ── API ───────────────────────────────────────────────────────────

@app.route('/api/results')
def api_results():
    """Retourne results.json complet."""
    results = load_json('data/results.json')
    return jsonify(results or {})


@app.route('/api/recommendations')
def api_recommendations():
    """Retourne les recommandations du dernier waypoint avec mesures."""
    results = load_json('data/results.json')
    if not results:
        return jsonify([])

    waypoints = results.get('waypoints', [])
    output = []
    for wp in waypoints:
        entry = {
            'waypoint_id': wp.get('waypoint_id'),
            'sensor': wp.get('sensor'),
            'vlm_analysis': wp.get('vlm_analysis'),
            'recommendations': wp.get('recommendations'),
            'tts_audio': wp.get('tts_audio'),
            'photos': wp.get('photos', [])[:1],  # première photo
        }
        if entry['sensor'] or entry['recommendations']:
            output.append(entry)

    return jsonify(output)


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """
    Chat IA avec contexte complet (mesures + VLM + reco).
    Modèle : Groq Llama 3.1 8B.
    """
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message vide'}), 400

    language = data.get('language', 'fr')

    # Charger le contexte
    results = load_json('data/results.json')
    map_data = load_json('config/map.json')

    system_prompt = _build_chat_prompt(results, map_data, language)

    try:
        import requests
        groq_key = os.environ.get('GROQ_API_KEY')
        if not groq_key:
            return jsonify({'error': 'GROQ_API_KEY non configurée'}), 500

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if resp.status_code != 200:
            return jsonify({'error': f'Groq: {resp.status_code}'}), 502

        reply = resp.json()['choices'][0]['message']['content']
        return jsonify({'reply': reply, 'model': 'llama-3.1-8b-instant'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tts', methods=['POST'])
def api_tts():
    """Synthèse vocale d'un texte."""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    lang = data.get('language', 'fr')
    engine = data.get('engine', 'auto')

    if not text:
        return jsonify({'error': 'Texte vide'}), 400

    result = speak(text, engine=engine, lang=lang)
    return jsonify(result)


@app.route('/api/tts/replay/<lang>')
def api_tts_replay(lang):
    """Rejoue la dernière recommandation dans une langue donnée."""
    results = load_json('data/results.json')
    if not results:
        return jsonify({'error': 'Aucune donnée'}), 404

    # Trouver le dernier waypoint avec reco
    waypoints = results.get('waypoints', [])
    for wp in reversed(waypoints):
        reco = wp.get('recommendations')
        if reco and reco.get('summary'):
            result = speak(reco['summary'], engine='auto', lang=lang)
            return jsonify(result)

    return jsonify({'error': 'Aucune recommandation trouvée'}), 404


@app.route('/api/engines')
def api_engines():
    """Liste les moteurs TTS disponibles."""
    return jsonify({
        'engines': get_available_engines(),
        'languages': get_available_languages('espeak-ng'),
    })


# ── Photos ────────────────────────────────────────────────────────

@app.route('/photos/<filename>')
def serve_photo(filename):
    photos_dir = PROJECT_DIR / 'data' / 'photos'
    if not (photos_dir / filename).exists():
        abort(404)
    return send_from_directory(str(photos_dir), filename)


# ── Prompt système chat ───────────────────────────────────────────

def _build_chat_prompt(results, map_data, language='fr'):
    """Construit le prompt système du chat avec tout le contexte."""
    context = ""
    if results:
        waypoints = results.get('waypoints', [])
        for wp in waypoints:
            context += f"\nWaypoint {wp.get('waypoint_id')}:\n"
            s = wp.get('sensor')
            if s:
                context += (
                    f"  Humidité: {s.get('humidity_pct')}%, "
                    f"Temp: {s.get('temperature_c')}°C, "
                    f"EC: {s.get('ec_us_cm')}µS/cm, "
                    f"pH: {s.get('ph')}\n"
                )
            vlm = wp.get('vlm_analysis')
            if vlm and vlm.get('provider'):
                context += (
                    f"  Analyse visuelle: sol {vlm.get('soil_type')}, "
                    f"couleur {vlm.get('color')}, "
                    f"texture {vlm.get('texture')}\n"
                )
            reco = wp.get('recommendations')
            if reco:
                crops = reco.get('crops', [])
                if crops:
                    context += f"  Cultures recommandées: {', '.join(crops[:5])}\n"
                summary = reco.get('summary', '')
                if summary:
                    context += f"  Résumé: {summary}\n"

    prompts = {
        'fr': (
            "Tu es un expert agronome spécialisé en agriculture africaine "
            "(Sahel, zones tropicales). "
            "Tu réponds aux questions d'un agriculteur qui utilise un robot "
            "pour analyser son sol.\n\n"
            "DONNÉES DE LA DERNIÈRE MISSION :\n"
            f"{context}\n"
            "RÈGLES :\n"
            "- Réponds en français, langage simple et clair.\n"
            "- Base-toi UNIQUEMENT sur les données fournies ci-dessus.\n"
            "- Ne jamais inventer de valeurs ou de mesures.\n"
            "- Si une question sort du contexte agricole, réponds poliment "
            "que tu es spécialisé en agriculture.\n"
            "- Suggère des cultures adaptées au type de sol mesuré.\n"
            "- Mentionne les risques (pH extrême, salinité, sécheresse) "
            "si pertinent.\n"
        ),
        'en': (
            "You are an agronomy expert specialized in African agriculture...\n"
            f"{context}\n"
            "Answer in English...\n"
        ),
    }
    return prompts.get(language, prompts['fr'])


# ── Démarrage ─────────────────────────────────────────────────────

def _get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


if __name__ == '__main__':
    HOST = '0.0.0.0'
    PORT = 5000
    local_ip = _get_local_ip()

    print()
    print("=" * 60)
    print("  🌱 TABLEAU DE BORD AGRICOLE — SPA")
    print("=" * 60)
    print(f"  Local    : http://127.0.0.1:{PORT}")
    print(f"  Réseau   : http://{local_ip}:{PORT}")
    print("=" * 60)
    print()

    app.run(host=HOST, port=PORT, debug=True, use_reloader=False)
