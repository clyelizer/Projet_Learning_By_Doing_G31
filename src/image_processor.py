#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de traitement asynchrone des images.
Pipeline pour envoyer les photos à un modèle IA spécialisé
et sauvegarder les résultats.

Le traitement se fait en arrière-plan (thread) pour ne pas
bloquer le mouvement du robot entre les waypoints.

Usage:
    python image_processor.py    # test avec images simulées
"""

import threading
import queue
import time


class ImageProcessor:
    """Pipeline de traitement d'images asynchrone."""

    def __init__(self):
        self._queue = queue.Queue()
        self._results = []
        self._running = False
        self._thread = None

    def start(self):
        """Démarre le thread d'arrière-plan s'il n'est pas déjà actif."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def enqueue(self, image_paths, waypoint_id):
        """
        Ajoute des images à traiter en arrière-plan.

        Args:
            image_paths: list[str] — chemins des images
            waypoint_id: int — identifiant du waypoint
        """
        self.start()
        for path in image_paths:
            self._queue.put((path, waypoint_id))
        print(f"[PROC] {len(image_paths)} image(s) du waypoint "
              f"{waypoint_id} mises en file d'attente")

    def _worker(self):
        """Thread d'arrière-plan : traite les images une par une."""
        while self._running:
            try:
                image_path, waypoint_id = self._queue.get(timeout=1)
                result = self._process_one(image_path, waypoint_id)
                self._results.append(result)
                self._queue.task_done()
            except queue.Empty:
                pass  # rien à traiter, on attend
            except Exception as e:
                print(f"[ERROR] Échec traitement image: {e}")
                self._queue.task_done()

    def _process_one(self, image_path, waypoint_id):
        """
        Traite une image : envoie au modèle IA et récupère le résultat.
        PLACEHOLDER — le modèle IA sera intégré ici.
        """
        # TODO: remplacer par l'appel au modèle IA spécialisé
        # Exemple: model_output = ai_model.analyze(image_path)
        model_output = {"status": "placeholder", "image": image_path}

        print(f"[PROC] Image traitée: {image_path} (wp {waypoint_id})")
        return {
            'waypoint_id': waypoint_id,
            'image_path': image_path,
            'model_output': model_output,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

    def wait_all(self, timeout=30):
        """
        Attend que toutes les images en file soient traitées.

        Args:
            timeout: timeout maximum en secondes
        """
        print(f"[PROC] Attente fin des traitements "
              f"({self._queue.qsize()} en attente)...")
        start_time = time.time()
        while self._queue.unfinished_tasks > 0:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"[WARN] Timeout après {timeout}s — "
                      f"{self._queue.unfinished_tasks} tâche(s) restante(s)")
                break
            time.sleep(0.1)
        else:
            print("[PROC] Tous les traitements sont terminés")

    def get_results(self):
        """Retourne la liste des résultats de traitement."""
        return list(self._results)


# Singleton
_processor = None


def get_processor():
    """Retourne l'instance unique du processeur d'images."""
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


if __name__ == '__main__':
    print("Test processeur d'images (mode simulation)")
    proc = get_processor()
    proc.enqueue(['/tmp/test1.jpg', '/tmp/test2.jpg'], waypoint_id=1)
    proc.enqueue(['/tmp/test3.jpg'], waypoint_id=2)
    proc.wait_all()
    results = proc.get_results()
    print(f"\nRésultats ({len(results)} images) :")
    for r in results:
        print(f"  wp{r['waypoint_id']}: {r['image_path']} → {r['model_output']}")
