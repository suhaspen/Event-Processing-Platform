from __future__ import annotations

from typing import Tuple

import pandas as pd

from app.ml.training_csv_adapter import normalize_training_columns
from app.services.processors.pairwise_feature_mapper import FEATURE_NAMES


def build_training_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Build feature matrix X and target y from a training dataframe.

    Accepts either legacy CSV headers (``team_a_elo``, …) or canonical names
    (``entity_a_elo``, …) after ``normalize_training_columns``.
    """
    df = normalize_training_columns(df)

    elo_diff = df["entity_a_elo"] - df["entity_b_elo"]
    recent_win_pct_diff = (
        df["entity_a_recent_win_pct"] - df["entity_b_recent_win_pct"]
    )
    points_per_game_diff = (
        df["entity_a_points_per_game"] - df["entity_b_points_per_game"]
    )
    points_allowed_diff = (
        df["entity_a_points_allowed_per_game"]
        - df["entity_b_points_allowed_per_game"]
    )
    turnover_diff = (
        df["entity_a_turnover_diff"] - df["entity_b_turnover_diff"]
    )
    rest_diff = df["entity_a_rest_days"] - df["entity_b_rest_days"]
    home_advantage = df["primary_plays_at_home"].astype(float)
    qb_status_diff = (
        df["entity_a_lead_status"] - df["entity_b_lead_status"]
    )

    X = pd.DataFrame(
        {
            "elo_diff": elo_diff,
            "recent_win_pct_diff": recent_win_pct_diff,
            "points_per_game_diff": points_per_game_diff,
            "points_allowed_diff": points_allowed_diff,
            "turnover_diff": turnover_diff,
            "rest_diff": rest_diff,
            "home_advantage": home_advantage,
            "qb_status_diff": qb_status_diff,
        }
    )[FEATURE_NAMES]

    y = df["primary_outcome_positive"].astype(int)
    return X, y
