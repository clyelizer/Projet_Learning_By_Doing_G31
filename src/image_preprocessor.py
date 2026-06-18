#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de preprocessing d'images de sol.

Deux modes d'analyse :
  method='manual'   → implémentations from scratch (learning by doing)
  method='advanced' → OpenCV + scikit-image optimisées (production)

Chaque fonction a un suffixe _manual ou _advanced.
Le dispatcher extract_features() choisit le pipeline selon le paramètre.

Usage:
    python image_preprocessor.py <image.jpg> [--method manual|advanced]
"""

import sys
import os
import time

import numpy as np

# ── Imports optionnels (fallback si absents) ──────────────────────

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from skimage.feature import greycomatrix, greycoprops
    from skimage.filters import gabor
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ── Helpers ───────────────────────────────────────────────────────

def load_image(path):
    """
    Charge une image depuis le disque.
    Priorité : OpenCV → PIL → erreur.
    Retourne un ndarray RGB (H, W, 3).
    """
    if CV2_AVAILABLE:
        img = cv2.imread(path)
        if img is not None:
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if PIL_AVAILABLE:
        img = Image.open(path).convert('RGB')
        return np.array(img)
    raise RuntimeError("Aucune librairie d'image dispo (cv2 ou PIL requis)")


# ═══════════════════════════════════════════════════════════════════
# MODE MANUEL — Implémentations from scratch
# Chaque fonction est codée sans utiliser OpenCV/skimage
# ═══════════════════════════════════════════════════════════════════

def grayscale_manual(img):
    """
    Conversion RGB → niveaux de gris.
    Pondération standard : Y = 0.299R + 0.587G + 0.114B (CIE 1931).
    """
    if img.ndim == 2:
        return img.astype(np.float64)
    return (0.299 * img[:, :, 0].astype(np.float64) +
            0.587 * img[:, :, 1].astype(np.float64) +
            0.114 * img[:, :, 2].astype(np.float64))


def rgb_to_hsv_manual(img):
    """
    Conversion RGB → HSV from scratch.
    Basé sur Smith (1978) "Color Gamut Transform Pairs".

    Returns:
        (H, S, V) — trois ndarrays float64
        H ∈ [0, 360), S ∈ [0, 1], V ∈ [0, 1]
    """
    r = img[:, :, 0].astype(np.float64) / 255.0
    g = img[:, :, 1].astype(np.float64) / 255.0
    b = img[:, :, 2].astype(np.float64) / 255.0

    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    delta = c_max - c_min

    # Hue
    h = np.zeros_like(c_max)
    mask_r = (c_max == r) & (delta != 0)
    mask_g = (c_max == g) & (delta != 0)
    mask_b = (c_max == b) & (delta != 0)

    h[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)
    h[mask_g] = 60.0 * (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2)
    h[mask_b] = 60.0 * (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4)

    # Saturation
    s = np.zeros_like(c_max)
    s[c_max != 0] = delta[c_max != 0] / c_max[c_max != 0]

    # Value
    v = c_max

    return h, s, v


def histogram_manual(img, bins=256):
    """
    Calcule l'histogramme manuellement (sans numpy.histogram).

    Args:
        img: ndarray 2D (grayscale) ou 3D (RGB)
        bins: nombre de bins

    Returns:
        dict avec 'mean', 'std', 'min', 'max', 'hist' (array des comptes)
    """
    flat = img.ravel()
    mn, mx = flat.min(), flat.max()

    if mn == mx:
        hist = np.zeros(bins)
        hist[0] = len(flat)
    else:
        indices = ((flat - mn) / (mx - mn) * (bins - 1)).astype(np.int32)
        indices = np.clip(indices, 0, bins - 1)
        hist = np.bincount(indices, minlength=bins)

    return {
        'mean': float(np.mean(flat)),
        'std': float(np.std(flat)),
        'min': float(mn),
        'max': float(mx),
        'hist': hist
    }


def threshold_otsu_manual(img_gray):
    """
    Algorithme d'Otsu implémenté à la main.
    Trouve le seuil qui minimise la variance intra-classe.

    Réf: Otsu (1979). "A Threshold Selection Method from Gray-Level Histograms".

    Returns:
        float — seuil optimal
    """
    flat = img_gray.ravel().astype(np.int64)
    total = len(flat)
    hist, _ = np.histogram(flat, bins=256, range=(0, 255))

    sum_all = np.dot(np.arange(256), hist)
    sum_b = 0.0
    w_b = 0
    max_var = 0.0
    threshold = 0

    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break

        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f

        var_between = w_b * w_f * (m_b - m_f) ** 2
        if var_between > max_var:
            max_var = var_between
            threshold = t

    return float(threshold)


def sobel_edges_manual(img_gray):
    """
    Détection de contours Sobel 3×3 manuelle.
    Retourne la magnitude du gradient.

    Réf: Sobel & Feldman (1968). "A 3×3 Isotropic Gradient Operator".
    """
    img = img_gray.astype(np.float64)
    h, w = img.shape

    # Noyaux Sobel 3×3
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    ky = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float64)

    gx = np.zeros_like(img)
    gy = np.zeros_like(img)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            patch = img[y - 1:y + 2, x - 1:x + 2]
            gx[y, x] = np.sum(patch * kx)
            gy[y, x] = np.sum(patch * ky)

    return np.sqrt(gx ** 2 + gy ** 2)


def laplacian_var_manual(img_gray):
    """
    Variance du Laplacien — mesure de netteté 'from scratch'.
    Noyau Laplacien 3×3 standard.
    Retourne la variance (float).
    """
    img = img_gray.astype(np.float64)
    h, w = img.shape
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)

    lap = np.zeros_like(img)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            patch = img[y - 1:y + 2, x - 1:x + 2]
            lap[y, x] = np.sum(patch * kernel)

    return float(np.var(lap))


def exg_vegetation_manual(img):
    """
    Excess Green Index — détection de végétation 'from scratch'.
    ExG = 2*G - R - B

    Réf: Woebbecke et al. (1995). Trans. ASAE 38(1).

    Returns:
        float — pourcentage de pixels classés comme végétation
    """
    r = img[:, :, 0].astype(np.float64)
    g = img[:, :, 1].astype(np.float64)
    b = img[:, :, 2].astype(np.float64)

    exg = 2.0 * g - r - b
    veg_mask = exg > 20  # seuil empirique
    return float(np.sum(veg_mask) / veg_mask.size * 100)


# ═══════════════════════════════════════════════════════════════════
# MODE AVANCÉ — Fonctions optimisées via bibliothèques
# ═══════════════════════════════════════════════════════════════════

def color_analysis_advanced(img):
    """
    Analyse couleur avancée : histogrammes HSV + statistiques CIELAB.
    Utilise OpenCV.
    """
    if not CV2_AVAILABLE:
        return {'error': 'OpenCV non disponible'}

    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)

    result = {}

    # HSV
    result['hsv'] = {}
    for ch_name, ch_idx in [('h', 0), ('s', 1), ('v', 2)]:
        data = hsv[:, :, ch_idx]
        result['hsv'][f'{ch_name}_mean'] = float(np.mean(data))
        result['hsv'][f'{ch_name}_std'] = float(np.std(data))
        result['hsv'][f'{ch_name}_median'] = float(np.median(data))

    # CIELAB
    result['lab'] = {}
    for ch_name, ch_idx in [('l', 0), ('a', 1), ('b', 2)]:
        data = lab[:, :, ch_idx]
        result['lab'][f'{ch_name}_mean'] = float(np.mean(data))
        result['lab'][f'{ch_name}_std'] = float(np.std(data))
        result['lab'][f'{ch_name}_median'] = float(np.median(data))

    return result


def texture_advanced(img_gray):
    """
    Analyse de texture avancée : GLCM + Haralick via scikit-image.
    """
    if not SKIMAGE_AVAILABLE:
        return {'error': 'scikit-image non disponible'}

    img_uint8 = img_gray.astype(np.uint8)
    glcm = greycomatrix(img_uint8, [1], [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4],
                        levels=256, symmetric=True, normed=True)

    return {
        'contrast': float(greycoprops(glcm, 'contrast').mean()),
        'dissimilarity': float(greycoprops(glcm, 'dissimilarity').mean()),
        'homogeneity': float(greycoprops(glcm, 'homogeneity').mean()),
        'energy': float(greycoprops(glcm, 'energy').mean()),
        'correlation': float(greycoprops(glcm, 'correlation').mean()),
        'ASM': float(greycoprops(glcm, 'ASM').mean()),
    }


def quality_check_advanced(img_gray):
    """
    Contrôle qualité image : sharpness Laplacian + contraste RMS.
    Utilise OpenCV.
    """
    if not CV2_AVAILABLE:
        return {'error': 'OpenCV non disponible'}

    laplacian = cv2.Laplacian(img_gray.astype(np.uint8), cv2.CV_64F)
    sharpness = float(laplacian.var())

    rms_contrast = float(np.std(img_gray))

    # Classification
    if sharpness < 100:
        quality = 'floue'
    elif sharpness < 500:
        quality = 'acceptable'
    else:
        quality = 'nette'

    return {
        'sharpness': sharpness,
        'rms_contrast': rms_contrast,
        'quality': quality
    }


def segment_soil_advanced(img):
    """
    Segmentation sol vs fond par seuillage HSV + opérations morphologiques.
    Utilise OpenCV.
    """
    if not CV2_AVAILABLE:
        return {'error': 'OpenCV non disponible'}

    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    # Plage "sol" : bruns/rouges/oranges (H 5-35°), saturation > 10%
    lower = np.array([5, 25, 20])
    upper = np.array([35, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    soil_pct = float(np.sum(mask > 0) / mask.size * 100)

    # Végétation via ExG (méthode vectorisée)
    r = img[:, :, 0].astype(np.float64)
    g = img[:, :, 1].astype(np.float64)
    b = img[:, :, 2].astype(np.float64)
    exg = 2 * g - r - b
    veg_pct = float(np.sum(exg > 20) / exg.size * 100)

    return {
        'soil_pct': soil_pct,
        'vegetation_pct': veg_pct,
        'other_pct': round(100 - soil_pct - veg_pct, 1)
    }


def extract_features_advanced(img):
    """Pipeline complet mode avancé."""
    gray = grayscale_manual(img)
    features = {
        'method': 'advanced',
        'color': color_analysis_advanced(img),
        'texture': texture_advanced(gray),
        'quality': quality_check_advanced(gray),
        'composition': segment_soil_advanced(img),
    }
    return features


# ═══════════════════════════════════════════════════════════════════
# PIPELINE MANUEL COMPLET — Agrège toutes les fonctions manuelles
# ═══════════════════════════════════════════════════════════════════

def extract_features_manual(img):
    """Pipeline complet mode manuel — toutes les fonctions from scratch."""
    gray = grayscale_manual(img)
    h, s, v = rgb_to_hsv_manual(img)

    # Histogrammes
    h_hist = histogram_manual(h * 360, bins=36)  # Hue en degrés
    s_hist = histogram_manual(s * 255, bins=32)
    v_hist = histogram_manual(v * 255, bins=32)

    # Texture manuelle — GLCM + Haralick (from scratch aussi !)
    glcm_result = _glcm_manual(gray.astype(np.uint8))
    haralick = _haralick_manual(glcm_result['glcm'])

    # Qualité
    sharp = laplacian_var_manual(gray)
    rms = float(np.std(gray))

    # Végétation
    veg_pct = exg_vegetation_manual(img)

    # Segmentation simple par seuillage teinte
    soil_mask = (h >= 10) & (h <= 40) & (s > 0.1)
    soil_pct = float(np.sum(soil_mask) / soil_mask.size * 100)

    return {
        'method': 'manual',
        'color': {
            'h_mean': h_hist['mean'], 'h_std': h_hist['std'],
            's_mean': s_hist['mean'], 's_std': s_hist['std'],
            'v_mean': v_hist['mean'], 'v_std': v_hist['std'],
        },
        'texture': haralick,
        'quality': {
            'sharpness': sharp,
            'rms_contrast': rms,
            'quality': 'floue' if sharp < 100 else ('acceptable' if sharp < 500 else 'nette'),
        },
        'composition': {
            'soil_pct': soil_pct,
            'vegetation_pct': veg_pct,
            'other_pct': round(100 - soil_pct - veg_pct, 1),
        },
    }


# ═══════════════════════════════════════════════════════════════════
# GLCM + HARALICK MANUEL — Implémentations from scratch
# Ces fonctions sont le coeur du "learning by doing"
# ═══════════════════════════════════════════════════════════════════

def _glcm_manual(img_gray, distance=1, angle=0):
    """
    Matrice de co-occurrence (GLCM) implémentée à la main.

    Basé sur Haralick et al. (1973).

    Args:
        img_gray: ndarray 2D uint8
        distance: distance entre pixels (défaut 1)
        angle: en radians (0 = horizontal, pi/2 = vertical, etc.)

    Returns:
        dict avec 'glcm' (ndarray 2D) et 'levels'
    """
    h, w = img_gray.shape
    levels = 256
    glcm = np.zeros((levels, levels), dtype=np.float64)

    dx = int(round(distance * np.cos(angle)))
    dy = int(round(distance * np.sin(angle)))

    for y in range(h):
        for x in range(w):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                i = int(img_gray[y, x])
                j = int(img_gray[ny, nx])
                glcm[i, j] += 1

    # Normalisation
    total = glcm.sum()
    if total > 0:
        glcm /= total

    return {'glcm': glcm, 'distance': distance, 'angle': angle}


def _haralick_manual(glcm):
    """
    Calcul des 5 caractéristiques de Haralick à partir d'une GLCM.

    Implémenté à la main — chaque formule est codée explicitement.
    """
    levels = glcm.shape[0]
    i_idx, j_idx = np.arange(levels), np.arange(levels)

    # Marginal probabilities
    px = glcm.sum(axis=0)  # p(i)
    py = glcm.sum(axis=1)  # p(j)

    # Means
    mu_x = np.sum(i_idx * px)
    mu_y = np.sum(j_idx * py)

    # Standard deviations
    sigma_x = np.sqrt(np.sum(((i_idx - mu_x) ** 2) * px))
    sigma_y = np.sqrt(np.sum(((j_idx - mu_y) ** 2) * py))

    # Contrast: Σ (i-j)^2 * p(i,j)
    contrast = 0.0
    energy = 0.0
    homogeneity = 0.0
    correlation_num = 0.0

    for i in range(levels):
        for j in range(levels):
            p = glcm[i, j]
            if p == 0:
                continue
            diff = i - j
            contrast += (diff * diff) * p
            energy += p * p
            homogeneity += p / (1.0 + abs(diff))
            correlation_num += (i - mu_x) * (j - mu_y) * p

    # Entropy: -Σ p(i,j) * log2(p(i,j))
    entropy = -np.sum(glcm[glcm > 0] * np.log2(glcm[glcm > 0]))

    # Correlation (éviter division par zéro)
    if sigma_x > 0 and sigma_y > 0:
        correlation = correlation_num / (sigma_x * sigma_y)
    else:
        correlation = 0.0

    return {
        'contrast': round(contrast, 4),
        'energy': round(energy, 6),
        'homogeneity': round(homogeneity, 4),
        'correlation': round(correlation, 4),
        'entropy': round(entropy, 4),
    }


# ═══════════════════════════════════════════════════════════════════
# DISPATCHER — Point d'entrée unique
# ═══════════════════════════════════════════════════════════════════

def extract_features(img, method='manual'):
    """
    Extrait toutes les features d'une image de sol.

    Args:
        img: ndarray RGB (H, W, 3) ou chemin vers fichier image
        method: 'manual' (from scratch) ou 'advanced' (OpenCV/skimage)

    Returns:
        dict structuré avec 'method', 'color', 'texture', 'quality', 'composition'
    """
    if isinstance(img, str):
        img = load_image(img)

    if method == 'advanced':
        if not CV2_AVAILABLE and not SKIMAGE_AVAILABLE:
            print("[WARN] OpenCV/skimage absents — fallback mode manuel")
            method = 'manual'
        else:
            return extract_features_advanced(img)

    return extract_features_manual(img)


# ═══════════════════════════════════════════════════════════════════
# PIPELINE ASYNCHRONE — File d'attente + traitement
# Conservé de l'ancien image_processor.py
# ═══════════════════════════════════════════════════════════════════

import threading
import queue as _queue_mod

class ImageProcessor:
    """Pipeline de traitement d'images asynchrone."""

    def __init__(self):
        self._queue = _queue_mod.Queue()
        self._results = []
        self._running = False
        self._thread = None

    def start(self):
        """Démarre le thread d'arrière-plan."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def stop(self):
        """Arrête proprement le worker."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3)

    def enqueue(self, image_paths, waypoint_id):
        """Ajoute des images à traiter."""
        self.start()
        for path in image_paths:
            self._queue.put((path, waypoint_id))
        print(f"[PROC] {len(image_paths)} image(s) du waypoint {waypoint_id} en file")

    def _worker(self):
        """Thread d'arrière-plan."""
        while self._running:
            try:
                image_path, waypoint_id = self._queue.get(timeout=1)
                result = self._process_one(image_path, waypoint_id)
                self._results.append(result)
                self._queue.task_done()
            except _queue_mod.Empty:
                pass
            except Exception as e:
                print(f"[ERROR] Échec traitement image: {e}")
                # Ne PAS appeler task_done() ici — déjà fait plus haut
                # si _process_one échoue, l'item a déjà été retiré de la queue

    def _process_one(self, image_path, waypoint_id):
        """
        Traite une image : preprocessing manuel → features.
        Le VLM sera branché ici dans la phase suivante.
        """
        features = extract_features(image_path, method='manual')

        print(f"[PROC] Image traitée: {os.path.basename(image_path)} (wp {waypoint_id})")
        return {
            'waypoint_id': waypoint_id,
            'image_path': image_path,
            'features': features,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }

    def wait_all(self, timeout=30):
        """Attend que toutes les images soient traitées."""
        print(f"[PROC] Attente fin traitements ({self._queue.qsize()} en attente)...")
        start_time = time.time()
        while self._queue.unfinished_tasks > 0:
            if time.time() - start_time > timeout:
                print(f"[WARN] Timeout après {timeout}s — "
                      f"{self._queue.unfinished_tasks} tâche(s) restante(s)")
                break
            time.sleep(0.1)
        else:
            print("[PROC] Tous les traitements terminés")

    def get_results(self):
        """Retourne une copie des résultats."""
        return list(self._results)


# Singleton
_processor = None

def get_processor():
    """Retourne l'instance unique du processeur."""
    global _processor
    if _processor is None:
        _processor = ImageProcessor()
    return _processor

def enqueue(image_paths, waypoint_id):
    """Raccourci : ajoute des images au pipeline."""
    return get_processor().enqueue(image_paths, waypoint_id)

def wait_all():
    """Raccourci : attend la fin des traitements."""
    return get_processor().wait_all()

def get_results():
    """Raccourci : récupère les résultats."""
    return get_processor().get_results()


# ── Benchmark ─────────────────────────────────────────────────────

def benchmark(image_path):
    """Compare les deux modes sur une image : résultats + temps d'exécution."""
    img = load_image(image_path)
    print(f"Image: {image_path}  ({img.shape[1]}×{img.shape[0]})\n")

    for method in ('manual', 'advanced'):
        t0 = time.perf_counter()
        result = extract_features(img, method=method)
        elapsed = time.perf_counter() - t0

        if 'error' in result.get('color', {}):
            print(f"[{method}] Erreur: {result['color']['error']}")
            continue

        print(f"--- {method.upper()} ({elapsed*1000:.1f} ms) ---")
        c = result['color']
        t = result['texture']
        q = result['quality']
        comp = result['composition']
        print(f"  Couleur  : H={c.get('h_mean', '?'):.1f}° S={c.get('s_mean', '?'):.3f} V={c.get('v_mean', '?'):.1f}")
        print(f"  Texture  : contrast={t.get('contrast', '?'):.1f} energy={t.get('energy', '?'):.4f}")
        print(f"  Qualité  : sharpness={q.get('sharpness', '?'):.1f} ({q.get('quality', '?')})")
        print(f"  Compos.  : sol={comp.get('soil_pct', '?'):.1f}% veg={comp.get('vegetation_pct', '?'):.1f}%")
        print()


# ── Main ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Preprocessing d'image de sol — manuel vs avancé"
    )
    parser.add_argument('image', help="Chemin vers l'image JPEG")
    parser.add_argument('--method', choices=('manual', 'advanced'), default='manual',
                        help="Mode d'analyse (défaut: manual)")
    parser.add_argument('--bench', action='store_true',
                        help="Benchmark : compare les deux modes")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"Fichier introuvable: {args.image}")
        sys.exit(1)

    if args.bench:
        benchmark(args.image)
    else:
        result = extract_features(args.image, method=args.method)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
