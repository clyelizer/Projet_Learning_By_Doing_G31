#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moteur de recommandations agricoles complet.

Pipeline :
  mesures robot (EC, pH, T, humidite)
    → estimer_NPK()            → N, P2O5, K2O estimes (formules pedotransfert)
    → get_recommendations()    → classement cultures (base reference 41 cultures)
    → generer_impact_culture() → waterfall impact parametre PAR culture classee

Usage:
    python reco_engine.py          # test avec donnees simulees
"""

import base64
import io
import json
import os
import sys
import joblib
from typing import Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Ajouter src/ml/05_recommendation au path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ML_DIR = os.path.join(_SCRIPT_DIR, 'ml')
sys.path.insert(0, os.path.join(_ML_DIR, '05_recommendation'))

from recommendation_ranking import (
    get_recommendations as _get_recommendations,
    rank_cultures as _rank_cultures,
    load_base_reference,
)

# ── Chemin vers les modeles ML entraines ─────────────────────────
_BEST_DIR = os.path.join(_ML_DIR, '02_models', 'best')

# ── Cache des modeles (singleton simple) ──────────────────────────
_ml_models_cache = {}

def _get_ml_model(path):
    """Charge un modele .pkl avec cache simple."""
    if path not in _ml_models_cache:
        if not os.path.exists(path):
            return None
        _ml_models_cache[path] = joblib.load(path)
    return _ml_models_cache[path]

# Valeur par defaut pour EC_approx (median du dataset d'entrainement)
# Utilisee quand les donnees iSDA ne sont pas disponibles en inference.
_DEFAULT_EC_APPROX = 0.72  # dS/m


def estimer_NPK_ML(pH: float, temperature: float, humidite: float) -> dict:
    """
    Estime N, P, K (kg/ha elementaire) via les regresseurs RF entraines.
    Retourne N_kg/ha, P_mg/kg, K_mg/kg + methodes.
    Retourne None si les modeles ne sont pas disponibles.
    """
    scaler = _get_ml_model(os.path.join(_BEST_DIR, 'scaler_regression_N.pkl'))
    if scaler is None:
        return None

    X = np.array([[pH, temperature, humidite]])
    import pandas as pd
    _SCALER_REG_COLS = ['pH', 'temperature', 'humidite']
    X_df = pd.DataFrame(X, columns=_SCALER_REG_COLS)
    X_scaled = scaler.transform(X_df)

    N_model = _get_ml_model(os.path.join(_BEST_DIR, 'regressor_N.pkl'))
    P_model = _get_ml_model(os.path.join(_BEST_DIR, 'regressor_P.pkl'))
    K_model = _get_ml_model(os.path.join(_BEST_DIR, 'regressor_K.pkl'))
    if N_model is None or P_model is None or K_model is None:
        return None

    N_kg = max(0, round(float(N_model.predict(X_scaled)[0]), 1))
    P_kg = max(5, round(float(P_model.predict(X_scaled)[0]), 1))
    K_kg = max(10, round(float(K_model.predict(X_scaled)[0]), 1))

    return {
        "N_kg_ha": N_kg, "P_mg_kg": P_kg, "K_mg_kg": K_kg,
        "methodes": {"N": "RF Regressor", "P": "RF Regressor", "K": "RF Regressor"},
    }


def predire_culture_ML(pH: float, temperature: float, humidite: float,
                       N: float, P: float, K: float) -> Optional[dict]:
    """
    Predire la culture via le classifieur RF.
    Construit les 13 features attendues (7 raw + 6 engineered).
    Retourne None si le modele n'est pas disponible.
    """
    clf = _get_ml_model(os.path.join(_BEST_DIR, 'classifier.pkl'))
    scaler = _get_ml_model(os.path.join(_BEST_DIR, 'scaler_classification.pkl'))
    le = _get_ml_model(os.path.join(_BEST_DIR, 'label_encoder_culture.pkl'))
    if clf is None or scaler is None or le is None:
        return None

    ratio_N_P = N / P if P > 0 else 0.0
    ratio_N_K = N / K if K > 0 else 0.0
    ratio_P_K = P / K if K > 0 else 0.0
    max_npk = max(abs(N), abs(P), abs(K), 1e-10)
    score_balance = 1 - (
        abs(abs(N) / max_npk - 0.5) +
        abs(abs(P) / max_npk - 0.3) +
        abs(abs(K) / max_npk - 0.2)
    ) / 2
    EC_approx = _DEFAULT_EC_APPROX
    pH_times_EC = pH * EC_approx

    feats = np.array([[
        N, P, K, temperature, humidite, pH, 0.0,
        ratio_N_P, ratio_N_K, ratio_P_K,
        score_balance, EC_approx, pH_times_EC,
    ]])
    import pandas as pd
    _SCALER_CLF_COLS = [
        'N', 'P', 'K', 'temperature', 'humidite', 'pH', 'precipitation',
        'ratio_N_P', 'ratio_N_K', 'ratio_P_K', 'score_NPK_balance', 'EC_approx', 'pH_times_EC',
    ]
    feats_df = pd.DataFrame([feats[0]], columns=_SCALER_CLF_COLS)
    feats_scaled = scaler.transform(feats_df)
    pred_idx = clf.predict(feats_scaled)[0]
    probas = clf.predict_proba(feats_scaled)[0]

    culture = str(le.inverse_transform([pred_idx])[0])
    top3_idx = np.argsort(probas)[::-1][:3]

    return {
        "culture": culture,
        "confiance": round(float(probas[pred_idx]), 4),
        "top_3": [{"culture": str(le.classes_[i]), "probabilite": round(float(probas[i]), 4)}
                  for i in top3_idx],
    }


# ── Estimation NPK (formules pedotransfert) ─────────────────────

_POIDS_PARAM = {"pH": 0.30, "temperature": 0.20, "humidite": 0.20,
                "N": 0.15, "P2O5": 0.10, "K2O": 0.05}


def estimer_NPK(EC: float, pH: float, humidite: float,
                temperature: float) -> dict:
    """
    Estime N, P2O5, K2O (kg/ha) depuis les 4 mesures du robot.

    Formules issues de la litterature:
      N  → Mirzakhaninafchi 2022 (R²=0.990), fallback Koumanov 2001
      P  → MSU Extension (optimum pH 6.0-7.0)
      K  → Mazur 2022 (r=0.8)
    """
    # ── AZOTE (N) ────────────────────────────────────────────
    EC_msm = EC * 100  # dS/m → mS/m
    a, b_lin, c = 0.0007, 0.0107, -EC_msm + 0.208
    discriminant = b_lin**2 - 4*a*c
    if discriminant >= 0:
        N_kg_ha = max(0, (-b_lin + np.sqrt(discriminant)) / (2*a))
    else:
        N_mgkg = max(0, 84.801 * EC * EC - 10.059 * EC)
        N_kg_ha = N_mgkg * 2

    if temperature > 35 or temperature < 10:
        N_kg_ha *= 0.7

    # ── PHOSPHORE (P) ────────────────────────────────────────
    if 6.0 <= pH <= 7.0:
        P_mgkg = 50
    elif pH < 6.0:
        P_mgkg = max(5, 50 - (6.0 - pH) * 30)
    else:
        P_mgkg = max(5, 50 - (pH - 7.0) * 30)

    # ── POTASSIUM (K) ────────────────────────────────────────
    K_mgkg = max(10, 15 + EC * 80)

    N_kg = round(N_kg_ha, 1)
    P2O5_kg = round(P_mgkg * 2.29, 1)
    K2O_kg = round(K_mgkg * 1.205, 1)

    return {
        "N_kg_ha": N_kg,
        "P2O5_kg_ha": P2O5_kg,
        "K2O_kg_ha": K2O_kg,
        "N_mg_kg": round(N_kg / 2, 1),
        "P_mg_kg": round(P_mgkg, 1),
        "K_mg_kg": round(K_mgkg, 1),
        "methodes": {
            "N": "Mirzakhaninafchi 2022 (R²=0.990)",
            "P": "MSU Extension (pH optimum 6.0-7.0)",
            "K": "Mazur 2022 (r=0.8)",
        }
    }


# ── Graphique d'impact parametre par culture ──────────────────

def generer_impact_culture(nom_culture: str, score: float,
                           scores_details: dict,
                           parametres_match: list,
                           parametres_limites: list,
                           parametres_hors_plage: list) -> Optional[str]:
    """
    Genere un barplot horizontal montrant l'impact de chaque parametre
    sur le score d'une culture donnee.

    Returns:
        str — PNG en base64, ou None si erreur.
    """
    if not scores_details:
        return None

    # Filtrer les parametres non nuls et les trier par impact descendant
    params = [(k, v) for k, v in scores_details.items()
              if v is not None and k in _POIDS_PARAM]
    if not params:
        return None

    params.sort(key=lambda x: x[1], reverse=True)
    labels = [p[0] for p in params]
    values = [p[1] for p in params]

    # Couleurs: vert (>=0.5 = bon), orange (0.25-0.5 = limite), rouge (<0.25)
    colors = []
    for v in values:
        if v >= 0.5:
            colors.append('#2ecc71')
        elif v >= 0.25:
            colors.append('#f39c12')
        else:
            colors.append('#e74c3c')

    fig, ax = plt.subplots(figsize=(7, 3.2))
    bars = ax.barh(range(len(values)), values, color=colors,
                   edgecolor='white', linewidth=0.5, height=0.6)

    ax.set_yticks(range(len(values)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 1.15)
    ax.set_xlabel('Compatibilite (0 = hors plage, 1 = optimal)', fontsize=8)
    ax.set_title(f"Impact des parametres — {nom_culture} (score: {score:.0f}%)",
                 fontsize=10, fontweight='bold')
    ax.axvline(0.5, color='gray', linewidth=0.5, linestyle='--', alpha=0.5)

    # Valeurs sur les barres
    for i, (bar, val) in enumerate(zip(bars, values)):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                f'{val:.0%}', va='center', fontsize=7, color='#333')

    # Legende en haut
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', label='Optimal (>=50%)'),
        Patch(facecolor='#f39c12', label='Limite (25-50%)'),
        Patch(facecolor='#e74c3c', label='Hors plage (<25%)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=6,
              framealpha=0.8)

    # Annotations dessous: match/limite/hors_plage
    annotations = []
    if parametres_match:
        annotations.append(f"✅ {', '.join(parametres_match)}")
    if parametres_limites:
        annotations.append(f"⚠️ {', '.join(parametres_limites)}")
    if parametres_hors_plage:
        annotations.append(f"❌ {', '.join(parametres_hors_plage)}")

    if annotations:
        fig.text(0.02, -0.05, ' | '.join(annotations), fontsize=7,
                 color='#555', wrap=True)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    return base64.b64encode(buf.read()).decode('utf-8')


# ── Pipeline complet ───────────────────────────────────────────

def recommend(sensor_data: dict, language: str = 'fr',
              top_n: int = 5) -> dict:
    """
    Pipeline complet de recommandation agricole.

    Args:
        sensor_data: dict — {humidity_pct, temperature_c, ec_us_cm, ph}
        language: reserve
        top_n: nb de cultures avec graphique d'impact (max 8)

    Returns:
        dict avec mesures_brutes, npk_estimes, classement[],
        chaque entree du classement contient un "impact_chart_b64".
    """
    EC = float(sensor_data.get('ec_us_cm', 0)) / 1000
    pH = float(sensor_data.get('ph', 7.0))
    humidite = float(sensor_data.get('humidity_pct', 50))
    temperature = float(sensor_data.get('temperature_c', 25))

    # Etape 1: NPK — ML en priorite, fallback formules pedotransfert
    ml_npk = estimer_NPK_ML(pH, temperature, humidite)
    if ml_npk:
        npk = {
            "N_kg_ha": ml_npk["N_kg_ha"],
            "N_mg_kg": ml_npk["N_kg_ha"] / 2,
            "P_mg_kg": ml_npk["P_mg_kg"],
            "K_mg_kg": ml_npk["K_mg_kg"],
            "P2O5_kg_ha": round(ml_npk["P_mg_kg"] * 2.29, 1),
            "K2O_kg_ha": round(ml_npk["K_mg_kg"] * 1.205, 1),
            "methode": "ML",
        }
    else:
        npk = estimer_NPK(EC, pH, humidite, temperature)
        npk["methode"] = "pedotransfert"

    # Valeurs N, P, K elementaires pour le classifieur ML
    N_el = npk["N_kg_ha"]
    P_el = npk["P_mg_kg"]
    K_el = npk["K_mg_kg"]

    # Etape 2: classement (base reference 41 cultures + scoring ML optionnel)
    mesures_completes = {
        "EC": EC, "pH": pH, "humidite": humidite, "temperature": temperature,
        "N": npk["N_kg_ha"], "P2O5": npk["P2O5_kg_ha"], "K2O": npk["K2O_kg_ha"],
    }
    reco = _get_recommendations(mesures_completes)
    ranking = reco.get("ranking", [])

    # Etape 2b: prediction ML de la culture (si modele disponible)
    ml_culture = predire_culture_ML(pH, temperature, humidite, N_el, P_el, K_el)

    # Etape 3: generer impact chart pour chaque culture du top
    classement = []
    for i, c in enumerate(ranking):
        entry = dict(c)  # copie
        if i < top_n:
            chart = generer_impact_culture(
                c["culture"], c["score"],
                c.get("scores_details", {}),
                c.get("parametres_match", []),
                c.get("parametres_limites", []),
                c.get("parametres_hors_plage", []),
            )
            entry["impact_chart_b64"] = chart
        else:
            entry["impact_chart_b64"] = None
        classement.append(entry)

    result = {
        "mesures_brutes": {
            "ec_ds_m": round(EC, 3),
            "ec_us_cm": round(EC * 1000, 1),
            "ph": pH,
            "humidite_pct": humidite,
            "temperature_c": temperature,
        },
        "npk_estimes": npk,
        "classement": classement,
        "top_culture": reco.get("top_culture"),
        "top_score": reco.get("top_score"),
        "fertilisation": reco.get("fertilisation"),
        "ml_culture": ml_culture,
    }

    return result



# ── Generation de conseils LLM ──────────────────────────────

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def generer_conseils_mission(waypoints_data: list, language: str = "fr") -> dict:
    """
    Genere des conseils agricoles clairs via Groq Llama pour toute une mission.

    Args:
        waypoints_data: list[dict] — chaque entree a les champs:
            {waypoint_id, sensor: {humidity_pct, temperature_c, ec_us_cm, ph},
             ml: {top_culture, top_score, npk, fertilisation}}
        language: "fr" ou "en"

    Returns:
        dict avec "global_summary", "par_zone" (conseils par wp), "audio_text"
    """
    from dotenv import load_dotenv
    load_dotenv()
    import requests

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY non configuree"}

    # Construire le contexte de la mission
    zones_text = ""
    for wp in waypoints_data:
        s = wp.get("sensor", {})
        ml = wp.get("ml", {})
        npk = ml.get("npk_estimes", {})
        zones_text += f"\nZone {wp['waypoint_id']}:\n"
        zones_text += f"  Mesures: pH={s.get('ph')}, EC={s.get('ec_us_cm')}uS/cm, Humidite={s.get('humidity_pct')}%, Temp={s.get('temperature_c')}C\n"
        zones_text += f"  NPK estimes: N={npk.get('N_kg_ha')}, P2O5={npk.get('P2O5_kg_ha')}, K2O={npk.get('K2O_kg_ha')} kg/ha\n"
        zones_text += f"  Top culture: {ml.get('top_culture')} (score {ml.get('top_score')}%)\n"
        if ml.get("fertilisation"):
            zones_text += f"  Fertilisation recommandee: {ml['fertilisation'].get('NPK_recommandation', 'N/A')}\n"

    # ── Construire les prompts selon la langue ────────────────────────

    # Langues supportées par le LLM (Groq Llama)
    lang_config = {
        'fr': {'name': 'français', 'resume': 'resume_global', 'culture': 'culture_conseillee', 'explication': 'explication', 'action': 'action', 'urgence': 'urgence', 'audio': 'audio_propice', 'urg_values': {'haute':'Haute','moyenne':'Moyenne','faible':'Faible'}},
        'en': {'name': 'English', 'resume': 'resume_global', 'culture': 'culture_conseillee', 'explication': 'explication', 'action': 'action', 'urgence': 'urgence', 'audio': 'audio_propice', 'urg_values': {'haute':'High','moyenne':'Medium','faible':'Low'}},
        'ha': {'name': 'Hausa', 'resume': 'takaitaccen_bayani', 'culture': 'shawarar_noma', 'explication': 'bayani', 'action': 'mataki', 'urgence': 'gaggawa', 'audio': 'sauti_magana', 'urg_values': {'haute':'Matsananci','moyenne':'Matsakaici','faible':'Kadan'}},
        'sw': {'name': 'Kiswahili', 'resume': 'muhtasari', 'culture': 'zoezi_la_kilimo', 'explication': 'maelezo', 'action': 'hatua', 'urgence': 'dharura', 'audio': 'sauti_ya_kusikiliza', 'urg_values': {'haute':'Kubwa','moyenne':'Kati','faible':'Ndogo'}},
        'ar': {'name': 'العربية', 'resume': 'ملخص_عام', 'culture': 'المحصول_المقترح', 'explication': 'شرح', 'action': 'إجراء', 'urgence': 'استعجال', 'audio': 'نص_صوتي', 'urg_values': {'haute':'عالي','moyenne':'متوسط','faible':'منخفض'}},
    }

    cfg = lang_config.get(language, lang_config['fr'])

    # Construction du prompt system/langue
    if language == 'ha':
        system_prompt = (
            "Kai ƙwararren mashawarcin aikin gona ne a Afirka (Sahel, yankuna masu zafi).\n"
            "Bincika bayanan ƙasa da aka kawo ka ka ba da shawara a sarari, mai amfani da kuma harshe mai sauki ga manomi.\n\n"
            "DOKOKI:\n"
            "- Amsa KAWAI a cikin JSON mai inganci, ba tare da rubutu a gaba ko baya ba.\n"
            "- Ka zama mai takamaiman: ambaci sunayen amfanin gona, adadi (kg/ha), ayyuka na gaske.\n"
            "- Idan akwai haɗari (pH mai tsanani, gishiri), bayyana dalili da abin da za a yi.\n"
            "- Ga kowane yanki, ba da shawara 1-2 masu amfani.\n"
            "- Ka ƙare da taƙaitaccen bayani game da dukan gonar.\n"
        )
    elif language == 'sw':
        system_prompt = (
            "Wewe ni mshauri mtaalamu wa kilimo barani Afrika (Sahel, maeneo ya kitropiki).\n"
            "Chambua data ya udongo uliotolewa na toa ushauri wazi, wa vitendo, kwa lugha rahisi kwa mkulima.\n\n"
            "KANUNI:\n"
            "- Jibu KWA JSON pekee, bila maandishi kabla au baada.\n"
            "- Kuwa mahususi: taja mazao, kiasi (kg/ha), vitendo madhubuti.\n"
            "- Ikiwa thamani ni hatari (pH kali, chumvi), eleza kwa nini na nini cha kufanya.\n"
            "- Kwa kila eneo, toa ushauri 1-2 wa vitendo.\n"
            "- Malizia kwa muhtasari wa shamba zima.\n"
        )
    elif language == 'ar':
        system_prompt = (
            "أنت خبير استشاري زراعي متخصص في أفريقيا (الساحل، المناطق الاستوائية).\n"
            "قم بتحليل بيانات التربة المقدمة وقدم نصائح واضحة وعملية بلغة بسيطة للمزارع.\n\n"
            "القواعد:\n"
            "- أجب فقط بصيغة JSON صالحة، دون أي نص قبلها أو بعدها.\n"
            "- كن محددًا: اذكر أسماء المحاصيل والكميات (كغم/هكتار) والإجراءات الملموسة.\n"
            "- إذا كانت القيمة خطيرة (حموضة شديدة، ملوحة)، اشرح السبب وماذا تفعل.\n"
            "- لكل منطقة، قدم نصيحة عملية واحدة أو اثنتين.\n"
            "- اختتم بملخص عام لجميع الحقل.\n"
        )
    elif language == 'en':
        system_prompt = (
            "You are an expert agricultural advisor for Africa (Sahel, tropical zones).\n"
            "Analyze the provided soil data and give DETAILED, practical advice in simple language.\n\n"
            "RULES:\n"
            "- Reply ONLY in valid JSON, no text before or after.\n"
            "- For EACH zone, give ACTIONABLE advice, not a soil description.\n"
            "- Explain EXACTLY what to do: which crop to plant, when, with which fertilizers (kg/ha), which soil amendments (lime, compost, etc.), which farming techniques.\n"
            "- If EC is high (salinity), explain how to leach the soil. If pH is acidic, how much lime. If pH is alkaline, what organic matter to add.\n"
            "- If N/P/K is low, suggest SPECIFIC fertilizers (NPK 15-15-15, urea, DAP, KCl) with doses in kg/ha.\n"
            "- The global summary must be a 5-8 sentence paragraph synthesizing ALL zones.\n"
            "- The audio text must be 4-6 sentences, designed to be read aloud to the farmer (clear, minimal technical jargon).\n"
            "- End each zone with an urgency level (high/medium/low).\n"
        )
    else:  # français par défaut
        system_prompt = (
            "Tu es un conseiller agricole expert en Afrique (Sahel, zones tropicales).\n"
            "Analyse les donnees de sol fournies et donne des conseils detailles, pratiques, en langage simple.\n\n"
            "REGLES:\n"
            "- Reponds UNIQUEMENT en JSON valide, sans texte avant ni apres.\n"
            "- Pour CHAQUE zone, donne un conseil ACTIONNABLE, pas une description du sol.\n"
            "- Explique EXACTEMENT quoi faire : quelle culture planter, quand, avec quelle fertilisation (kg/ha), quel amendement (chaux, compost, etc.), quelle technique culturale.\n"
            "- Si l'EC est eleve (salinite), explique comment lessiver le sol. Si le pH est acide, combien de chaux. Si le pH est alcalin, quoi apporter comme matiere organique.\n"
            "- Si N/P/K est bas, donne des engrais SPECIFIQUES (NPK 15-15-15, uree, DAP, KCl) avec les doses en kg/ha.\n"
            "- Le resume global doit etre un paragraphe de 5 a 8 phrases qui synthetise les recommandations de TOUTES les zones.\n"
            "- Le texte audio doit etre 4 a 6 phrases, concu pour etre lu a voix haute a l'agriculteur (clair, sans jargon technique superflu).\n"
            "- Termine chaque conseil par une recommandation d'urgence (haute/moyenne/faible).\n"
        )

    user_msg_parts = [
        f"Waɗannan bayanan aikin gona ne cikakke:" if language == 'ha'
        else f"Hizi ni data kamili ya misheni ya kilimo:" if language == 'sw'
        else f"هذه هي بيانات المهمة الزراعية الكاملة:" if language == 'ar'
        else f"Here are the complete agricultural mission data:"
        if language == 'en'
        else f"Voici les donnees de la mission agricole complete:",
        f"{zones_text}\n",
        f"Koma KAWAI wannan JSON (babu rubutu gaba/ko baya):" if language == 'ha'
        else f"Rudisha JSON hii PEKEE (hakuna maandishi kabla/baada):" if language == 'sw'
        else f"أعد فقط صيغة JSON هذه (لا نص قبل/بعد):" if language == 'ar'
        else f"Return ONLY this JSON (no text before/after):"
        if language == 'en'
        else f"Retourne UNIQUEMENT ce JSON (pas de texte avant/apres):",
        '{\n'
        f'  "{cfg["resume"]}": "resume global detaille pour tout le champ",\n'
        '  "zones": [\n'
        '    {\n'
        f'      "zone": 1,\n'
        f'      "{cfg["culture"]}": "nom de la culture recommandee",\n'
        f'      "{cfg["explication"]}": "pourquoi cette culture convient (pH, EC, N, P, K)",\n'
        f'      "{cfg["action"]}": "PLAN D ACTION DETAILLE : culture, fertilisation kg/ha, amendement, preparation sol, calendrier",\n'
        f'      "{cfg["urgence"]}": "{"faible/moyenne/haute" if language == "fr" else "low/medium/high"}"\n'
        '    }\n'
        '  ],\n'
        f'  "{cfg["audio"]}": "texte clair a lire a voix haute (4-6 phrases)"\n'
        '}'
    ]
    user_msg = "\n".join(user_msg_parts)

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(
            _GROQ_URL, json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30,
        )
        data = resp.json()
        if resp.status_code != 200:
            return {"error": f"Groq: {data.get('error',{}).get('message', str(resp.status_code))}"}
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        result["_raw_zones"] = zones_text

        # Normaliser les clés spécifiques à la langue → clés françaises standard
        # (le frontend et app.py utilisent toujours resume_global, audio_propice, etc.)
        if language != 'fr':
            for new_key, std_key in [
                (cfg['resume'], 'resume_global'),
                (cfg['audio'], 'audio_propice'),
            ]:
                if new_key in result and new_key != std_key:
                    result[std_key] = result.pop(new_key)
            # Normaliser les clés des zones
            zone_key_map = {
                cfg['culture']: 'culture_conseillee',
                cfg['explication']: 'explication',
                cfg['action']: 'action',
                cfg['urgence']: 'urgence',
            }
            zones = result.get('zones', [])
            for zone in zones:
                for old_k, new_k in zone_key_map.items():
                    if old_k in zone and old_k != new_k:
                        zone[new_k] = zone.pop(old_k)
        return result
    except Exception as e:
        return {"error": str(e)}

# ── Test ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  RECO ENGINE — Pipeline impact par culture")
    print("=" * 60)

    fake_sensor = {
        'humidity_pct': 21.5,
        'temperature_c': 23.4,
        'ec_us_cm': 62.0,
        'ph': 8.2,
    }

    print(f"\nMesures: {json.dumps(fake_sensor, indent=2)}")
    print("\nExecution...\n")

    result = recommend(fake_sensor, top_n=3)

    npk = result["npk_estimes"]
    print(f"NPK: N={npk['N_kg_ha']} P2O5={npk['P2O5_kg_ha']} K2O={npk['K2O_kg_ha']}\n")

    for i, c in enumerate(result["classement"][:3]):
        print(f"#{i+1} {c['culture']} — {c['score']}%")
        print(f"  ✅ {', '.join(c.get('parametres_match', []))}")
        print(f"  ⚠️ {', '.join(c.get('parametres_limites', []))}")
        print(f"  ❌ {', '.join(c.get('parametres_hors_plage', []))}")
        print(f"  Scores: {c.get('scores_details', {})}")
        print(f"  Chart: {'YES (' + str(len(c.get('impact_chart_b64',''))) + ' chars)' if c.get('impact_chart_b64') else 'NONE'}")
        print()

    if result["fertilisation"]:
        print(f"Fertilisation: {result['fertilisation'].get('NPK_recommandation', 'N/A')}")
    print("\n✅ OK")
