"""
AuraFit — Collaborative Filtering Engine.

Algorithm: ALS (Alternating Least Squares) matrix factorisation for
implicit feedback (Hu, Koren, Volinsky 2008). Implemented via the
`implicit` library (fast C++/CUDA backend).

Training:
  - Runs nightly via Celery Beat (rebuild_cf_model task)
  - Input: user × product confidence matrix
  - Confidence = weighted sum of interactions (purchase=5, save=3, like=2...)
  - Factors: 128, iterations: 20, regularisation: 0.01

Inference:
  - For active users (≥ MIN_INTERACTION_FOR_CF interactions):
    → ALS.recommend(user_id, ...) → top-N product_ids with scores
  - For cold-start users:
    → Fall back to popularity-weighted profile-rule baseline

Persistence:
  - Model saved to /tmp/als_model_{version}.npz after training
  - Loaded on service startup and cached in memory
  - Redis stores per-user candidate sorted sets (TTL: 24h)
"""
from __future__ import annotations

import hashlib
import io
import os
import pickle
import uuid
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MODEL_PATH = "/tmp/aurafit_als_model.pkl"


class CollaborativeFilter:
    """
    ALS-based collaborative filter.
    Call .train(interactions_df) offline.
    Call .recommend(user_id, n) online.
    """

    def __init__(self) -> None:
        self._settings  = get_settings()
        self._model     = None           # implicit ALS model
        self._user_map: dict[str, int]    = {}   # user_id_str → matrix row index
        self._item_map: dict[str, int]    = {}   # product_id_str → matrix col index
        self._item_reverse: dict[int, str] = {}  # col index → product_id_str
        self._is_trained = False

    # ── Training (runs in Celery worker) ─────────────────────────────────────

    def train(self, interactions: list[dict]) -> None:
        """
        Train ALS model on interaction data.

        interactions: list of {user_id, product_id, confidence}
          confidence = sum of interaction weights per user-product pair

        This is CPU-bound and should be called from a Celery task,
        not from an API request handler.
        """
        try:
            from implicit.als import AlternatingLeastSquares
            from scipy.sparse import csr_matrix
        except ImportError:
            logger.warning("cf.implicit_not_installed — skipping training")
            return

        s = self._settings
        logger.info("cf.training_start", interaction_count=len(interactions))

        if not interactions:
            logger.warning("cf.no_interactions — skipping")
            return

        # Build user/item index maps
        users    = sorted({r["user_id"]    for r in interactions})
        products = sorted({r["product_id"] for r in interactions})
        self._user_map     = {u: i for i, u in enumerate(users)}
        self._item_map     = {p: i for i, p in enumerate(products)}
        self._item_reverse = {i: p for p, i in self._item_map.items()}

        # Build sparse user×item confidence matrix
        rows, cols, data = [], [], []
        for r in interactions:
            ui = self._user_map.get(r["user_id"])
            pi = self._item_map.get(r["product_id"])
            if ui is not None and pi is not None:
                rows.append(ui)
                cols.append(pi)
                data.append(float(r["confidence"]))

        user_item = csr_matrix(
            (data, (rows, cols)),
            shape=(len(users), len(products)),
            dtype=np.float32,
        )

        # Train ALS
        self._model = AlternatingLeastSquares(
            factors=s.ALS_FACTORS,
            iterations=s.ALS_ITERATIONS,
            regularization=s.ALS_REGULARIZATION,
            alpha=s.ALS_ALPHA,
            random_state=42,
            use_gpu=False,    # GPU flag — set True if GPU workers are available
        )
        self._model.fit(user_item)
        self._is_trained = True

        # Persist
        self._save()
        logger.info(
            "cf.training_complete",
            users=len(users),
            products=len(products),
            factors=s.ALS_FACTORS,
        )

    def recommend(
        self,
        user_id: str,
        n: int = 300,
        filter_already_interacted: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        """
        Return top-n (product_id, score) pairs for a user.
        Returns empty list for unknown users (cold start).
        """
        if not self._is_trained or self._model is None:
            return []

        user_idx = self._user_map.get(user_id)
        if user_idx is None:
            logger.debug("cf.unknown_user", user_id=user_id)
            return []

        try:
            from scipy.sparse import csr_matrix
            # Reconstruct item matrix row for this user
            user_items = self._model.user_factors[user_idx]
            ids, scores = self._model.recommend(
                user_idx,
                self._build_user_item_row(user_idx),
                N=n,
                filter_already_liked=True,
            )
        except Exception as exc:
            logger.exception("cf.recommend_error", user_id=user_id, error=str(exc))
            return []

        results = []
        for idx, score in zip(ids, scores):
            product_id = self._item_reverse.get(int(idx))
            if product_id:
                # Normalise score to [0, 1]
                results.append((product_id, float(np.clip(score / 10.0, 0.0, 1.0))))
        return results

    def get_similar_products(self, product_id: str, n: int = 20) -> list[tuple[str, float]]:
        """Find products similar to a given product using item factors."""
        if not self._is_trained or self._model is None:
            return []

        item_idx = self._item_map.get(product_id)
        if item_idx is None:
            return []

        try:
            ids, scores = self._model.similar_items(item_idx, N=n + 1)
        except Exception as exc:
            logger.exception("cf.similar_error", product_id=product_id, error=str(exc))
            return []

        return [
            (self._item_reverse[int(i)], float(np.clip(s, 0.0, 1.0)))
            for i, s in zip(ids, scores)
            if int(i) != item_idx and self._item_reverse.get(int(i))
        ][:n]

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            with open(MODEL_PATH, "wb") as f:
                pickle.dump({
                    "model":        self._model,
                    "user_map":     self._user_map,
                    "item_map":     self._item_map,
                    "item_reverse": self._item_reverse,
                }, f)
            logger.info("cf.model_saved", path=MODEL_PATH)
        except Exception as exc:
            logger.error("cf.save_failed", error=str(exc))

    def load(self) -> bool:
        """Load model from disk at startup. Returns True if successful."""
        if not os.path.exists(MODEL_PATH):
            logger.info("cf.no_model_on_disk — will use cold-start until trained")
            return False
        try:
            with open(MODEL_PATH, "rb") as f:
                data = pickle.load(f)
            self._model        = data["model"]
            self._user_map     = data["user_map"]
            self._item_map     = data["item_map"]
            self._item_reverse = data["item_reverse"]
            self._is_trained   = True
            logger.info("cf.model_loaded", users=len(self._user_map), items=len(self._item_map))
            return True
        except Exception as exc:
            logger.error("cf.load_failed", error=str(exc))
            return False

    def _build_user_item_row(self, user_idx: int):
        """Helper: sparse row for user's existing interactions (for recommend filter)."""
        from scipy.sparse import csr_matrix
        # Pass empty row — model handles filtering internally via filter_already_liked
        return csr_matrix((1, max(len(self._item_map), 1)), dtype=np.float32)

    @property
    def is_ready(self) -> bool:
        return self._is_trained


# Global singleton loaded at startup
_cf_model = CollaborativeFilter()


def get_cf_model() -> CollaborativeFilter:
    return _cf_model


def load_cf_model_at_startup() -> None:
    _cf_model.load()
