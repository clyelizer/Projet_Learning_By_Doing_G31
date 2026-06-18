#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'agrégation des données de mission.
Collecte les mesures capteur et résultats image par waypoint,
puis sauvegarde le tout dans un fichier JSON.

Usage:
    python data_logger.py       # test avec données simulées
"""

import json
import os
import time


class DataLogger:
    """Journal de mission : collecte et sauvegarde les données."""

    def __init__(self):
        self._mission_start = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        self._waypoints = []

    def log_waypoint(self, waypoint_id, sensor_data=None, image_paths=None):
        """
        Enregistre ou met à jour les données d'un waypoint.

        Si une entrée existe déjà pour ce waypoint_id, elle est fusionnée
        (par ex. un appel pour 'probe' puis un appel pour 'photo').

        Args:
            waypoint_id: int — identifiant du waypoint
            sensor_data: dict ou None — données du capteur NPK
            image_paths: list ou None — chemins des photos
        """
        # Chercher une entrée existante pour ce waypoint
        existing = None
        for entry in self._waypoints:
            if entry['waypoint_id'] == waypoint_id:
                existing = entry
                break

        if existing:
            # Fusion : ne remplacer que les champs fournis (non-None)
            if sensor_data is not None:
                existing['sensor'] = sensor_data
            if image_paths is not None:
                existing['photos'] = image_paths
            print(f"[LOG] Waypoint {waypoint_id} mis à jour "
                  f"(capteur={'oui' if existing['sensor'] else 'non'}, "
                  f"photos={len(existing['photos'] if existing['photos'] else [])})")
        else:
            entry = {
                'waypoint_id': waypoint_id,
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'sensor': sensor_data,
                'photos': image_paths or [],
                'image_results': None  # sera rempli après traitement
            }
            self._waypoints.append(entry)
            print(f"[LOG] Waypoint {waypoint_id} enregistré "
                  f"(capteur={'oui' if sensor_data else 'non'}, "
                  f"photos={len(image_paths) if image_paths else 0})")

    def attach_image_results(self, image_results):
        """
        Associe les résultats du processeur d'images aux waypoints.

        Args:
            image_results: list[dict] — résultats de image_preprocessor.get_results()
        """
        for result in image_results:
            wp_id = result['waypoint_id']
            for entry in self._waypoints:
                if entry['waypoint_id'] == wp_id:
                    if entry['image_results'] is None:
                        entry['image_results'] = []
                    entry['image_results'].append(result)
                    break

    def attach_vlm(self, waypoint_id, vlm_result):
        """
        Attache l'analyse VLM (Gemini/Groq) à un waypoint.

        Args:
            waypoint_id: int
            vlm_result: dict — résultat de vlm_analyzer.analyze_soil_ia()
        """
        for entry in self._waypoints:
            if entry['waypoint_id'] == waypoint_id:
                entry['vlm_analysis'] = vlm_result
                return

    def attach_reco(self, waypoint_id, reco_result):
        """
        Attache les recommandations à un waypoint.

        Args:
            waypoint_id: int
            reco_result: dict — résultat de reco_engine.recommend()
        """
        for entry in self._waypoints:
            if entry['waypoint_id'] == waypoint_id:
                entry['recommendations'] = reco_result
                return

    def attach_audio(self, waypoint_id, audio_result):
        """
        Attache le chemin audio TTS à un waypoint.

        Args:
            waypoint_id: int
            audio_result: dict — résultat de tts_engine.speak()
        """
        for entry in self._waypoints:
            if entry['waypoint_id'] == waypoint_id:
                entry['tts_audio'] = audio_result
                return

    def get_summary(self):
        """Retourne le résumé complet de la mission."""
        return {
            'mission': {
                'start_time': self._mission_start,
                'end_time': time.strftime('%Y-%m-%dT%H:%M:%SZ',
                                          time.gmtime()),
                'waypoint_count': len(self._waypoints)
            },
            'waypoints': self._waypoints
        }

    def save_final(self, output_path=None):
        """
        Sauvegarde les résultats complets en JSON.

        Args:
            output_path: chemin du fichier de sortie
                         (défaut: ../data/results.json)
        """
        if output_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, '..', 'data',
                                       'results.json')

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        summary = self.get_summary()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"[LOG] Résultats sauvegardés dans {output_path}")
        return output_path


# Singleton
_logger = None


def get_logger():
    """Retourne l'instance unique du logger."""
    global _logger
    if _logger is None:
        _logger = DataLogger()
    return _logger


def log_waypoint(waypoint_id, sensor_data=None, image_paths=None):
    """Raccourci : enregistre les données d'un waypoint."""
    return get_logger().log_waypoint(waypoint_id, sensor_data, image_paths)


def save_final(output_path=None):
    """Raccourci : sauvegarde les résultats."""
    return get_logger().save_final(output_path)


if __name__ == '__main__':
    print("Test data logger (données simulées)")
    logger = get_logger()

    # Simulation waypoint 1
    logger.log_waypoint(
        1,
        sensor_data={'humidity_pct': 45.2, 'temperature_c': 22.1,
                     'ec_ms_cm': 1.2, 'ph': 6.8},
        image_paths=['data/photos/wp1_001.jpg', 'data/photos/wp1_002.jpg']
    )

    # Simulation waypoint 2
    logger.log_waypoint(
        2,
        sensor_data={'humidity_pct': 38.7, 'temperature_c': 23.4,
                     'ec_ms_cm': 0.9, 'ph': 7.1},
        image_paths=['data/photos/wp2_001.jpg']
    )

    # Sauvegarde
    path = logger.save_final()
    print(f"\nFichier sauvegardé : {path}")
    print(json.dumps(logger.get_summary(), indent=2, ensure_ascii=False))
