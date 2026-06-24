#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests reco_engine — pipeline de recommandation agricole.

Skip par défaut pour les tests API (quota). Activer avec :
    RUN_VLM=1 pytest tests/test_reco_engine.py -v -s
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from reco_engine import (
    recommend,
    estimer_NPK,
    estimer_NPK_ML,
    predire_culture_ML,
    load_base_reference,
)

_RUN = os.environ.get('RUN_VLM') == '1'


# ── Tests sans API (toujours exécutés) ────────────────────────────

class TestHeuristicNPK:
    """Formules pedotransfert legacy."""

    def test_estimer_NPK_retourne_cles_attendues(self):
        result = estimer_NPK(EC=0.5, pH=6.5, humidite=60, temperature=25)
        assert 'N_kg_ha' in result
        assert 'P2O5_kg_ha' in result
        assert 'K2O_kg_ha' in result
        assert 'methodes' in result
        assert result['N_kg_ha'] >= 0

    def test_estimer_NPK_ph_acide(self):
        """pH < 6 → P plus bas."""
        r_acid = estimer_NPK(EC=0.5, pH=5.0, humidite=60, temperature=25)
        r_neutral = estimer_NPK(EC=0.5, pH=7.0, humidite=60, temperature=25)
        assert r_acid['P_mg_kg'] <= r_neutral['P_mg_kg']

    def test_estimer_NPK_ph_alcalin(self):
        """pH > 7 → P plus bas."""
        r_alk = estimer_NPK(EC=0.5, pH=8.5, humidite=60, temperature=25)
        r_neutral = estimer_NPK(EC=0.5, pH=7.0, humidite=60, temperature=25)
        assert r_alk['P_mg_kg'] <= r_neutral['P_mg_kg']


class TestMLNPK:
    """Estimation NPK via Random Forest Regressors."""

    def test_modele_disponible(self):
        result = estimer_NPK_ML(pH=6.5, temperature=25, humidite=60)
        assert result is not None

    def test_estimer_NPK_ML_retourne_cles(self):
        result = estimer_NPK_ML(pH=6.5, temperature=25, humidite=60)
        assert result is not None
        assert 'N_kg_ha' in result
        assert 'P_mg_kg' in result
        assert 'K_mg_kg' in result
        assert result['N_kg_ha'] >= 0

    def test_estimer_NPK_ML_valeurs_plausibles(self):
        result = estimer_NPK_ML(pH=6.5, temperature=25, humidite=60)
        assert result is not None
        assert 0 <= result['N_kg_ha'] <= 500
        assert 5 <= result['P_mg_kg'] <= 200
        assert 10 <= result['K_mg_kg'] <= 500


class TestMLCulture:
    """Classification de culture via Random Forest Classifier."""

    def test_predire_culture_ML_retourne_dict(self):
        result = predire_culture_ML(pH=6.5, temperature=28, humidite=65, N=90, P=40, K=45)
        assert result is not None
        assert 'culture' in result
        assert 'confiance' in result
        assert 'top_3' in result
        assert 0 <= result['confiance'] <= 1
        assert len(result['top_3']) == 3

    def test_predire_culture_ML_culture_valide(self):
        result = predire_culture_ML(pH=6.5, temperature=28, humidite=65, N=90, P=40, K=45)
        assert result is not None
        assert result['culture'] in ['beans', 'maize', 'rice', 'banana', 'coffee',
                                      'cotton', 'groundnuts', 'mango', 'orange',
                                      'Soyabeans', 'apple', 'grapes', 'watermelon',
                                      'peas', 'cowpeas']


class TestRecommendIntegre:
    """Tests end-to-end du pipeline recommend()."""

    def test_recommend_structure(self):
        sensor = {
            'humidity_pct': 21.5, 'temperature_c': 23.4,
            'ec_us_cm': 62.0, 'ph': 8.2,
        }
        result = recommend(sensor)
        assert 'mesures_brutes' in result
        assert 'npk_estimes' in result
        assert 'classement' in result
        assert 'top_culture' in result
        assert 'ml_culture' in result
        assert 'fertilisation' in result

    def test_recommend_utilise_ML(self):
        """ML doit etre la methode par defaut pour NPK."""
        sensor = {'humidity_pct': 50, 'temperature_c': 25, 'ec_us_cm': 100, 'ph': 7}
        result = recommend(sensor)
        npk = result.get('npk_estimes', {})
        assert npk.get('methode') == 'ML'

    def test_recommend_classement_len(self):
        sensor = {'humidity_pct': 50, 'temperature_c': 25, 'ec_us_cm': 100, 'ph': 7}
        result = recommend(sensor)
        assert len(result.get('classement', [])) == 41

    def test_recommend_ml_culture_presente(self):
        sensor = {'humidity_pct': 65, 'temperature_c': 28, 'ec_us_cm': 100, 'ph': 6.5}
        result = recommend(sensor)
        ml = result.get('ml_culture')
        assert ml is not None
        assert 'culture' in ml
        assert 'confiance' in ml
        assert isinstance(ml['top_3'], list)
        assert len(ml['top_3']) == 3

    def test_recommend_top_n_param(self):
        """top_n controle le nombre de graphiques d'impact."""
        sensor = {'humidity_pct': 50, 'temperature_c': 25, 'ec_us_cm': 100, 'ph': 7}
        result = recommend(sensor, top_n=3)
        charts = [c for c in result.get('classement', []) if c.get('impact_chart_b64')]
        assert len(charts) == 3

    def test_recommend_cas_extreme_ph(self):
        """pH extreme doit produire un resultat complet."""
        sensor = {'humidity_pct': 60, 'temperature_c': 30, 'ec_us_cm': 200, 'ph': 4.0}
        result = recommend(sensor)
        assert 'error' not in result
        assert result['npk_estimes']['N_kg_ha'] >= 0

    def test_recommend_ec_zero(self):
        """EC=0 (capteur non disponible) ne doit pas crasher."""
        sensor = {'humidity_pct': 60, 'temperature_c': 25, 'ec_us_cm': 0, 'ph': 7.0}
        result = recommend(sensor)
        assert 'error' not in result


# ── Tests avec API réelle (RUN_VLM=1) ─────────────────────────────

@pytest.mark.skipif(not _RUN, reason="RUN_VLM=1 non défini — quota préservé")
class TestRecommendRealAPI:
    """Appels réels à Groq Llama 8B."""

    def test_reco_retourne_structure(self):
        sensor = {
            'humidity_pct': 21.5, 'temperature_c': 23.4,
            'ec_us_cm': 62.0, 'ph': 8.2,
        }
        result = recommend(sensor, language='fr')
        if 'error' in result:
            pytest.skip(f"API down: {result['error']}")
        assert 'classement' in result
        assert len(result['classement']) > 0
