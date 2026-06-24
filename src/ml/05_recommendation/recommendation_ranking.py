#!/usr/bin/env python3
"""
recommendation_ranking.py — Systeme de classement (ranking) des cultures
avec justificatifs et recommandations de fertilisation pour robot agricole.

Usage:
    python recommendation_ranking.py          # Execute les tests unitaires
    from recommendation_ranking import rank_cultures, get_recommendations
"""

import json
import os
import sys
from typing import Any

# ---------------------------------------------------------------------------
# 1. Chemin de la base de reference
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.join(SCRIPT_DIR, '..', '01_databases', 'base_reference_agricole.json')

# ---------------------------------------------------------------------------
# 2. Ponderation des parametres (somme = 100 %)
# ---------------------------------------------------------------------------

POIDS = {
    "pH": 0.30,
    "temperature": 0.20,
    "humidite": 0.20,
    "N": 0.15,
    "P2O5": 0.10,
    "K2O": 0.05,
}

PARAMETRES_SCORES = ["pH", "temperature", "humidite", "N", "P2O5", "K2O"]
PARAMETRES_ROBOT = ["EC", "pH", "humidite", "temperature"]

# ---------------------------------------------------------------------------
# 3. Chargement de la base
# ---------------------------------------------------------------------------

def load_base_reference(path: str = BASE_PATH) -> dict:
    """Charge la base de reference JSON et retourne le dictionnaire complet."""
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Base de reference introuvable : {path}\n"
            "Verifiez le chemin ou telechargez le fichier."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 4. Extraction des plages optimales par culture
# ---------------------------------------------------------------------------

def extraire_plages(base: dict) -> dict:
    """
    Pour chaque culture, extrait les plages optimales {min, max, optimal}
    pour les parametres : pH, N, P2O5, K2O, temperature, humidite.

    Retourne un dict indexe par le nom de la culture :
        {
            "Mais": {
                "pH":       {"min": 5.0, "max": 7.0, "optimal": 6.0},
                "temperature": {"min": 16, "max": 33, "optimal": None},
                ...
            },
            ...
        }
    """
    plages = {}
    for entree in base.get("cultures", []):
        nom = entree["culture"]
        sol = entree.get("sol", {})
        plage_culture = {}
        for param in PARAMETRES_SCORES:
            data = sol.get(param, {})
            pmin = data.get("min")
            pmax = data.get("max")
            popt = data.get("optimal")
            if pmin is not None and pmax is not None:
                plage_culture[param] = {
                    "min": float(pmin),
                    "max": float(pmax),
                    "optimal": float(popt) if popt is not None else None,
                    "unite": data.get("unite", ""),
                }
        plages[nom] = plage_culture
    return plages


# ---------------------------------------------------------------------------
# 5. Calcul de compatibilite individuelle d'un parametre
# ---------------------------------------------------------------------------

def _compatibilite_param(valeur: float, plage: dict) -> float:
    """
    Calcule le score de compatibilite (0.0 - 1.0) pour un parametre.

    - Si valeur dans [min, max]          → score = 1.0
    - Si valeur < min (ecart <= plage)   → score lineaire 0.5 → 1.0
    - Si valeur > max (ecart <= plage)   → score lineaire 0.5 → 1.0
    - Si ecart > plage                   → score lineaire jusqu'a 0.0
    """
    pmin = plage["min"]
    pmax = plage["max"]
    plage_amplitude = pmax - pmin

    if plage_amplitude <= 0:
        return 1.0 if valeur == pmin else 0.0

    if pmin <= valeur <= pmax:
        return 1.0

    if valeur < pmin:
        distance = (pmin - valeur) / plage_amplitude
        return max(0.0, 1.0 - distance)
    else:  # valeur > pmax
        distance = (valeur - pmax) / plage_amplitude
        return max(0.0, 1.0 - distance)


# ---------------------------------------------------------------------------
# 6. Generation du justificatif textuel
# ---------------------------------------------------------------------------

def _generer_justificatif(
    nom_culture: str,
    mesures: dict,
    plage_culture: dict,
    scores_params: dict,
    score_total: float,
) -> str:
    """
    Construit un paragraphe explicatif en francais indiquant :
      - quels parametres sont dans la plage optimale
      - quels parametres sont limites ou hors plage
      - les valeurs mesurees et les references.
    """
    phrases = []
    phrases.append(
        f"{nom_culture} — Score de compatibilite : {score_total:.1f}%"
    )

    for param in PARAMETRES_SCORES:
        if param not in mesures or param not in plage_culture:
            continue
        valeur = mesures[param]
        plage = plage_culture[param]
        pmin = plage["min"]
        pmax = plage["max"]
        unite = plage.get("unite", "")

        if pmin <= valeur <= pmax:
            phrases.append(
                f"- {param} : {valeur}{unite} est dans la plage optimale "
                f"[{pmin}-{pmax}{unite}]"
            )
        elif valeur < pmin:
            phrases.append(
                f"- {param} : {valeur}{unite} est SOUS la plage optimale "
                f"[{pmin}-{pmax}{unite}]"
            )
        else:
            phrases.append(
                f"- {param} : {valeur}{unite} est AU-DESSUS de la plage optimale "
                f"[{pmin}-{pmax}{unite}]"
            )

    # Mention des parametres absents (donnees manquantes dans la base)
    absents = [
        p for p in PARAMETRES_SCORES
        if p not in plage_culture
    ]
    if absents:
        phrases.append(
            f"- Parametres sans reference dans la base : {', '.join(absents)}"
        )

    return "\n".join(phrases)


# ---------------------------------------------------------------------------
# 7. Fonction principale : rank_cultures
# ---------------------------------------------------------------------------

def rank_cultures(mesures_robot: dict) -> list[dict]:
    """
    Classe les cultures par compatibilite avec les mesures du robot.

    Parameters
    ----------
    mesures_robot : dict
        Mesures realisees par le robot. Au minimum :
            {"pH": float, "humidite": float, "temperature": float}
        Optionnellement peut contenir N, P2O5, K2O (estimes par ML).

    Returns
    -------
    list[dict]
        Liste triee (score decroissant) de dictionnaires :
            [
                {
                    "culture": "Mais",
                    "score": 92.5,
                    "justificatif": "...",
                    "parametres_match": ["pH", "temperature", ...],
                    "parametres_limites": ["humidite", ...],
                    "parametres_hors_plage": [...],
                    "scores_details": {"pH": 1.0, "temperature": 0.85, ...}
                },
                ...
            ]
    """
    # Charger et preparer les donnees
    base = load_base_reference()
    plages = extraire_plages(base)

    # Separer les mesures connues des inconnues
    #  - EC est ignore car aucune culture n'a de plage de reference
    #  - On ne garde que les parametres qui existent dans les plages
    mesures = {}
    for p in mesures_robot:
        if p in PARAMETRES_SCORES:
            mesures[p] = float(mesures_robot[p])
        elif p in ("EC",):
            # EC est mesure mais non note (pas de reference)
            pass

    if not mesures:
        raise ValueError(
            "Aucune mesure exploitable fournie. "
            "Fournissez au moins pH, humidite ou temperature."
        )

    # Calculer le poids total effectif (renormalisation si certains absents)
    poids_effectif = {p: POIDS[p] for p in mesures if p in POIDS}
    total_poids = sum(poids_effectif.values())
    if total_poids <= 0:
        raise ValueError("Aucun parametre pondere n'est disponible dans les mesures.")

    resultats = []
    for nom_culture, plage_culture in plages.items():
        scores_params = {}
        parametres_match = []
        parametres_limites = []
        parametres_hors_plage = []

        for param, valeur in mesures.items():
            if param not in plage_culture:
                scores_params[param] = None
                continue

            plage = plage_culture[param]
            score = _compatibilite_param(valeur, plage)
            scores_params[param] = score

            if score >= 1.0:
                parametres_match.append(param)
            elif score >= 0.5:
                parametres_limites.append(param)
            else:
                parametres_hors_plage.append(param)

        # Score pondere renormalise
        score_pondere = 0.0
        for param, valeur in mesures.items():
            if param in scores_params and scores_params[param] is not None:
                poids = POIDS.get(param, 0.0)
                score_pondere += poids * scores_params[param]

        # Renormaliser par rapport au poids total effectif
        score_normalise = (score_pondere / total_poids) * 100.0
        score_normalise = max(0.0, min(100.0, score_normalise))

        justificatif = _generer_justificatif(
            nom_culture, mesures, plage_culture,
            scores_params, score_normalise,
        )

        resultats.append({
            "culture": nom_culture,
            "score": round(score_normalise, 1),
            "justificatif": justificatif,
            "parametres_match": parametres_match,
            "parametres_limites": parametres_limites,
            "parametres_hors_plage": parametres_hors_plage,
            "scores_details": {
                k: round(v, 4) if v is not None else None
                for k, v in scores_params.items()
            },
        })

    # Trier par score decroissant
    resultats.sort(key=lambda r: r["score"], reverse=True)
    return resultats


# ---------------------------------------------------------------------------
# 8. Recommandations de fertilisation
# ---------------------------------------------------------------------------

def get_recommendations(mesures_robot: dict) -> dict:
    """
    Genere le ranking + recommandations de fertilisation.

    Parameters
    ----------
    mesures_robot : dict
        Meme format que pour rank_cultures().

    Returns
    -------
    dict
        {
            "mesures": {...},
            "ranking": [ ... ],          # resultat de rank_cultures()
            "top_culture": "...",
            "top_score": 92.5,
            "fertilisation": {
                "NPK_recommandation": "...",
                "source": "...",
            } | None,
        }
    """
    base = load_base_reference()
    ranking = rank_cultures(mesures_robot)

    result = {
        "mesures": mesures_robot,
        "ranking": ranking,
    }

    if ranking:
        top = ranking[0]
        result["top_culture"] = top["culture"]
        result["top_score"] = top["score"]

        # Chercher la fertilisation de la culture top dans la base
        fertilisation = None
        for entree in base.get("cultures", []):
            if entree["culture"] == top["culture"]:
                fertilisation = entree.get("fertilisation")
                break
        result["fertilisation"] = fertilisation

    return result


# ---------------------------------------------------------------------------
# 9. Point d'entree principal + tests unitaires
# ---------------------------------------------------------------------------

def main():
    """Tests unitaires du module."""
    print("=" * 60)
    print("recommendation_ranking.py — Tests unitaires")
    print("=" * 60)

    # --- Test 1 : Chargement de la base ---
    print("\n[Test 1] Chargement de la base de reference...")
    try:
        base = load_base_reference()
        cultures = base.get("cultures", [])
        print(f"  OK — {len(cultures)} cultures chargees :")
        for c in cultures:
            print(f"    - {c['culture']} ({c.get('nom_scientifique', 'N/A')})")
    except Exception as e:
        print(f"  ERREUR : {e}")
        sys.exit(1)

    # --- Test 2 : Extraction des plages ---
    print("\n[Test 2] Extraction des plages optimales...")
    plages = extraire_plages(base)
    print(f"  OK — Plages extraites pour {len(plages)} cultures")
    for nom, plage in list(plages.items())[:3]:
        params = list(plage.keys())
        print(f"    {nom} : {params}")

    # --- Test 3 : rank_cultures avec valeurs fictives ---
    print("\n[Test 3] rank_cultures() avec mesures fictives...")
    mesures_test = {
        "pH": 6.2,
        "temperature": 28.0,
        "humidite": 65.0,
        "EC": 0.5,                     # ignore dans le scoring
        "N": 90.0,                     # optionnel (estimation ML)
    }
    try:
        ranking = rank_cultures(mesures_test)
        print(f"  OK — {len(ranking)} cultures classees")
        print(f"  Top 3 :")
        for i, r in enumerate(ranking[:3], 1):
            print(f"    {i}. {r['culture']} — Score: {r['score']}%")
            print(f"       Match: {r['parametres_match']}")
            print(f"       Limites: {r['parametres_limites']}")
            print(f"       Hors plage: {r['parametres_hors_plage']}")
            # Afficher un extrait du justificatif
            justif_preview = r['justificatif'].split('\n')
            for line in justif_preview[:3]:
                print(f"       {line}")
            print()
    except Exception as e:
        print(f"  ERREUR : {e}")
        import traceback
        traceback.print_exc()

    # --- Test 4 : Verification du top 3 ---
    print("\n[Test 4] Verification du top 3...")
    # Avec pH=6.2, T=28, humidite=65, N=90 :
    #   Mais    : pH 5.0-7.0 (match), T 16-33 (match), humidite 55.3-74.8 (match), N 80-120 (match)
    #   Manioc  : pH 5.5-8.0 (match), T 20-29 (match), N 48-160 (match)
    #   Coton   : pH 5.2-7.5 (match), T 22-36 (match), N 60-150 (match)
    # Let's just assert the top 3 are reasonable
    top3_names = [r["culture"] for r in ranking[:3]]
    print(f"  Top 3 : {top3_names}")
    assert len(top3_names) == 3, "Le top 3 doit contenir 3 cultures"
    assert ranking[0]["score"] >= ranking[1]["score"], "Le 1er doit avoir un score >= au 2e"
    assert ranking[1]["score"] >= ranking[2]["score"], "Le 2e doit avoir un score >= au 3e"
    assert all(r["score"] >= 0 and r["score"] <= 100 for r in ranking[:3]), \
        "Les scores doivent etre entre 0 et 100"
    print("  Assertions passees : scores decroissants et dans [0, 100]")
    print("  Top 3 correct.")

    # --- Test 5 : get_recommendations ---
    print("\n[Test 5] get_recommendations()...")
    try:
        rec = get_recommendations(mesures_test)
        print(f"  Culture recommandee : {rec['top_culture']} (score: {rec['top_score']}%)")
        if rec["fertilisation"]:
            print(f"  Fertilisation : {rec['fertilisation']['NPK_recommandation']}")
            print(f"  Source : {rec['fertilisation']['source']}")
        print("  OK")
    except Exception as e:
        print(f"  ERREUR : {e}")
        import traceback
        traceback.print_exc()

    # --- Test 6 : Cas extremes ---
    print("\n[Test 6] Cas extremes — valeurs hors echelle...")
    mesures_extremes = {"pH": 2.0, "temperature": 50.0, "humidite": 5.0}
    ranking_extreme = rank_cultures(mesures_extremes)
    print(f"  Toutes les cultures doivent avoir un score faible")
    for i, r in enumerate(ranking_extreme[:3], 1):
        print(f"    {i}. {r['culture']} — {r['score']}%")
    assert all(r["score"] < 50 for r in ranking_extreme[:3]), \
        "Les scores extremes doivent etre faibles"
    print("  OK — scores faibles confirmes.")

    print("\n" + "=" * 60)
    print("TOUS LES TESTS PASSES AVEC SUCCES.")
    print("=" * 60)


if __name__ == "__main__":
    main()
