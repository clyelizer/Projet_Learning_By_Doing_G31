#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests camera + processeur d'images — hardware réel, aucun mock.

Lancer :
    pytest tests/test_camera.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import tempfile
import time

import src.camera as cam
from src.image_processor import ImageProcessor, get_processor


# ── camera.py ─────────────────────────────────────────────────────

@pytest.mark.skipif(not cam.CAM_AVAILABLE, reason="Picamera2 absent")
class TestCameraHardware:
    """Tests avec la vraie caméra branchée."""

    @classmethod
    def teardown_class(cls):
        """Éteint la caméra après tous les tests de cette classe."""
        cam.cleanup()

    def test_get_camera_retourne_instance_reelle(self):
        """_get_camera() retourne un objet Picamera2 fonctionnel."""
        c = cam._get_camera()
        assert c is not None
        assert type(c).__name__ == 'Picamera2'

    def test_singleton_reutilise_instance(self):
        """Deux appels → même instance."""
        c1 = cam._get_camera()
        c2 = cam._get_camera()
        assert c1 is c2

    def test_take_photos_cree_fichiers_reels(self):
        """Prend 2 photos et vérifie que les fichiers existent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            photos = cam.take_photos(n=2, delay=0.5, output_dir=tmpdir)
            assert len(photos) == 2
            for p in photos:
                assert os.path.isfile(p), f"Fichier absent: {p}"
                assert os.path.getsize(p) > 0, f"Fichier vide: {p}"
                assert p.startswith(tmpdir)
                basename = os.path.basename(p)
                assert basename.startswith('wp_photo_')
                assert basename.endswith('.jpg')

    def test_take_photos_nommage_correct(self):
        """Pattern wp_photo_<timestamp>_<n>.jpg."""
        with tempfile.TemporaryDirectory() as tmpdir:
            photos = cam.take_photos(n=1, output_dir=tmpdir)
            basename = os.path.basename(photos[0])
            parts = basename.replace('.jpg', '').split('_')
            assert parts[0] == 'wp'
            assert parts[1] == 'photo'
            assert parts[3] == '01'
            assert int(parts[2]) > 0

    def test_take_photos_delai_entre_prises(self):
        """Vérifie que le délai entre prises est respecté (hors warmup)."""
        cam._get_camera()  # absorbe le sleep(2) de warmup
        with tempfile.TemporaryDirectory() as tmpdir:
            start = time.time()
            cam.take_photos(n=3, delay=0.3, output_dir=tmpdir)
            elapsed = time.time() - start
            assert 0.5 <= elapsed < 2.0, f"Délai anormal: {elapsed:.2f}s"

    def test_take_photos_output_dir_par_defaut(self):
        """Sans output_dir explicite, utilise data/photos/."""
        photos = cam.take_photos(n=1)
        try:
            assert len(photos) == 1
            assert 'data/photos' in photos[0]
            assert os.path.isfile(photos[0])
        finally:
            for p in photos:
                if os.path.isfile(p):
                    os.remove(p)

    def test_cleanup_eteint_camera(self):
        """cleanup() arrête la caméra, puis take_photos la relance."""
        cam.cleanup()
        with tempfile.TemporaryDirectory() as tmpdir:
            photos = cam.take_photos(n=1, output_dir=tmpdir)
            assert len(photos) == 1
            assert os.path.isfile(photos[0])


# ── image_processor.py ────────────────────────────────────────────

class TestImageProcessor:
    """Tests du pipeline asynchrone (pas de hardware requis)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.proc = ImageProcessor()

    def test_start_cree_thread_daemon(self):
        assert not self.proc._running
        self.proc.start()
        assert self.proc._running
        assert self.proc._thread is not None
        assert self.proc._thread.daemon is True

    def test_enqueue_et_traitement(self):
        """Enqueue 3 images → le worker les traite toutes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i in range(3):
                p = os.path.join(tmpdir, f"img_{i}.jpg")
                with open(p, 'w') as f:
                    f.write('x')
                paths.append(p)

            self.proc.enqueue(paths, waypoint_id=1)
            self.proc.wait_all(timeout=5)
            results = self.proc.get_results()
            assert len(results) == 3
            for r in results:
                assert r['waypoint_id'] == 1
                assert 'image_path' in r
                assert 'model_output' in r
                assert 'timestamp' in r

    def test_process_one_structure(self):
        """_process_one retourne le bon schéma."""
        result = self.proc._process_one('/tmp/x.jpg', waypoint_id=5)
        assert result['waypoint_id'] == 5
        assert result['image_path'] == '/tmp/x.jpg'
        assert 'model_output' in result
        assert 'timestamp' in result

    def test_wait_all_bloque_sur_queue_pleine(self):
        """wait_all() attend le timeout si le worker ne tourne pas."""
        self.proc._queue.put(('/tmp/a.jpg', 1))
        self.proc._queue.unfinished_tasks = 1
        start = time.time()
        self.proc.wait_all(timeout=1.0)
        elapsed = time.time() - start
        assert elapsed >= 0.9, f"Pas attendu: {elapsed:.2f}s"

    def test_get_results_independant(self):
        """get_results() retourne une copie, pas la liste interne."""
        self.proc.enqueue(['/tmp/a.jpg'], waypoint_id=1)
        self.proc.wait_all(timeout=2)
        r1 = self.proc.get_results()
        r2 = self.proc.get_results()
        assert r1 == r2
        r1.append({'fake': True})
        r3 = self.proc.get_results()
        assert len(r3) == len(r2)

    def test_singleton(self):
        """get_processor() retourne toujours la même instance."""
        p1 = get_processor()
        p2 = get_processor()
        assert p1 is p2
