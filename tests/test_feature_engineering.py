import pandas as pd

from app.ml.features import build_training_features
from app.services.processors.pairwise_feature_mapper import (
    FEATURE_NAMES,
    build_pairwise_feature_vector,
)
from app.schemas.pairwise_ml import PairwiseMetricsRequest


def test_feature_names_match() -> None:
    assert FEATURE_NAMES == [
        "elo_diff",
        "recent_win_pct_diff",
        "points_per_game_diff",
        "points_allowed_diff",
        "turnover_diff",
        "rest_diff",
        "home_advantage",
        "qb_status_diff",
    ]


def test_build_features_and_training_alignment() -> None:
    payload = PairwiseMetricsRequest.model_validate(
        {
            "team_a": "A",
            "team_b": "B",
            "team_a_elo": 1600,
            "team_b_elo": 1500,
            "team_a_recent_win_pct": 0.7,
            "team_b_recent_win_pct": 0.5,
            "team_a_points_per_game": 27.0,
            "team_b_points_per_game": 24.0,
            "team_a_points_allowed_per_game": 20.0,
            "team_b_points_allowed_per_game": 23.0,
            "team_a_turnover_diff": 5,
            "team_b_turnover_diff": 1,
            "team_a_rest_days": 7,
            "team_b_rest_days": 6,
            "is_team_a_home": True,
            "team_a_starting_qb_status": 1.0,
            "team_b_starting_qb_status": 0.9,
        }
    )

    features_dict, ordered = build_pairwise_feature_vector(payload)

    assert set(features_dict.keys()) == set(FEATURE_NAMES)
    assert len(ordered) == len(FEATURE_NAMES)

    df = pd.DataFrame(
        [
            {
                "team_a_elo": payload.entity_a_elo,
                "team_b_elo": payload.entity_b_elo,
                "team_a_recent_win_pct": payload.entity_a_recent_win_pct,
                "team_b_recent_win_pct": payload.entity_b_recent_win_pct,
                "team_a_points_per_game": payload.entity_a_points_per_game,
                "team_b_points_per_game": payload.entity_b_points_per_game,
                "team_a_points_allowed_per_game": payload.entity_a_points_allowed_per_game,
                "team_b_points_allowed_per_game": payload.entity_b_points_allowed_per_game,
                "team_a_turnover_diff": payload.entity_a_turnover_diff,
                "team_b_turnover_diff": payload.entity_b_turnover_diff,
                "team_a_rest_days": payload.entity_a_rest_days,
                "team_b_rest_days": payload.entity_b_rest_days,
                "is_team_a_home": payload.primary_plays_at_home,
                "team_a_starting_qb_status": payload.entity_a_lead_status,
                "team_b_starting_qb_status": payload.entity_b_lead_status,
                "team_a_won": 1,
            }
        ]
    )

    X, y = build_training_features(df)

    assert list(X.columns) == FEATURE_NAMES
    assert y.iloc[0] == 1
