#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests d'enregistrement vidéo H264 via ffmpeg (V4L2 direct).

Lancement :
    pytest tests/test_video_record.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import tempfile
import time

from src import camera_video as vid


def _show(label, path):
    """Affiche les infos d'une vidéo."""
    if path and os.path.isfile(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"\n  🎥 {label}: {os.path.basename(path)} ({size_kb:.1f} KB)")


@pytest.mark.skipif(not os.path.exists('/dev/video0'),
                    reason="/dev/video0 absent")
class TestVideoRecord:
    """Enregistrement vidéo H264 via ffmpeg + V4L2."""

    @classmethod
    def teardown_class(cls):
        """Nettoie après tous les tests."""
        vid.cleanup()

    def test_record_video_cree_fichier_valide(self):
        """Enregistre 2s → fichier .h264 existe et > 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "test.h264")
            path = vid.record_video(duration_s=2, output_path=out)
            assert path == out
            assert os.path.isfile(path), f"Fichier absent: {path}"
            size_kb = os.path.getsize(path) / 1024
            assert size_kb > 0, f"Fichier vide: {path}"
            _show("Vidéo 2s", path)

    def test_record_video_chemin_auto(self):
        """Sans output_path → data/videos/video_<ts>.h264."""
        path = vid.record_video(duration_s=1)
        try:
            assert path is not None
            assert os.path.isfile(path)
            assert 'data/videos' in path
            assert os.path.getsize(path) > 0
            _show("Vidéo auto", path)
        finally:
            if path and os.path.isfile(path):
                os.remove(path)

    def test_record_video_durees_differentes(self):
        """0.5s vs 1.5s → la plus longue ≥ la plus courte."""
        with tempfile.TemporaryDirectory() as tmpdir:
            short = vid.record_video(
                duration_s=0.5,
                output_path=os.path.join(tmpdir, "short.h264"))
            long_ = vid.record_video(
                duration_s=1.5,
                output_path=os.path.join(tmpdir, "long.h264"))
            size_short = os.path.getsize(short)
            size_long = os.path.getsize(long_)
            _show("Courte (0.5s)", short)
            _show("Longue (1.5s)", long_)
            assert size_long >= size_short, \
                f"Vidéo longue plus petite: {size_long} < {size_short}"

    def test_cleanup_arrete_sans_crash(self):
        """cleanup() après ou sans enregistrement ne crash pas."""
        vid.record_video(duration_s=0.5,
                         output_path=os.path.join(tempfile.gettempdir(),
                                                  "ctest.h264"))
        vid.cleanup()
        vid.cleanup()  # idempotent
        print("\n  ✅ cleanup() idempotent")
