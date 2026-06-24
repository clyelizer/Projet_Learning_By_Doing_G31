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
import time
import signal
import shutil
import pathlib
import subprocess
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, abort

# Ajouter src/ au path pour importer les modules
SRC_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))

from reco_engine import recommend, estimer_NPK, load_base_reference, generer_conseils_mission
from tts_engine import speak, get_available_engines, get_available_languages
from doctor import run_diagnostic

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent

app = Flask(__name__, static_folder='static', static_url_path='')

# Désactiver le cache des fichiers statiques (JS/CSS) pendant le développement
@app.after_request
def no_cache(response):
    if request.path.endswith(('.js', '.css', '.html')):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


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
    """Retourne recommandations ML + conseils LLM + TTS pour toute la mission."""
    lang = request.args.get('lang', 'fr')
    results = load_json('data/results.json')
    if not results:
        return jsonify([])

    waypoints = results.get('waypoints', [])
    output = []
    waypoints_ml = []

    for wp in waypoints:
        sensor = wp.get('sensor')
        if not sensor:
            continue

        # Pipeline ML
        try:
            reco = recommend(sensor, top_n=3)
        except Exception as e:
            reco = {'error': str(e)}

        # Photos existantes
        photos_dir = PROJECT_DIR / 'data' / 'photos'
        existing_photos = []
        for p in (wp.get('photos') or []):
            fname = os.path.basename(p)
            if (photos_dir / fname).exists():
                existing_photos.append(fname)

        entry = {
            'waypoint_id': wp.get('waypoint_id'),
            'sensor': sensor,
            'ml': reco,
            'photos': existing_photos[:1],
        }
        output.append(entry)
        waypoints_ml.append(entry)

    # Conseils LLM globaux
    conseils = generer_conseils_mission(waypoints_ml, language=lang)

    # TTS du resume global affiche (identique a l'ecran)
    tts_result = None
    texte_audio = conseils.get('resume_global') or conseils.get('audio_propice')
    if texte_audio:
        try:
            speak_result = speak(texte_audio, engine='auto', lang=lang)
            if 'path' in speak_result:
                # Ajouter une URL accessible
                audio_path = speak_result['path']
                audio_url = '/audio/' + os.path.basename(audio_path)
                tts_result = {
                    'path': audio_path,
                    'url': audio_url,
                    'engine': speak_result.get('engine'),
                }
        except Exception:
            pass

    return jsonify({
        'zones': output,
        'conseils': conseils,
        'tts': tts_result,
    })


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


# ── Conseil personnalisé (advisor) ────────────────────────

@app.route('/api/chat/conseil', methods=['POST'])
def api_chat_conseil():
    """
    Chat de conseil personnalisé.
    Le LLM pose des questions → collecte → pipeline ML → explication.
    """
    try:
        from advisor import handle_conversation
    except ImportError as e:
        return jsonify({'error': f'Module advisor manquant: {e}'}), 500

    data = request.get_json(silent=True) or {}
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': 'Aucun message'}), 400

    language = data.get('language', 'fr')

    # Contexte de la mission (résultats actuels)
    results = load_json('data/results.json')

    result = handle_conversation(messages, context_results=results)
    if 'error' in result:
        return jsonify({'error': result['error']}), 500

    return jsonify({
        'reply': result.get('reply', ''),
        'mode': result.get('mode', 'collect'),
        'collected': result.get('collected', ''),
        'ml_data': result.get('ml_data'),
    })


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


# ── API: Recommandation interactive ─────────────────────────────

@app.route('/api/reco/analyze', methods=['POST'])
def api_reco_analyze():
    """Analyse interactive: 4 mesures -> NPK + classement + impact par culture."""
    data = request.get_json(silent=True) or {}
    sensor_data = {
        'ec_us_cm': data.get('ec_us_cm', 500),
        'ph': data.get('ph', 7.0),
        'humidity_pct': data.get('humidity_pct', 50),
        'temperature_c': data.get('temperature_c', 25),
    }
    top_n = data.get('top_n', 5)
    result = recommend(sensor_data, top_n=top_n)
    return jsonify(result)


@app.route('/api/base-reference')
def api_base_reference():
    """Retourne la base de reference avec filtres optionnels."""
    base = load_base_reference()
    zone = request.args.get('zone')
    search = request.args.get('search', '').lower()

    cultures = base.get('cultures', [])
    if zone:
        cultures = [c for c in cultures if c.get('zone', '') == zone]
    if search:
        cultures = [
            c for c in cultures
            if search in c.get('culture', '').lower()
            or search in c.get('nom_scientifique', '').lower()
        ]

    return jsonify({
        'metadata': base.get('metadata'),
        'cultures': cultures,
        'count': len(cultures),
    })


@app.route('/api/ml/models')
def api_ml_models():
    """Infos sur les modeles ML disponibles."""
    model_dir = SCRIPT_DIR.parent / 'ml' / '02_models'
    models = {}
    for f in sorted(os.listdir(str(model_dir))) if model_dir.exists() else []:
        if f.endswith('.pkl'):
            fpath = model_dir / f
            size_kb = round(fpath.stat().st_size / 1024, 1)
            models[f] = {'size_kb': size_kb}
    return jsonify({'models': models, 'count': len(models)})


@app.route('/api/ml/figures')
def api_ml_figures():
    """Liste les figures disponibles."""
    fig_dir = SCRIPT_DIR.parent / 'ml' / '04_figures'
    figures = []
    if fig_dir.exists():
        for f in sorted(fig_dir.iterdir()):
            if f.is_file() and f.suffix == '.png':
                figures.append({'name': f.name, 'size_kb': round(f.stat().st_size / 1024, 1)})
        dep_dir = fig_dir / 'shap_dependence'
        if dep_dir.exists():
            for f in sorted(dep_dir.iterdir()):
                if f.suffix == '.png':
                    figures.append({'name': f'shap_dependence/{f.name}',
                                    'size_kb': round(f.stat().st_size / 1024, 1)})
    return jsonify({'figures': figures, 'count': len(figures)})


@app.route('/api/ml/figures/<path:filename>')
def api_ml_figure(filename):
    """Sert une figure PNG."""
    fig_dir = str(SCRIPT_DIR.parent / 'ml' / '04_figures')
    return send_from_directory(fig_dir, filename)


@app.route('/api/ml/metrics')
def api_ml_metrics():
    """Retourne les metriques d'entrainement."""
    path = SCRIPT_DIR.parent / 'ml' / '03_training' / 'metriques.txt'
    if path.exists():
        return jsonify({'content': path.read_text()})
    return jsonify({'content': None})


@app.route('/api/ml/predict', methods=['POST'])
def api_ml_predict():
    """Classement avec N/P/K personnalises (mode explicabilite)."""
    data = request.get_json(silent=True) or {}
    # Construire les mesures avec les valeurs fournies
    sensor_data = {
        'ec_us_cm': 500,  # valeur par defaut
        'ph': data.get('pH', 7.0),
        'humidity_pct': data.get('humidite', 50),
        'temperature_c': data.get('temperature', 25),
    }
    # On passe directement N, P2O5, K2O fournis par l'utilisateur
    # en surchargeant l'estimation NPK
    from reco_engine import _get_recommendations
    mesures = {
        "pH": data.get('pH', 7.0),
        "humidite": data.get('humidite', 50),
        "temperature": data.get('temperature', 25),
        "N": data.get('N', 50),
        "P2O5": data.get('P2O5', 30),
        "K2O": data.get('K2O', 20),
    }
    reco = _get_recommendations(mesures)
    ranking = reco.get("ranking", [])
    # Generer impact chart pour top 3
    from reco_engine import generer_impact_culture
    classement = []
    for i, c in enumerate(ranking[:5]):
        entry = dict(c)
        if i < 3:
            chart = generer_impact_culture(
                c["culture"], c["score"],
                c.get("scores_details", {}),
                c.get("parametres_match", []),
                c.get("parametres_limites", []),
                c.get("parametres_hors_plage", []),
            )
            entry["impact_chart_b64"] = chart
        classement.append(entry)
    return jsonify({
        "classement": classement,
        "top_culture": reco.get("top_culture"),
        "top_score": reco.get("top_score"),
    })


# ── Audio ────────────────────────────────────────────────────────

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Sert les fichiers audio generes par TTS."""
    audio_dir = PROJECT_DIR / 'data' / 'audio'
    if not (audio_dir / filename).exists():
        abort(404)
    return send_from_directory(str(audio_dir), filename)


# ── Photos ────────────────────────────────────────────────────────

@app.route('/photos/<filename>')
def serve_photo(filename):
    photos_dir = PROJECT_DIR / 'data' / 'photos'
    if not (photos_dir / filename).exists():
        abort(404)
    return send_from_directory(str(photos_dir), filename)


# ── Robot Doctor ──────────────────────────────────────────────────

@app.route('/api/doctor/check', methods=['GET', 'POST'])
def api_doctor_check():
    """
    Exécute un diagnostic complet du robot.
    GET : diagnostic seul (pas de LLM, pas d'auto-heal)
    POST : options avec_llm et auto_heal dans le body JSON
    """
    with_llm = False
    auto_heal = False
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        with_llm = data.get('with_llm', False)
        auto_heal = data.get('auto_heal', False)

    result = run_diagnostic(with_llm=with_llm, auto_heal=auto_heal)
    return jsonify(result)


@app.route('/api/doctor/heal', methods=['POST'])
def api_doctor_heal():
    """
    Exécute les correctifs automatiques pour les checks en erreur
    (sans refaire un diagnostic complet).
    Se base sur le dernier rapport sauvegardé.
    """
    # Charger le dernier rapport pour récupérer les checks
    report_dir = PROJECT_DIR / 'data' / 'doctor'
    latest = report_dir / 'latest.md'
    if not latest.exists():
        # Faire un diagnostic rapide d'abord
        result = run_diagnostic(with_llm=False, auto_heal=True)
        return jsonify(result)

    # Relancer diagnostic avec auto-heal
    result = run_diagnostic(with_llm=False, auto_heal=True)
    return jsonify(result)


@app.route('/api/doctor/report')
def api_doctor_report():
    """Retourne le dernier rapport de diagnostic."""
    report_dir = PROJECT_DIR / 'data' / 'doctor'
    latest = report_dir / 'latest.md'
    if latest.exists():
        try:
            content = Path(latest).read_text()
            return jsonify({'report': content, 'path': str(latest)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'report': None, 'path': None})


@app.route('/api/doctor/history')
def api_doctor_history():
    """Liste les rapports de diagnostic disponibles."""
    report_dir = PROJECT_DIR / 'data' / 'doctor'
    if not report_dir.exists():
        return jsonify({'reports': []})
    reports = []
    for f in sorted(report_dir.iterdir(), reverse=True):
        if f.suffix == '.md' and f.name != 'latest.md':
            reports.append({
                'name': f.name,
                'date': time.ctime(f.stat().st_mtime) if hasattr(time, 'ctime') else '',
                'size': f.stat().st_size,
            })
    return jsonify({'reports': reports})


@app.route('/api/doctor/report/download')
def api_doctor_report_download():
    """Télécharge le dernier rapport en tant que fichier .md."""
    report_dir = PROJECT_DIR / 'data' / 'doctor'
    latest = report_dir / 'latest.md'
    if latest.exists():
        from flask import Response
        content = latest.read_bytes()
        return Response(content, mimetype='text/markdown',
                        headers={'Content-Disposition': 'attachment; filename=diagnostic_agroscan.md'})
    abort(404)


# ── Mission ─────────────────────────────────────────────────────

BACKUP_DIR = PROJECT_DIR / 'config' / 'backups'
MISSION_DIR = PROJECT_DIR / 'src'


@app.route('/api/mission/config')
def api_mission_config():
    """Liste les fichiers de configuration disponibles."""
    config_dir = PROJECT_DIR / 'config'
    files = {}
    for fname in ['map.json', 'calibration.json', 'config.json']:
        fpath = config_dir / fname
        if fpath.exists():
            files[fname] = {
                'size': fpath.stat().st_size,
                'modified': time.ctime(fpath.stat().st_mtime),
                'content': json.loads(fpath.read_text()) if fname != 'calibration.json' else None,
            }
    return jsonify(files)


@app.route('/api/mission/config/upload', methods=['POST'])
def api_mission_config_upload():
    """Upload d'un fichier de configuration (map.json ou calibration.json)."""
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    file = request.files['file']
    if file.filename not in ('map.json', 'calibration.json', 'config.json'):
        return jsonify({'error': f'Nom invalide: {file.filename}. Utilisez map.json, calibration.json ou config.json'}), 400

    config_dir = PROJECT_DIR / 'config'
    dest = config_dir / file.filename

    # Backup auto avant écrasement
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        ts = time.strftime('%Y%m%d_%H%M%S')
        backup_name = f'{file.filename}.{ts}.backup'
        shutil.copy2(str(dest), str(BACKUP_DIR / backup_name))

    file.save(str(dest))
    return jsonify({'success': True, 'filename': file.filename, 'size': dest.stat().st_size})


@app.route('/api/mission/backup', methods=['POST'])
def api_mission_backup():
    """Crée une backup de tous les fichiers de config."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime('%Y%m%d_%H%M%S')
    created = []
    for fname in ['map.json', 'calibration.json', 'config.json']:
        src = PROJECT_DIR / 'config' / fname
        if src.exists():
            backup_name = f'{fname}.{ts}.backup'
            shutil.copy2(str(src), str(BACKUP_DIR / backup_name))
            created.append(backup_name)
    return jsonify({'success': True, 'backups': created, 'timestamp': ts})


@app.route('/api/mission/backups')
def api_mission_backups():
    """Liste les backups disponibles."""
    if not BACKUP_DIR.exists():
        return jsonify({'backups': []})
    backups = []
    for f in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if f.suffix == '.backup':
            parts = f.name.split('.')
            original = parts[0] + '.json' if len(parts) >= 2 else f.name
            ts = parts[1] if len(parts) >= 3 else ''
            backups.append({
                'name': f.name,
                'original': original,
                'timestamp': ts,
                'size': f.stat().st_size,
                'modified': time.ctime(f.stat().st_mtime),
            })
    return jsonify({'backups': backups})


@app.route('/api/mission/restore', methods=['POST'])
def api_mission_restore():
    """Restaure une backup."""
    data = request.get_json(silent=True) or {}
    backup_name = data.get('backup')
    if not backup_name:
        return jsonify({'error': 'Nom de backup requis'}), 400
    backup_path = BACKUP_DIR / backup_name
    if not backup_path.exists():
        return jsonify({'error': f'Backup introuvable: {backup_name}'}), 404

    # Déterminer le nom original
    original_name = backup_name.split('.')[0] + '.json'
    dest = PROJECT_DIR / 'config' / original_name

    # Backup de l'actuel avant restauration
    if dest.exists():
        ts = time.strftime('%Y%m%d_%H%M%S')
        shutil.copy2(str(dest), str(BACKUP_DIR / f'{original_name}.{ts}.pre-restore.backup'))

    shutil.copy2(str(backup_path), str(dest))
    return jsonify({'success': True, 'restored': original_name, 'from': backup_name})


@app.route('/api/mission/launch', methods=['POST'])
def api_mission_launch():
    """Lance une mission en arrière-plan."""
    data = request.get_json(silent=True) or {}
    dry_run = data.get('dry_run', False)

    # Vérifier qu'aucune mission n'est déjà en cours
    if _is_mission_running():
        return jsonify({'error': 'Une mission est déjà en cours'}), 409

    cmd = [sys.executable, 'main.py']
    if dry_run:
        cmd.append('--dry-run')

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(MISSION_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Sauvegarder le PID
        pid_file = PROJECT_DIR / 'data' / 'mission.pid'
        pid_file.write_text(str(proc.pid))
        return jsonify({'success': True, 'pid': proc.pid, 'dry_run': dry_run})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mission/status')
def api_mission_status():
    """Vérifie l'état de la mission en cours."""
    pid_file = PROJECT_DIR / 'data' / 'mission.pid'
    running = False
    pid = None
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)  # Signal 0 = test existence
            running = True
        except OSError:
            # Process mort, nettoyer
            pid_file.unlink(missing_ok=True)

    # Derniers résultats
    results = None
    results_path = PROJECT_DIR / 'data' / 'results.json'
    if results_path.exists():
        try:
            results = json.loads(results_path.read_text())
        except Exception:
            pass

    return jsonify({
        'running': running,
        'pid': pid,
        'results': results,
    })


@app.route('/api/mission/stop', methods=['POST'])
def api_mission_stop():
    """Arrête la mission en cours."""
    pid_file = PROJECT_DIR / 'data' / 'mission.pid'
    if not pid_file.exists():
        return jsonify({'error': 'Aucune mission en cours'}), 404
    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        pid_file.unlink(missing_ok=True)
        return jsonify({'success': True, 'pid': pid})
    except ProcessLookupError:
        pid_file.unlink(missing_ok=True)
        return jsonify({'success': True, 'pid': pid, 'note': 'Déjà terminée'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _is_mission_running():
    """Vérifie si une mission est en cours (interne)."""
    pid_file = PROJECT_DIR / 'data' / 'mission.pid'
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        pid_file.unlink(missing_ok=True)
        return False


# ── Email config (notification IP au boot) ─────────────────────
EMAIL_CONFIG_PATH = PROJECT_DIR / 'config' / 'email_config.json'


def _load_email_config():
    if not EMAIL_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(EMAIL_CONFIG_PATH.read_text())
    except Exception:
        return {}


@app.route('/api/mission/email-config', methods=['GET', 'POST'])
def api_email_config():
    if request.method == 'GET':
        cfg = _load_email_config()
        # Masquer le mdp dans la réponse
        cfg.pop('smtp_password', None)
        cfg['_comment'] = 'Sauvegarder pour activer l\'envoi IP au boot'
        return jsonify(cfg)

    data = request.get_json(silent=True) or {}
    cfg = {
        'smtp_server': data.get('smtp_server', 'smtp.gmail.com'),
        'smtp_port': int(data.get('smtp_port', 587)),
        'smtp_user': data.get('smtp_user', ''),
        'smtp_password': data.get('smtp_password', ''),
        'recipient_email': data.get('recipient_email', ''),
    }
    EMAIL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    EMAIL_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    return jsonify({'success': True, 'message': 'Configuration email sauvegardée'})


# ── Map JSON (GET + PUT) ──────────────────────────────────
MAP_PATH = PROJECT_DIR / 'config' / 'map.json'


@app.route('/api/mission/map', methods=['GET', 'POST'])
def api_mission_map():
    if request.method == 'GET':
        if MAP_PATH.exists():
            try:
                return jsonify(json.loads(MAP_PATH.read_text()))
            except Exception:
                pass
        return jsonify({'table': {'width_cm': 150, 'height_cm': 100}, 'waypoints': [], 'start': {'x': 10, 'y': 10, 'heading_deg': 0}})
    data = request.get_json(silent=True) or {}
    MAP_PATH.write_text(json.dumps(data, indent=2))
    return jsonify({'success': True})


@app.route('/api/mission/test-email', methods=['POST'])
def api_test_email():
    """Teste l'envoi d'email avec la config actuelle."""
    import subprocess
    script = PROJECT_DIR / 'tools' / 'send_ip_email.py'
    if not script.exists():
        return jsonify({'error': 'Script introuvable'}), 500
    try:
        result = subprocess.run(
            [sys.executable, str(script), '--test'],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return jsonify({'success': True, 'output': result.stdout})
        else:
            return jsonify({'error': result.stderr.strip() or 'Échec silencieux'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout (30s) — Vérifie SMTP'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── IP locale (affichée dans Mission) ─────────────────────────
@app.route('/api/network/ip')
def api_network_ip():
    ip = _get_local_ip()
    import socket
    return jsonify({
        'ip': ip,
        'hostname': socket.gethostname(),
        'url': f'http://{ip}:5000',
        'mdns': f'http://{socket.gethostname()}.local:5000',
    })


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
        s.connect(('8.8.8.8', 80))
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
    print("  🌱 AGROSCAN — SPA")
    print("=" * 60)
    print(f"  Local    : http://127.0.0.1:{PORT}")
    print(f"  Réseau   : http://{local_ip}:{PORT}")
    print("=" * 60)
    print()

    app.run(host=HOST, port=PORT, debug=True, use_reloader=False)
