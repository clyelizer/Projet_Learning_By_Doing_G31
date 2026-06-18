#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test d'intégration — capture photo réelle via Picamera2.

Lancement :
    pytest tests/test_cam_live.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import time
import tempfile

import src.camera as cam


def _show(prefix, photo_paths):
    """Affiche les chemins des photos prises."""
    print(f"\n  {prefix}")
    for i, p in enumerate(photo_paths, 1):
        size_kb = os.path.getsize(p) / 1024
        print(f"    📷 Photo {i}: {os.path.basename(p)} ({size_kb:.1f} KB)")


@pytest.mark.skipif(not cam.CAM_AVAILABLE, reason="Picamera2 absent")
class TestCameraLive:
    """Capture réelle avec la caméra branchée."""

    @classmethod
    def teardown_class(cls):
        """Éteint la caméra après tous les tests."""
        cam.cleanup()

    def test_take_photos_cree_images_valides(self):
        """Prend 2 photos — les fichiers existent et ont une taille > 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            photos = cam.take_photos(n=2, delay=0.5, output_dir=tmpdir)
            assert len(photos) == 2, f"Attendu 2 photos, reçu {len(photos)}"
            _show("Photos capturées :", photos)
            for p in photos:
                assert os.path.isfile(p), f"Fichier absent: {p}"
                assert os.path.getsize(p) > 0, f"Fichier vide: {p}"

    def test_trois_photos_avec_delai(self):
        """Prend 3 photos avec délai de 0.3s — vérifie le délai total."""
        cam._get_camera()  # absorbe le sleep(2) de warmup
        with tempfile.TemporaryDirectory() as tmpdir:
            start = time.time()
            photos = cam.take_photos(n=3, delay=0.3, output_dir=tmpdir)
            elapsed = time.time() - start
            assert len(photos) == 3
            _show("3 photos avec délai :", photos)
            # Délai mini: 2 intervalles × 0.3s = 0.6s, marge de latence
            assert 0.5 <= elapsed < 3.0, f"Délai anormal: {elapsed:.2f}s"

    def test_photo_unique_sans_delai(self):
        """Une seule photo — pas de délai inutile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            start = time.time()
            photos = cam.take_photos(n=1, output_dir=tmpdir)
            elapsed = time.time() - start
            assert len(photos) == 1
            assert os.path.isfile(photos[0])
            _show("Photo unique :", photos)
            # Une seule photo doit être rapide (< 1s, pas de delay entre prises)
            assert elapsed < 2.0, f"Trop lent pour 1 photo: {elapsed:.2f}s"

    def test_photos_consecutives_stables(self):
        """Deux sessions de capture consécutives — les photos sont distinctes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            batch1 = cam.take_photos(n=1, output_dir=tmpdir)
            assert len(batch1) == 1
            time.sleep(0.5)
            batch2 = cam.take_photos(n=1, output_dir=tmpdir)
            assert len(batch2) == 1
            _show("Session 1 :", batch1)
            _show("Session 2 :", batch2)

            # Les fichiers doivent être distincts (timestamps différents)
            assert batch1[0] != batch2[0]

            # Les deux fichiers doivent exister
            for p in batch1 + batch2:
                assert os.path.isfile(p)

    def test_cleanup_puis_reprise(self):
        """Après cleanup(), la caméra peut être relancée."""
        cam.cleanup()
        # Après cleanup, _camera est None, on peut reprendre
        c = cam._get_camera()
        assert c is not None, "La caméra n'a pas pu être ré-initialisée"
        with tempfile.TemporaryDirectory() as tmpdir:
            photos = cam.take_photos(n=1, output_dir=tmpdir)
            assert len(photos) == 1
            assert os.path.isfile(photos[0])
            _show("Reprise après cleanup :", photos)
