from __future__ import annotations

"""
Maps a structured pairwise metrics payload into the engineered feature vector.

Used only by the optional ``pairwise_scoring`` processor and offline training pipelines.
"""

from typing import Dict, List, Tuple

from app.schemas.pairwise_ml import PairwiseMetricsRequest


FEATURE_NAMES: List[str] = [
    "elo_diff",
    "recent_win_pct_diff",
    "points_per_game_diff",
    "points_allowed_diff",
    "turnover_diff",
    "rest_diff",
    "home_advantage",
    "qb_status_diff",
]


def build_pairwise_feature_vector(
    payload: PairwiseMetricsRequest,
) -> Tuple[Dict[str, float], List[float]]:
    elo_diff = float(payload.entity_a_elo - payload.entity_b_elo)
    recent_win_pct_diff = float(
        payload.entity_a_recent_win_pct - payload.entity_b_recent_win_pct
    )
    points_per_game_diff = float(
        payload.entity_a_points_per_game - payload.entity_b_points_per_game
    )
    points_allowed_diff = float(
        payload.entity_a_points_allowed_per_game
        - payload.entity_b_points_allowed_per_game
    )
    turnover_diff = float(
        payload.entity_a_turnover_diff - payload.entity_b_turnover_diff
    )
    rest_diff = float(payload.entity_a_rest_days - payload.entity_b_rest_days)
    home_advantage = 1.0 if payload.primary_plays_at_home else 0.0
    qb_status_diff = float(
        payload.entity_a_lead_status - payload.entity_b_lead_status
    )

    features_dict: Dict[str, float] = {
        "elo_diff": elo_diff,
        "recent_win_pct_diff": recent_win_pct_diff,
        "points_per_game_diff": points_per_game_diff,
        "points_allowed_diff": points_allowed_diff,
        "turnover_diff": turnover_diff,
        "rest_diff": rest_diff,
        "home_advantage": home_advantage,
        "qb_status_diff": qb_status_diff,
    }

    ordered_features = [features_dict[name] for name in FEATURE_NAMES]
    return features_dict, ordered_features
