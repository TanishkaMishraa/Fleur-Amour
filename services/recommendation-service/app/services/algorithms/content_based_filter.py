"""
AuraFit — Content-Based Filtering Engine.

Algorithm:
  1. Every product has a SBERT text embedding (name + description + key ingredients)
     and optionally a CLIP image embedding. Both stored in product_embeddings.
  2. User preference vector = weighted mean of embeddings of products the user
     has liked / saved / purchased (stored in user_embeddings, rebuilt async).
  3. At query time: cosine ANN search via pgvector to find top-N similar products.
  4. Results merged with CF candidates in the hybrid engine.

Text embedding model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, 80ms/batch)
Image embedding model: openai/clip-vit-base-patch32 (512-dim, loaded on demand)

Embedding rebuilds:
  - Product: nightly or on product update (Celery: refresh_product_embeddings task)
  - User:    after each interaction batch (Celery: rebuild_user_embedding task)
"""
from __future__ import annotations

import uuid
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContentBasedFilter:
    """
    Handles:
      - embed_text(text) → 384-dim vector
      - embed_product(product) → store in product_embeddings
      - rebuild_user_embedding(user_id) → mean of positive interactions
      - find_similar(embedding, n) → ANN via pgvector
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model    = None      # SBERT model (lazy-loaded)

    # ── Embedding generation ──────────────────────────────────────────────────

    def _get_model(self) -> Any:
        """Lazy-load SBERT to avoid startup overhead."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                s = self._settings
                self._model = SentenceTransformer(s.EMBEDDING_MODEL)
                logger.info("cb.sbert_loaded", model=s.EMBEDDING_MODEL)
            except ImportError:
                logger.warning("cb.sentence_transformers_not_installed")
                return None
        return self._model

    def embed_text(self, text: str) -> list[float] | None:
        """Generate a 384-dim SBERT embedding for a text string."""
        model = self._get_model()
        if model is None:
            return None
        try:
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as exc:
            logger.error("cb.embed_error", error=str(exc))
            return None

    def embed_product_text(self, product: Any) -> list[float] | None:
        """
        Build canonical product text and embed it.
        Combines: name, brand, category, description, key ingredients, attributes.
        """
        parts = [product.name]

        if hasattr(product, "brand") and product.brand:
            parts.append(product.brand.name)

        if product.description:
            # Truncate to ~512 chars to stay within model context
            parts.append(product.description[:512])

        if product.ingredients:
            # First 256 chars of ingredients list
            parts.append(f"Ingredients: {product.ingredients[:256]}")

        attrs = product.attributes or {}
        for key in ("shade", "finish", "skin_type", "concern", "family", "notes", "style_tags"):
            val = attrs.get(key)
            if val:
                parts.append(f"{key}: {val}" if isinstance(val, str) else f"{key}: {', '.join(val)}")

        if product.concern_tags:
            parts.append(f"Addresses: {', '.join(product.concern_tags)}")

        text = ". ".join(parts)
        return self.embed_text(text)

    # ── ANN search via pgvector ───────────────────────────────────────────────

    async def find_similar_by_embedding(
        self,
        session: Any,
        query_embedding: list[float],
        n: int = 200,
        domain_filter: str | None = None,
        exclude_ids: list[uuid.UUID] | None = None,
    ) -> list[tuple[str, float]]:
        """
        ANN cosine similarity search via pgvector.
        Returns list of (product_id_str, similarity_score) sorted by score desc.
        """
        from sqlalchemy import text, select
        from pgvector.sqlalchemy import Vector
        from app.models.catalog import ProductEmbedding, Product, Category

        try:
            # pgvector cosine distance query (1 - cosine_distance = similarity)
            vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            query = (
                select(
                    ProductEmbedding.product_id,
                    (1 - ProductEmbedding.text_embedding.cosine_distance(query_embedding))
                    .label("similarity")
                )
                .join(Product, ProductEmbedding.product_id == Product.id)
                .where(Product.is_active == True)   # noqa: E712
                .where(Product.in_stock == True)    # noqa: E712
                .order_by(text("similarity DESC"))
                .limit(n + 10)   # Fetch extra to allow post-filter
            )

            if exclude_ids:
                query = query.where(ProductEmbedding.product_id.not_in(exclude_ids))

            result = await session.execute(query)
            rows   = result.fetchall()

        except Exception as exc:
            logger.exception("cb.ann_error", error=str(exc))
            return []

        return [
            (str(r.product_id), float(r.similarity))
            for r in rows
            if r.similarity is not None and r.similarity > 0.0
        ][:n]

    async def rebuild_user_embedding(
        self,
        session: Any,
        user_id: uuid.UUID,
    ) -> list[float] | None:
        """
        Compute user preference vector as weighted mean of product text embeddings.
        Weights: purchase=5, save=3, like=2, try_on=2, view=0.5
        Stores result in user_embeddings table.
        """
        from sqlalchemy import select, insert, update
        from app.models.catalog import UserProductInteraction, ProductEmbedding, UserEmbedding

        WEIGHTS = {
            "purchase": 5.0, "save": 3.0, "like": 2.0,
            "try_on": 2.0, "review": 2.5, "view": 0.5,
        }

        try:
            # Get positive interactions for this user
            rows = (await session.execute(
                select(UserProductInteraction.product_id, UserProductInteraction.interaction_type)
                .where(UserProductInteraction.user_id == user_id)
                .where(UserProductInteraction.interaction_type.in_(list(WEIGHTS.keys())))
            )).fetchall()

            if not rows:
                return None

            # Fetch embeddings for these products
            product_ids = list({r.product_id for r in rows})
            emb_rows = (await session.execute(
                select(ProductEmbedding.product_id, ProductEmbedding.text_embedding)
                .where(ProductEmbedding.product_id.in_(product_ids))
                .where(ProductEmbedding.text_embedding.isnot(None))
            )).fetchall()

            if not emb_rows:
                return None

            emb_map = {str(r.product_id): np.array(r.text_embedding) for r in emb_rows}

            # Weighted mean
            weighted_sum = np.zeros(self._settings.EMBEDDING_DIM)
            total_weight = 0.0
            for row in rows:
                pid  = str(row.product_id)
                wt   = WEIGHTS.get(row.interaction_type, 0.5)
                emb  = emb_map.get(pid)
                if emb is not None:
                    weighted_sum += wt * emb
                    total_weight += wt

            if total_weight == 0:
                return None

            mean_vec = weighted_sum / total_weight
            # L2 normalise
            norm = np.linalg.norm(mean_vec)
            if norm > 0:
                mean_vec /= norm

            embedding_list = mean_vec.tolist()

            # Upsert into user_embeddings
            existing = (await session.execute(
                select(UserEmbedding).where(UserEmbedding.user_id == user_id)
            )).scalar_one_or_none()

            if existing:
                existing.text_embedding     = embedding_list
                existing.interaction_count  = len(rows)
                session.add(existing)
            else:
                session.add(UserEmbedding(
                    user_id=user_id,
                    text_embedding=embedding_list,
                    interaction_count=len(rows),
                    model_version="1.0.0",
                ))

            await session.flush()
            logger.info("cb.user_embedding_rebuilt", user_id=str(user_id), interactions=len(rows))
            return embedding_list

        except Exception as exc:
            logger.exception("cb.rebuild_user_embedding_error", user_id=str(user_id), error=str(exc))
            return None

    async def get_user_embedding(self, session: Any, user_id: uuid.UUID) -> list[float] | None:
        """Retrieve stored user preference vector."""
        from sqlalchemy import select
        from app.models.catalog import UserEmbedding

        result = await session.execute(
            select(UserEmbedding.text_embedding)
            .where(UserEmbedding.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return row if row else None


# Module-level singleton
_cb_filter = ContentBasedFilter()


def get_cb_filter() -> ContentBasedFilter:
    return _cb_filter
