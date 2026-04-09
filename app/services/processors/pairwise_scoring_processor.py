from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.pairwise_ml import PairwiseMetricsRequest
from app.services.processors.base_processor import (
    BaseProcessor,
    ProcessingContext,
    ProcessorResult,
)
from app.services.processors.pairwise_feature_mapper import (
    FEATURE_NAMES,
    build_pairwise_feature_vector,
)
from app.services.processors.rating_adjustment import win_probabilities_with_home_bias

logger = logging.getLogger(__name__)


@dataclass
class _ArtifactBundle:
    model: object
    feature_names: List[str]
    version: str


class _OptionalArtifactScorer:
    """Loads sklearn artifact from disk if present; otherwise uses rating-only path."""

    def __init__(self) -> None:
        settings = get_settings()
        self._artifact_path: Path = settings.model_path
        self._metadata_path: Path = settings.model_metadata_path
        self._bundle: _ArtifactBundle | None = None
        self._try_load()

    def _try_load(self) -> None:
        if not self._artifact_path.exists() or not self._metadata_path.exists():
            return
        try:
            model = joblib.load(self._artifact_path)
            meta_raw = json.loads(self._metadata_path.read_text(encoding="utf-8"))
            self._bundle = _ArtifactBundle(
                model=model,
                feature_names=list(meta_raw.get("feature_names", FEATURE_NAMES)),
                version=str(meta_raw.get("version", get_settings().model_version)),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("pairwise artifact load failed: %s", exc)
            self._bundle = None

    @property
    def model_active(self) -> bool:
        return self._bundle is not None

    def score(
        self, payload: PairwiseMetricsRequest
    ) -> tuple[Dict[str, float], float, float, str, str]:
        engineered, ordered = build_pairwise_feature_vector(payload)
        if self._bundle is not None:
            x = np.array(ordered, dtype=float).reshape(1, -1)
            proba = self._bundle.model.predict_proba(x)[0, 1]
            p_p, p_c = float(proba), float(1.0 - proba)
            mode, ver = "model", self._bundle.version
        else:
            p_p, p_c = win_probabilities_with_home_bias(
                payload.entity_a_elo,
                payload.entity_b_elo,
                payload.primary_plays_at_home,
            )
            mode, ver = "rating_only", "rating_only"
        total = p_p + p_c
        if total > 0:
            p_p /= total
            p_c /= total
        return engineered, p_p, p_c, mode, ver


_scorer_singleton: _OptionalArtifactScorer | None = None


def _get_scorer() -> _OptionalArtifactScorer:
    global _scorer_singleton
    if _scorer_singleton is None:
        _scorer_singleton = _OptionalArtifactScorer()
    return _scorer_singleton


class PairwiseScoringProcessor(BaseProcessor):
    """
    Optional processor: validates payload as ``PairwiseMetricsRequest`` and attaches scores.

    Enabled only via settings; intended for demo / extension scoring, not core ingestion.
    """

    @property
    def name(self) -> str:
        return "pairwise_scoring"

    def should_process(self, ctx: ProcessingContext) -> bool:
        settings = get_settings()
        if not settings.enable_pairwise_scoring_processor:
            return False
        allowed = {t.strip() for t in settings.pairwise_scoring_event_types.split(",") if t.strip()}
        return ctx.event.event_type in allowed

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        try:
            payload = PairwiseMetricsRequest.model_validate(ctx.event.payload)
        except ValidationError as exc:
            return ProcessorResult(
                processor_name=self.name,
                skipped=True,
                message=f"payload not pairwise-shaped: {exc}",
            )
        try:
            feats, p_p, p_c, mode, ver = _get_scorer().score(payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("pairwise scoring failed")
            return ProcessorResult(
                processor_name=self.name,
                skipped=True,
                message=str(exc),
            )
        return ProcessorResult(
            processor_name=self.name,
            skipped=False,
            output={
                "primary_win_probability": p_p,
                "counterpart_win_probability": p_c,
                "scoring_mode": mode,
                "scoring_version": ver,
                "engineered_features": feats,
            },
        )
