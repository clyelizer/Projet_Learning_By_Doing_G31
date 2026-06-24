#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Conseil Personnalisé — AgroScan

Pipeline :
  1. LLM pose des questions UNE PAR UNE sur le terrain
  2. Collecte les réponses jusqu'à avoir 4+ infos
  3. Passe les données au pipeline ML (reco_engine)
  4. LLM explique les résultats

Usage :
    from advisor import handle_conversation
    result = handle_conversation(messages_echange)
"""

import json
import os
import sys
import re
import traceback

# Ajouter src/ au path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

from reco_engine import recommend, estimer_NPK


# ── Prompts système ─────────────────────────────────────────

COLLECT_PROMPT = """Tu es un expert agronome spécialisé en agriculture africaine.

Tu dois poser des questions UNE PAR UNE pour connaître le terrain de l'utilisateur.
ATTENTION : Ne pose jamais plusieurs questions dans le même message.

Objectif : collecter AU MOINS 4 informations parmi :
1. Pays et région (ex: Bénin, département Zou)
2. Type de sol (argileux, sableux, limoneux, latéritique)
3. Humidité du sol (sec, humide, détrempé)
4. pH du sol (acide ≈4-5.5, neutre ≈5.5-7.5, basique ≈7.5-9)
5. Couleur du sol (noir, rouge, jaune, gris, brun)
6. Texture (collant, granuleux, poudreux)
7. Engrais déjà utilisés (N/P/K si connu, ex: NPK 15-15-15)
8. Culture précédente (ce qui poussait avant)

RÈGLES STRICTES :
- Pose UNE question à la fois. Attends la réponse avant la suivante.
- Reformule si l'utilisateur ne comprend pas.
- Si l'utilisateur dit "je ne sais pas", note "non_renseigne" et passe à la suivante.
- Quand tu as AU MOINS 4 réponses, termine ton message par :
  [CONSEIL]{"pays":"...","region":"...","sol":"...","humidite":"...","ph":"...","couleur":"...","texture":"...","engrais":"...","precedent":"..."}
- N'invente RIEN. Si inconnu → "non_renseigne".
- Reste amical et parle langage simple (paysan, pas chercheur).
- Tu peux t'aider du contexte de la mission si disponible."""

EXPLAIN_PROMPT = """
Tu es un expert agronome africain. Tu reçois les résultats d'analyse ML
pour le champ de l'utilisateur.

CONTEXTE DE L'UTILISATEUR (ses réponses) :
{user_context}

RÉSULTATS DE L'ANALYSE ML :
{crops_top}
{npk_estime}
{impact}

Consignes :
1. Explique les résultats en langage très simple (comme à un agriculteur).
2. Dis les 3 meilleures cultures pour son champ et POURQUOI.
3. Donne les doses d'engrais N/P/K recommandées.
4. Sois court : max 5-6 phrases.
5. Termine par : "Souhaitez-vous que je détaille un point en particulier ?"
"""


# ── Appel LLM (Groq) ────────────────────────────────────────

def _call_llm(messages, temperature=0.3, max_tokens=2048):
    """Appelle Groq Llama 3.1 8B."""
    import requests
    groq_key = os.environ.get('GROQ_API_KEY')
    if not groq_key:
        return {'error': 'GROQ_API_KEY non configurée'}

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return {'error': f'Groq: {resp.status_code} — {resp.text[:200]}'}
        reply = resp.json()['choices'][0]['message']['content']
        return {'reply': reply, 'model': 'llama-3.1-8b-instant'}
    except Exception as e:
        return {'error': str(e)}


# ── Parse du [CONSEIL] JSON ─────────────────────────────────

def _parse_conseil(text):
    """Extrait le JSON du marqueur [CONSEIL]{...} dans la réponse LLM."""
    match = re.search(r'\[CONSEIL\](\{.*?\})', text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


# ── Construction du contexte utilisateur ─────────────────────

def _build_user_context(data):
    """Transforme les données collectées en texte pour le LLM."""
    parts = []
    mapping = {
        'pays': 'Pays/région',
        'sol': 'Type de sol',
        'humidite': 'Humidité',
        'ph': 'pH',
        'couleur': 'Couleur',
        'texture': 'Texture',
        'engrais': 'Engrais utilisés',
        'precedent': 'Culture précédente',
    }
    for key, label in mapping.items():
        val = data.get(key, '').strip()
        if val and val != 'non_renseigne':
            parts.append(f"{label} : {val}")
    return '\n'.join(parts) if parts else 'Aucune donnée spécifique'


# ── Pipeline ML ─────────────────────────────────────────────

def _run_ml(data):
    """
    Passe les données collectées dans le pipeline ML.
    Retourne un dict avec les résultats formatés.
    """
    # Convertir les infos utilisateur en données capteur approximatives
    sensor = {}

    # pH
    ph_text = data.get('ph', '').lower()
    if 'acide' in ph_text:
        sensor['ph'] = 5.0
    elif 'neutre' in ph_text:
        sensor['ph'] = 6.5
    elif 'basique' in ph_text or 'alcalin' in ph_text:
        sensor['ph'] = 8.0
    else:
        sensor['ph'] = 6.5  # défaut

    # Humidité
    hum_text = data.get('humidite', '').lower()
    if 'sec' in hum_text or 'sèche' in hum_text:
        sensor['humidity_pct'] = 20
    elif 'humide' in hum_text:
        sensor['humidity_pct'] = 60
    elif 'détremp' in hum_text or 'détremp' in hum_text:
        sensor['humidity_pct'] = 85
    else:
        sensor['humidity_pct'] = 40

    # Température (approximative Afrique)
    sensor['temperature_c'] = 28

    # EC (conductivité — valeur par défaut moyenne)
    sensor['ec_us_cm'] = 200

    try:
        # 1. Estimer NPK
        npk = estimer_NPK(
            sensor['ec_us_cm'],
            sensor['ph'],
            sensor['humidity_pct'],
            sensor['temperature_c'],
        )

        # 2. Recommandations ML
        reco = recommend(sensor, language='fr')

        # 3. Formater les cultures
        crops = reco.get('crops', [])[:5]
        crops_text = '\n'.join([
            f"  {i+1}. {c['name']} — score: {c.get('score', 0):.2f}"
            for i, c in enumerate(crops)
        ]) if crops else "Aucune culture trouvée"

        # 4. NPK formaté
        npk_text = (
            f"  N (Azote) estimé : {npk.get('N_kg_ha', 0):.0f} kg/ha\n"
            f"  P2O5 recommandé : {npk.get('P2O5_kg_ha', 0):.0f} kg/ha\n"
            f"  K2O recommandé   : {npk.get('K2O_kg_ha', 0):.0f} kg/ha"
        )

        # 5. Impact
        impact = reco.get('impact_text', '')
        impact_text = f"  {impact}" if impact else ""

        return {
            'success': True,
            'crops_top': crops_text,
            'npk_estime': npk_text,
            'impact': impact_text,
            'reco_full': reco,
            'npk_full': npk,
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"Erreur ML: {e}",
            'traceback': traceback.format_exc(),
        }


# ── Orchestrateur principal ─────────────────────────────────

def handle_conversation(messages, context_results=None):
    """
    Point d'entrée unique.
    
    Args:
        messages: liste des messages [{role, content}, ...]
        context_results: résultats de mission (dict) ou None
    
    Returns:
        dict avec reply, mode ('collect'|'explain'|'done'), etc.
    """
    # Construire le contexte mission si disponible
    mission_context = ""
    if context_results:
        waypoints = context_results.get('waypoints', [])
        if waypoints:
            wp = waypoints[-1]  # dernier waypoint
            sensor = wp.get('sensor', {})
            if sensor:
                mission_context = (
                    f"Contexte de la dernière analyse robot :\n"
                    f"  pH: {sensor.get('ph', '?')}\n"
                    f"  Humidité: {sensor.get('humidity_pct', '?')}%\n"
                    f"  Température: {sensor.get('temperature_c', '?')}°C\n"
                    f"  EC: {sensor.get('ec_us_cm', '?')} µS/cm\n"
                )

    # Messages système
    sys_msg = COLLECT_PROMPT
    if mission_context:
        sys_msg += f"\n\n{mission_context}"

    full_messages = [{"role": "system", "content": sys_msg}]

    # Ajouter l'historique (sauf les messages système précédents)
    for msg in messages:
        if msg.get('role') in ('user', 'assistant'):
            full_messages.append(msg)

    # Appel LLM
    result = _call_llm(full_messages)
    if 'error' in result:
        return result

    reply = result['reply']

    # Vérifier si le LLM a collecté assez d'infos
    collected = _parse_conseil(reply)
    if collected:
        # Lancer le pipeline ML
        ml_result = _run_ml(collected)
        if not ml_result['success']:
            return {'reply': f"❌ Erreur d'analyse: {ml_result['error']}", 'mode': 'error'}

        # Contexte utilisateur pour l'explication
        user_ctx = _build_user_context(collected)

        # Prompt d'explication
        explain_content = EXPLAIN_PROMPT.format(
            user_context=user_ctx,
            crops_top=ml_result['crops_top'],
            npk_estime=ml_result['npk_estime'],
            impact=ml_result['impact'],
        )

        # Appel LLM pour expliquer
        explain_msgs = [
            {"role": "system", "content": "Tu es un expert agronome africain."},
            {"role": "user", "content": explain_content},
        ]
        explain_result = _call_llm(explain_msgs, temperature=0.5)
        if 'error' in explain_result:
            return {'reply': f"❌ {explain_result['error']}", 'mode': 'error'}

        # Retourner la réponse finale avec les données ML
        # On enlève le [CONSEIL]... de la réponse pour le frontend
        clean_reply = re.sub(r'\[CONSEIL\]\{.*?\}', '', reply, flags=re.DOTALL).strip()

        return {
            'reply': explain_result['reply'],
            'mode': 'done',
            'collected': clean_reply,
            'ml_data': {
                'crops': ml_result.get('reco_full', {}).get('crops', []),
                'npk': ml_result.get('npk_full', {}),
            }
        }

    # Pas encore assez d'infos — continuer la collecte
    return {
        'reply': reply,
        'mode': 'collect',
    }
