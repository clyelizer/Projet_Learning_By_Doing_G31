#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test d'intégration — lecture réelle du capteur sol via Arduino.

Lancement :
    pytest tests/test_sensor_live.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import time

from src.sensor_arduino import read_sensor, SERIAL_AVAILABLE


def _show(prefix, r):
    """Affiche une lecture capteur de façon lisible."""
    print(f"\n  {prefix}")
    print(f"    💧 Humidité : {r['humidity_pct']:6.1f} %")
    print(f"    🌡️  Température: {r['temperature_c']:6.1f} °C")
    print(f"    ⚡ EC       : {r['ec_us_cm']:6.1f} µS/cm")
    print(f"    🧪 pH       : {r['ph']:6.1f}")
    print(f"    🕐 {r['timestamp']}")


@pytest.mark.skipif(not SERIAL_AVAILABLE, reason="pyserial absent")
class TestSensorLive:
    """Lecture réelle du capteur 4-en-1 via Arduino."""

    def test_read_sensor_retourne_donnees_valides(self):
        """Une lecture doit retourner les 4 mesures + timestamp."""
        result = read_sensor()
        assert result is not None, "Aucune donnée reçue — Arduino branché ?"
        _show("Lecture unique :", result)

        # Vérifie les 4 mesures
        assert 'humidity_pct' in result
        assert 'temperature_c' in result
        assert 'ec_us_cm' in result
        assert 'ph' in result
        assert 'timestamp' in result

        # Types
        assert isinstance(result['humidity_pct'], float)
        assert isinstance(result['temperature_c'], float)
        assert isinstance(result['ec_us_cm'], float)
        assert isinstance(result['ph'], float)

        # Plages plausibles (même à 0 si capteur dans l'air)
        assert 0.0 <= result['humidity_pct'] <= 100.0, \
            f"Humidité hors plage: {result['humidity_pct']}"
        assert -10.0 <= result['temperature_c'] <= 80.0, \
            f"Température hors plage: {result['temperature_c']}"
        assert 0.0 <= result['ec_us_cm'] <= 20000.0, \
            f"EC hors plage: {result['ec_us_cm']}"
        assert 0.0 <= result['ph'] <= 14.0, \
            f"pH hors plage: {result['ph']}"

    def test_deux_lectures_consecutives(self):
        """Deux lectures rapprochées doivent être cohérentes."""
        r1 = read_sensor()
        assert r1 is not None
        _show("Lecture 1 :", r1)
        time.sleep(1.0)
        r2 = read_sensor()
        assert r2 is not None
        _show("Lecture 2 :", r2)

        # La température ne doit pas varier de plus de 2°C en 1s
        delta_temp = abs(r1['temperature_c'] - r2['temperature_c'])
        assert delta_temp < 2.0, \
            f"Température instable: {r1['temperature_c']} → {r2['temperature_c']}"

        # Le pH ne doit pas varier de plus de 0.5 en 1s
        delta_ph = abs(r1['ph'] - r2['ph'])
        assert delta_ph < 0.5, \
            f"pH instable: {r1['ph']} → {r2['ph']}"

        # Vérifie que le timestamp change
        assert r1['timestamp'] != r2['timestamp']

    def test_cinq_lectures_stabilite(self):
        """5 lectures sur ~10s — les valeurs ne sont pas figées."""
        print("\n  📊 Série de 5 lectures (intervalle 2s) :")
        readings = []
        for i in range(5):
            r = read_sensor()
            assert r is not None
            readings.append(r)
            _show(f"#{i+1} :", r)
            if i < 4:
                time.sleep(2.0)

        # Vérifie qu'au moins une valeur a changé (capteur vivant)
        temps = [r['temperature_c'] for r in readings]
        hums = [r['humidity_pct'] for r in readings]
        ecs = [r['ec_us_cm'] for r in readings]
        phs = [r['ph'] for r in readings]

        # Au moins une des 4 mesures doit varier entre les lectures
        variations = (
            len(set(temps)) > 1 or
            len(set(hums)) > 1 or
            len(set(ecs)) > 1 or
            len(set(phs)) > 1
        )
        assert variations, (
            f"Capteur figé sur 5 lectures:\n"
            f"  Températures: {temps}\n"
            f"  Humidités:    {hums}\n"
            f"  ECs:          {ecs}\n"
            f"  pHs:          {phs}"
        )
