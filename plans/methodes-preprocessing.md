# Méthodes de Preprocessing d'Images — Sol Agricole

> Recherche pour le module `image_preprocessor.py` — Learning By Doing G31
> Date: 2026-06-17

---

## 1. Objectif

Extraire des caractéristiques (features) numériques d'une photo de sol pour :
1. Compléter l'analyse VLM (Gemini/Groq) avec des données quantitatives
2. Permettre des comparaisons objectives entre waypoints
3. Détecter automatiquement la qualité de l'image (flou, sous-exposition)

Aucun deep learning. Algorithmes classiques de vision par ordinateur uniquement.

---

## 2. Espaces Couleur pour l'Analyse de Sol

### 2.1 Conversion RGB → HSV

**Pourquoi :** Le sol est mieux caractérisé par sa teinte (H), saturation (S) et luminosité (V) que par ses canaux RGB. La teinte est directement corrélée au type de sol (argileux = rouge/orange, organique = brun foncé/noir, sableux = beige/jaune).

**Référence :** Smith, A.R. (1978). "Color Gamut Transform Pairs". *SIGGRAPH '78*. → Base théorique du modèle HSV.

**Formule :**
```
V = max(R,G,B)
S = (V - min(R,G,B)) / V  (si V ≠ 0)
H = selon le canal dominant (0°-360°)
```

**Implémentation :** OpenCV `cv2.cvtColor(img, cv2.COLOR_RGB2HSV)` + numpy pour l'histogramme.

### 2.2 CIELAB (L*a*b*)

**Pourquoi :** Espace perceptuellement uniforme. La distance euclidienne entre deux couleurs dans L*a*b* correspond à la différence perçue par l'œil humain. Utile pour comparer objectivement la couleur du sol entre deux échantillons.

- **L\*** : luminosité (0 = noir, 100 = blanc) → corrélé à la matière organique
- **a\*** : axe vert (−) → rouge (+) → indicateur d'oxydes de fer
- **b\*** : axe bleu (−) → jaune (+) → indicateur de carbonates

**Référence :** Viscarra Rossel, R.A. et al. (2006). "Colour space models for soil science". *Geoderma*, 133(3-4). → Application directe à la pédologie.

---

## 3. Analyse de Texture — Matrice de Co-occurrence (GLCM)

### 3.1 Principe

La GLCM compte la fréquence d'apparition de paires de pixels avec une valeur de gris donnée, séparés par une distance et un angle spécifiques. À partir de la GLCM, on extrait les **caractéristiques de Haralick**.

### 3.2 Caractéristiques de Haralick

| Feature | Formule simplifiée | Interprétation sol |
|---------|-------------------|-------------------|
| **Contraste** | Σ(i−j)²·p(i,j) | Texture grossière vs fine |
| **Corrélation** | Σ(i−μ)(j−μ)·p(i,j)/σ² | Structure régulière du sol |
| **Énergie** | Σp(i,j)² | Uniformité — sol homogène vs hétérogène |
| **Homogénéité** | Σp(i,j)/(1+|i−j|) | Similarité des pixels voisins |
| **Entropie** | −Σp(i,j)·log(p(i,j)) | Désordre — sol avec cailloux, racines |

**Référence :** Haralick, R.M., Shanmugam, K., & Dinstein, I. (1973). "Textural Features for Image Classification". *IEEE Trans. Systems, Man, Cybernetics*, SMC-3(6).

### 3.3 Implémentation

```python
from skimage.feature import greycomatrix, greycoprops
# Image en niveaux de gris, 256 niveaux, distance=1, 4 angles (0°,45°,90°,135°)
glcm = greycomatrix(gray_img, [1], [0, np.pi/4, np.pi/2, 3*np.pi/4], levels=256)
contrast = greycoprops(glcm, 'contrast').mean()
correlation = greycoprops(glcm, 'correlation').mean()
energy = greycoprops(glcm, 'energy').mean()
homogeneity = greycoprops(glcm, 'homogeneity').mean()
```

**Pourquoi 4 angles :** Moyenner sur 0°, 45°, 90°, 135° rend la mesure invariante à la rotation (le sol n'a pas d'orientation préférentielle).

---

## 4. Détection de Végétation

### 4.1 Indice Excess Green (ExG)

**Pourquoi :** Distinguer les pixels de végétation (feuilles, tiges) du sol nu. L'ExG exploite la dominance du canal vert dans la végétation.

**Formule :**
```
ExG = 2·G − R − B
```
Seuil empirique : ExG > 20 → végétation.

**Référence :** Woebbecke, D.M. et al. (1995). "Color indices for weed identification under various soil, residue, and lighting conditions". *Trans. ASAE*, 38(1).

### 4.2 Vegetation Area Ratio

```
vegetation_pct = (nb_pixels_ExG_positifs / nb_pixels_total) × 100
```

Utile pour estimer la couverture végétale sans VLM.

---

## 5. Mesure de Netteté (Sharpness)

### 5.1 Variance du Laplacien

**Pourquoi :** Détecter les photos floues (mouvement du robot, mauvaise mise au point). Une variance faible = image floue.

**Formule :** Appliquer un filtre Laplacien (dérivée seconde), puis calculer la variance des pixels résultants.

```python
laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
sharpness = laplacian.var()
```

**Seuils empiriques :**
- `sharpness < 100` → flou, image probablement inutilisable
- `100 ≤ sharpness < 500` → acceptable
- `sharpness ≥ 500` → nette

**Référence :** Pech-Pacheco, J.L. et al. (2000). "Diatom autofocusing in brightfield microscopy". *ICPR 2000*.

### 5.2 Contraste Global (RMS Contrast)

```
RMS = sqrt( Σ(I(x,y) − μ)² / N )
```

Complément au Laplacien : détecte les images sous-exposées (contraste faible) vs bien exposées.

---

## 6. Segmentation Sol / Fond

### 6.1 Approche par seuillage HSV

1. Convertir en HSV
2. Définir une plage de teinte « sol » (H ∈ [10°, 40°] pour bruns/rouges, S > 10% pour éviter le gris)
3. Créer un masque binaire
4. Appliquer des opérations morphologiques (ouverture + fermeture)

```python
hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
lower = np.array([10, 25, 20])   # H min, S min, V min
upper = np.array([40, 255, 255]) # H max, S max, V max
mask = cv2.inRange(hsv, lower, upper)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
soil_pct = np.sum(mask > 0) / mask.size * 100
```

### 6.2 Approche alternative — Otsu + Contours

Si le seuillage HSV est insuffisant (éclairage variable) :
1. Conversion en niveaux de gris
2. Seuillage d'Otsu (automatique, pas de seuil manuel)
3. Plus grand contour → région d'intérêt

**Référence :** Otsu, N. (1979). "A Threshold Selection Method from Gray-Level Histograms". *IEEE Trans. Systems, Man, Cybernetics*, 9(1).

---

## 7. Résumé — Fonctions à Implémenter

| Fonction | Input | Output | Libre |
|----------|-------|--------|-------|
| `load_image(path)` | chemin | ndarray (RGB) | PIL/OpenCV |
| `rgb_to_hsv(img)` | ndarray | (H,S,V arrays) | OpenCV |
| `color_histogram(img)` | ndarray | dict(mean_h, std_h, mean_s, ...) | numpy |
| `texture_glcm(img)` | grayscale ndarray | dict(contrast, energy, ...) | skimage |
| `detect_vegetation(img)` | ndarray | float (0–100%) | numpy |
| `compute_sharpness(img)` | grayscale ndarray | float | OpenCV |
| `compute_contrast(img)` | grayscale ndarray | float (RMS) | numpy |
| `segment_soil(img)` | ndarray | mask, soil_pct | OpenCV |
| `extract_features(img)` | ndarray | dict (toutes les features agrégées) | toutes |

### Output de `extract_features()` — Dict type

```json
{
  "color": {
    "h_mean": 25.3, "h_std": 8.1,
    "s_mean": 45.2, "s_std": 12.4,
    "v_mean": 120.5, "v_std": 30.1,
    "lab_l_mean": 48.2, "lab_a_mean": 12.5, "lab_b_mean": 22.3
  },
  "texture": {
    "contrast": 145.2, "energy": 0.34,
    "homogeneity": 0.72, "correlation": 0.88
  },
  "quality": {
    "sharpness": 342.5,
    "rms_contrast": 52.1
  },
  "composition": {
    "soil_pct": 78.3,
    "vegetation_pct": 15.2,
    "other_pct": 6.5
  }
}
```

---

## 8. Dépendances Python

```
numpy
opencv-python       # cv2
scikit-image        # skimage.feature (GLCM)
Pillow              # PIL (fallback chargement)
```

---

## 9. Références Complètes

1. **Smith, A.R.** (1978). Color Gamut Transform Pairs. *SIGGRAPH '78*, 12(3), 12-19.
2. **Viscarra Rossel, R.A., Minasny, B., Roudier, P., & McBratney, A.B.** (2006). Colour space models for soil science. *Geoderma*, 133(3-4), 320-337.
3. **Haralick, R.M., Shanmugam, K., & Dinstein, I.** (1973). Textural Features for Image Classification. *IEEE Trans. Systems, Man, Cybernetics*, SMC-3(6), 610-621.
4. **Woebbecke, D.M., Meyer, G.E., Von Bargen, K., & Mortensen, D.A.** (1995). Color indices for weed identification under various soil, residue, and lighting conditions. *Trans. ASAE*, 38(1), 259-269.
5. **Pech-Pacheco, J.L., Cristóbal, G., Chamorro-Martinez, J., & Fernández-Valdivia, J.** (2000). Diatom autofocusing in brightfield microscopy: a comparative study. *ICPR 2000*, 314-317.
6. **Otsu, N.** (1979). A Threshold Selection Method from Gray-Level Histograms. *IEEE Trans. Systems, Man, Cybernetics*, 9(1), 62-66.
7. **Russ, J.C.** (2016). *The Image Processing Handbook* (7th ed.). CRC Press. — Référence générale complète.
