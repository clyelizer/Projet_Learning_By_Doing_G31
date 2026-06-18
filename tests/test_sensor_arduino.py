#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitaires pour sensor_arduino.py — parse de la sortie Arduino.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.sensor_arduino import _parse_arduino_output


class TestParseArduinoOutput:
    """Tests du parser de trame Arduino."""

    def test_trame_complete(self):
        """Trame normale avec les 4 mesures."""
        trame = (
            "Humidité: 17.20 %\r\n"
            "Température: 24.10 °C\r\n"
            "EC: 45.00 us/cm\r\n"
            "pH: 8.60\r\n"
            "-----------------------\r\n"
        )
        result = _parse_arduino_output(trame)
        assert result is not None
        assert result['humidity_pct'] == pytest.approx(17.20)
        assert result['temperature_c'] == pytest.approx(24.10)
        assert result['ec_us_cm'] == pytest.approx(45.00)
        assert result['ph'] == pytest.approx(8.60)

    def test_trame_valeurs_zero(self):
        """Trame avec des valeurs à zéro (capteur dans l'air)."""
        trame = (
            "Humidité: 0.00 %\r\n"
            "Température: 25.00 °C\r\n"
            "EC: 0.00 us/cm\r\n"
            "pH: 7.00\r\n"
            "-----------------------\r\n"
        )
        result = _parse_arduino_output(trame)
        assert result is not None
        assert result['humidity_pct'] == pytest.approx(0.0)
        assert result['ec_us_cm'] == pytest.approx(0.0)

    def test_trame_grandes_valeurs(self):
        """Trame avec des valeurs élevées (sol humide/fertile)."""
        trame = (
            "Humidité: 85.50 %\r\n"
            "Température: 35.80 °C\r\n"
            "EC: 1200.00 us/cm\r\n"
            "pH: 9.50\r\n"
            "-----------------------\r\n"
        )
        result = _parse_arduino_output(trame)
        assert result is not None
        assert result['humidity_pct'] == pytest.approx(85.50)
        assert result['ec_us_cm'] == pytest.approx(1200.00)
        assert result['ph'] == pytest.approx(9.50)

    def test_trame_entiers_sans_decimale(self):
        """Cas où les valeurs sont des entiers (ex: 17 au lieu de 17.00)."""
        trame = (
            "Humidité: 17 %\r\n"
            "Température: 24 °C\r\n"
            "EC: 45 us/cm\r\n"
            "pH: 8 %\r\n"
            "-----------------------\r\n"
        )
        result = _parse_arduino_output(trame)
        assert result is not None
        assert result['humidity_pct'] == pytest.approx(17.0)
        assert result['temperature_c'] == pytest.approx(24.0)

    def test_trame_sauts_de_ligne_unix(self):
        """Trame avec \n seulement (pas de \r\n)."""
        trame = (
            "Humidité: 33.90 %\n"
            "Température: 21.60 °C\n"
            "EC: 168.00 us/cm\n"
            "pH: 8.60\n"
            "-----------------------\n"
        )
        result = _parse_arduino_output(trame)
        assert result is not None
        assert result['humidity_pct'] == pytest.approx(33.90)

    def test_trame_sans_separateur(self):
        """Trame valide mais sans la ligne de séparation."""
        trame = (
            "Humidité: 17.20 %\r\n"
            "Température: 24.10 °C\r\n"
            "EC: 45.00 us/cm\r\n"
            "pH: 8.60\r\n"
        )
        result = _parse_arduino_output(trame)
        assert result is not None  # le séparateur n'est pas obligatoire
        assert result['humidity_pct'] == pytest.approx(17.20)

    def test_trame_lignes_incompletes(self):
        """Trame avec des lignes manquantes."""
        trame = (
            "Humidité: 17.20 %\r\n"
            "Température: 24.10 °C\r\n"
            "-----------------------\r\n"
        )
        result = _parse_arduino_output(trame)
        assert result is None

    def test_erreur_modbus(self):
        """Trame d'erreur Modbus (l'Arduino peut envoyer ça)."""
        trame = "Erreur de lecture Modbus ! Code: E2\r\n"
        result = _parse_arduino_output(trame)
        assert result is None

    def test_vide(self):
        """Chaîne vide."""
        assert _parse_arduino_output("") is None

    def test_texte_bidouille(self):
        """Texte complètement inattendu."""
        assert _parse_arduino_output("abc123!!!") is None
        assert _parse_arduino_output("   \n  \n  ") is None

    def test_nbsp_dans_les_labels(self):
        """Labels avec espaces insécables ou variantes."""
        trame = (
            "Humidité: 10.50 %\r\n"
            "Température: 20.00 °C\r\n"
            "EC: 100.00 us/cm\r\n"
            "pH: 7.50\r\n"
            "-----------------------\r\n"
        )
        result = _parse_arduino_output(trame)
        assert result is not None
        assert result['ph'] == pytest.approx(7.50)

    def test_donnees_multiples_une_seule_prise(self):
        """Plusieurs trames d'affilée dans le buffer — doit parser la dernière."""
        trame = (
            "Humidité: 10.00 %\r\n"
            "Température: 20.00 °C\r\n"
            "EC: 100.00 us/cm\r\n"
            "pH: 7.00\r\n"
            "-----------------------\r\n"
            "Humidité: 11.00 %\r\n"
            "Température: 20.50 °C\r\n"
            "EC: 105.00 us/cm\r\n"
            "pH: 7.10\r\n"
            "-----------------------\r\n"
        )
        # Le parser actuel prend toutes les lignes, les 4 dernières valeurs gagnent
        result = _parse_arduino_output(trame)
        assert result is not None
        assert result['humidity_pct'] == pytest.approx(11.00)
        assert result['temperature_c'] == pytest.approx(20.50)
        assert result['ec_us_cm'] == pytest.approx(105.00)
        assert result['ph'] == pytest.approx(7.10)


class TestLoopbackReadDefault:
    """Test d'intégration basique — juste valider que le module s'importe."""

    def test_module_importable(self):
        """Le module sensor_arduino s'importe sans erreur."""
        import src.sensor_arduino as sa
        assert sa is not None
        assert hasattr(sa, 'read_sensor')
        assert hasattr(sa, '_parse_arduino_output')

    def test_read_sensor_retourne_none_sans_serial(self):
        """read_sensor() retourne None quand pyserial est absent."""
        import src.sensor_arduino as sa
        old = sa.SERIAL_AVAILABLE
        sa.SERIAL_AVAILABLE = False
        try:
            result = sa.read_sensor()
            assert result is None
        finally:
            sa.SERIAL_AVAILABLE = old
