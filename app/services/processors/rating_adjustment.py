from __future__ import annotations

"""
Elo-style expected score helpers for optional pairwise scoring.

Not used by core event ingestion when pairwise processing is disabled.
"""

from math import pow

from app.core.config import get_settings


def expected_score(rating_a: float, rating_b: float) -> float:
    exponent = (rating_b - rating_a) / 400.0
    return 1.0 / (1.0 + pow(10.0, exponent))


def win_probabilities_with_home_bias(
    rating_primary: float,
    rating_counterpart: float,
    primary_plays_at_home: bool,
) -> tuple[float, float]:
    settings = get_settings()
    adjusted_primary = float(rating_primary)
    adjusted_counterpart = float(rating_counterpart)

    if primary_plays_at_home:
        adjusted_primary += settings.home_field_elo_bonus

    p_primary = expected_score(adjusted_primary, adjusted_counterpart)
    p_counterpart = 1.0 - p_primary
    return p_primary, p_counterpart
