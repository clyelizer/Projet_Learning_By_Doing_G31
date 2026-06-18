#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests image_preprocessor — modes manuel et avancé.

Lancement :
    pytest tests/test_image_preprocessor.py -v -s
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import numpy as np
import tempfile
import time

from image_preprocessor import (
    load_image, grayscale_manual, rgb_to_hsv_manual,
    histogram_manual, threshold_otsu_manual,
    sobel_edges_manual, laplacian_var_manual,
    exg_vegetation_manual, extract_features,
    _glcm_manual, _haralick_manual,
    CV2_AVAILABLE, SKIMAGE_AVAILABLE,
)

# ── Trouver une photo de test ─────────────────────────────────────

def _find_photo():
    photos_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'photos')
    if not os.path.isdir(photos_dir):
        return None
    for f in sorted(os.listdir(photos_dir)):
        if f.endswith('.jpg'):
            return os.path.join(photos_dir, f)
    return None

_PHOTO = _find_photo()


# ═══════════════════════════════════════════════════════════════════
# MODE MANUEL — Toutes les fonctions from scratch
# ═══════════════════════════════════════════════════════════════════

class TestManualFunctions:
    """Tests des implémentations manuelles (sans OpenCV)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Crée une image RGB synthétique 100×100."""
        rng = np.random.RandomState(42)
        self.img = rng.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        self.gray = self.img.mean(axis=2)  # référence

    def test_grayscale_output_shape(self):
        """La conversion grayscale préserve la taille spatiale."""
        result = grayscale_manual(self.img)
        assert result.shape == (100, 100)

    def test_grayscale_values_in_range(self):
        """Les valeurs sont dans [0, 255]."""
        result = grayscale_manual(self.img)
        assert result.min() >= 0
        assert result.max() <= 255

    def test_grayscale_pure_white(self):
        """Image blanche → 255."""
        white = np.ones((10, 10, 3), dtype=np.uint8) * 255
        result = grayscale_manual(white)
        assert np.allclose(result, 255, atol=1)

    def test_grayscale_pure_black(self):
        """Image noire → 0."""
        black = np.zeros((10, 10, 3), dtype=np.uint8)
        result = grayscale_manual(black)
        assert np.allclose(result, 0, atol=1)

    def test_rgb_to_hsv_shapes(self):
        """HSV retourne 3 canaux de même taille."""
        h, s, v = rgb_to_hsv_manual(self.img)
        assert h.shape == (100, 100)
        assert s.shape == (100, 100)
        assert v.shape == (100, 100)

    def test_rgb_to_hsv_ranges(self):
        """H ∈ [0, 360), S ∈ [0, 1], V ∈ [0, 1]."""
        h, s, v = rgb_to_hsv_manual(self.img)
        assert h.min() >= 0 and h.max() < 360
        assert s.min() >= 0 and s.max() <= 1
        assert v.min() >= 0 and v.max() <= 1

    def test_rgb_to_hsv_pure_red(self):
        """Rouge pur → H≈0°, S≈1, V≈1."""
        red = np.zeros((5, 5, 3), dtype=np.uint8)
        red[:, :, 0] = 255
        h, s, v = rgb_to_hsv_manual(red)
        assert np.allclose(h[0, 0], 0, atol=1)
        assert np.allclose(s[0, 0], 1, atol=0.01)
        assert np.allclose(v[0, 0], 1, atol=0.01)

    def test_rgb_to_hsv_pure_green(self):
        """Vert pur → H≈120°."""
        green = np.zeros((5, 5, 3), dtype=np.uint8)
        green[:, :, 1] = 255
        h, s, v = rgb_to_hsv_manual(green)
        assert np.allclose(h[0, 0], 120, atol=1)

    def test_rgb_to_hsv_pure_blue(self):
        """Bleu pur → H≈240°."""
        blue = np.zeros((5, 5, 3), dtype=np.uint8)
        blue[:, :, 2] = 255
        h, s, v = rgb_to_hsv_manual(blue)
        assert np.allclose(h[0, 0], 240, atol=1)

    def test_histogram_output_keys(self):
        """Retourne mean, std, min, max, hist."""
        result = histogram_manual(self.gray)
        for key in ('mean', 'std', 'min', 'max', 'hist'):
            assert key in result

    def test_histogram_sum_equals_total(self):
        """La somme des bins = nombre de pixels."""
        result = histogram_manual(self.gray, bins=32)
        assert result['hist'].sum() == 100 * 100

    def test_histogram_uniform(self):
        """Image constante → histogramme avec un seul pic."""
        const = np.ones((50, 50)) * 128
        result = histogram_manual(const, bins=256)
        assert result['std'] == 0
        assert result['min'] == result['max']

    def test_otsu_bimodal(self):
        """Otsu sur image bimodale simple."""
        bimodal = np.zeros((100, 100))
        bimodal[:, :50] = 50   # moitié sombre
        bimodal[:, 50:] = 200  # moitié claire
        thresh = threshold_otsu_manual(bimodal)
        # Le seuil doit être entre les deux modes (inclus)
        assert 50 <= thresh <= 200

    def test_otsu_uniform(self):
        """Otsu sur image uniforme → retourne un seuil valide."""
        uniform = np.ones((50, 50)) * 100
        thresh = threshold_otsu_manual(uniform)
        assert 0 <= thresh <= 255

    def test_sobel_output_shape(self):
        """Sobel préserve la taille spatiale."""
        edges = sobel_edges_manual(self.gray)
        assert edges.shape == (100, 100)

    def test_sobel_zero_on_constant(self):
        """Image constante → pas de contours."""
        const = np.ones((50, 50)) * 100
        edges = sobel_edges_manual(const)
        # Le centre ne devrait pas avoir de gradient (les bords oui à cause du padding)
        assert edges[25, 25] == 0

    def test_laplacian_var_positive(self):
        """La variance du Laplacien est ≥ 0."""
        sharp = laplacian_var_manual(self.gray)
        assert sharp >= 0

    def test_laplacian_var_blurry_vs_sharp(self):
        """Image floue → variance plus faible."""
        # Image nette (bruit)
        sharp = laplacian_var_manual(self.gray)
        # Image floutée (moyennée)
        from scipy.ndimage import uniform_filter
        blurred = uniform_filter(self.gray, size=5)
        blurry = laplacian_var_manual(blurred)
        assert blurry < sharp, f"blurry={blurry} >= sharp={sharp}"

    def test_exg_vegetation_output_range(self):
        """ExG retourne un pourcentage entre 0 et 100."""
        pct = exg_vegetation_manual(self.img)
        assert 0 <= pct <= 100

    def test_exg_green_image(self):
        """Image verte → végétation détectée."""
        green = np.zeros((50, 50, 3), dtype=np.uint8)
        green[:, :, 1] = 200  # G élevé, R et B bas
        green[:, :, 0] = 20
        green[:, :, 2] = 20
        pct = exg_vegetation_manual(green)
        assert pct > 50, f"ExG devrait détecter la végétation: {pct:.1f}%"

    def test_exg_brown_image(self):
        """Image brune → pas de végétation."""
        brown = np.ones((50, 50, 3), dtype=np.uint8) * 100
        brown[:, :, 0] = 120  # plus de rouge
        brown[:, :, 1] = 80   # moins de vert
        pct = exg_vegetation_manual(brown)
        assert pct < 10, f"ExG ne devrait pas détecter de vég: {pct:.1f}%"


# ═══════════════════════════════════════════════════════════════════
# GLCM + HARALICK MANUEL
# ═══════════════════════════════════════════════════════════════════

class TestGlcmHaralick:
    """Tests GLCM + Haralick from scratch."""

    def test_glcm_shape(self):
        """GLCM est 256×256."""
        img = np.random.randint(0, 256, (32, 32), dtype=np.uint8)
        result = _glcm_manual(img)
        assert result['glcm'].shape == (256, 256)

    def test_glcm_sums_to_one(self):
        """GLCM normalisée → somme ≈ 1."""
        img = np.random.randint(0, 256, (64, 64), dtype=np.uint8)
        result = _glcm_manual(img)
        assert abs(result['glcm'].sum() - 1.0) < 1e-6

    def test_haralick_keys(self):
        """Retourne les 5 features Haralick."""
        img = np.random.randint(0, 256, (64, 64), dtype=np.uint8)
        glcm_result = _glcm_manual(img)
        features = _haralick_manual(glcm_result['glcm'])
        for key in ('contrast', 'energy', 'homogeneity', 'correlation', 'entropy'):
            assert key in features, f"Manque: {key}"

    def test_haralick_constant_image(self):
        """Image uniforme → contrast=0, energy=1, homogeneity=1."""
        img = np.ones((64, 64), dtype=np.uint8) * 128
        glcm_result = _glcm_manual(img)
        features = _haralick_manual(glcm_result['glcm'])
        assert features['contrast'] == 0
        assert features['energy'] > 0.99
        assert features['homogeneity'] > 0.99


# ═══════════════════════════════════════════════════════════════════
# MODE AVANCÉ (OpenCV requis)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV absent")
class TestAdvancedFunctions:
    """Tests des fonctions avancées OpenCV."""

    @pytest.fixture(autouse=True)
    def setup(self):
        rng = np.random.RandomState(42)
        self.img = rng.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    def test_color_analysis_returns_hsv_and_lab(self):
        from image_preprocessor import color_analysis_advanced
        result = color_analysis_advanced(self.img)
        assert 'hsv' in result
        assert 'lab' in result
        assert 'h_mean' in result['hsv']
        assert 'l_mean' in result['lab']

    def test_quality_check_returns_quality_label(self):
        from image_preprocessor import quality_check_advanced
        gray = self.img.mean(axis=2)
        result = quality_check_advanced(gray)
        assert 'sharpness' in result
        assert 'rms_contrast' in result
        assert result['quality'] in ('floue', 'acceptable', 'nette')

    def test_segment_soil_returns_percentages(self):
        from image_preprocessor import segment_soil_advanced
        result = segment_soil_advanced(self.img)
        assert 'soil_pct' in result
        assert 'vegetation_pct' in result
        total = result['soil_pct'] + result['vegetation_pct'] + result['other_pct']
        assert abs(total - 100) < 1, f"Total={total}"

    @pytest.mark.skipif(not SKIMAGE_AVAILABLE, reason="scikit-image absent")
    def test_texture_advanced(self):
        from image_preprocessor import texture_advanced
        gray = self.img.mean(axis=2)
        result = texture_advanced(gray)
        assert 'contrast' in result
        assert 'homogeneity' in result


# ═══════════════════════════════════════════════════════════════════
# TEST SUR PHOTO RÉELLE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.skipif(_PHOTO is None, reason="Pas de photo dans data/photos/")
class TestRealPhoto:
    """Tests avec une vraie photo du robot."""

    def test_load_real_photo(self):
        """Charge une photo réelle sans erreur."""
        img = load_image(_PHOTO)
        assert img is not None
        assert img.ndim == 3
        assert img.shape[2] == 3

    def test_extract_features_manual(self):
        """Mode manuel sur photo réelle → dict structuré."""
        result = extract_features(_PHOTO, method='manual')
        assert result['method'] == 'manual'
        assert 'color' in result
        assert 'texture' in result
        assert 'quality' in result
        assert 'composition' in result
        # Afficher les résultats
        print(f"\n  📷 {os.path.basename(_PHOTO)} "
              f"({result['quality']['sharpness']:.0f} sharp, "
              f"{result['quality']['quality']})")

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV absent")
    def test_extract_features_advanced(self):
        """Mode avancé sur photo réelle → dict structuré."""
        result = extract_features(_PHOTO, method='advanced')
        assert 'method' in result
        assert 'color' in result
        print(f"\n  📷 Advanced: HSV H={result['color']['hsv']['h_mean']:.1f}°")

    @pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV absent")
    def test_benchmark_both_modes(self):
        """Benchmark : compare les temps manuel vs avancé."""
        t0 = time.perf_counter()
        manual = extract_features(_PHOTO, method='manual')
        t_manual = time.perf_counter() - t0

        t0 = time.perf_counter()
        advanced = extract_features(_PHOTO, method='advanced')
        t_advanced = time.perf_counter() - t0

        print(f"\n  ⏱️  Manual: {t_manual*1000:.0f}ms | Advanced: {t_advanced*1000:.0f}ms | "
              f"Ratio: {t_manual/t_advanced:.1f}×")

        # Les deux modes doivent donner des résultats cohérents
        assert manual['quality']['quality'] == advanced['quality']['quality']


# ═══════════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Cas limites et robustesse."""

    def test_grayscale_already_gray(self):
        """Image déjà en niveaux de gris → pas d'erreur."""
        gray = np.random.randint(0, 255, (32, 32)).astype(np.float64)
        result = grayscale_manual(gray)
        assert result.shape == (32, 32)

    def test_hsv_black_image(self):
        """Image noire → H=0, S=0, V=0."""
        black = np.zeros((5, 5, 3), dtype=np.uint8)
        h, s, v = rgb_to_hsv_manual(black)
        assert np.all(v == 0)
        assert np.all(s == 0)

    def test_histogram_single_value(self):
        """Image avec une seule valeur."""
        single = np.ones((20, 20)) * 42
        result = histogram_manual(single, bins=256)
        assert result['mean'] == 42
        assert result['std'] == 0

    def test_exg_all_black(self):
        """Image noire → 0% végétation."""
        black = np.zeros((10, 10, 3), dtype=np.uint8)
        pct = exg_vegetation_manual(black)
        assert pct == 0
