from __future__ import annotations

"""
Normalize legacy training CSV column names into canonical ``entity_*`` / ``primary_*`` names.

Public APIs and processors use generic names; bundled sample data keeps historical headers.
"""

from typing import Dict

import pandas as pd

# Legacy column name -> canonical name used after normalization
LEGACY_COLUMN_RENAME: Dict[str, str] = {
    "team_a_elo": "entity_a_elo",
    "team_b_elo": "entity_b_elo",
    "team_a_recent_win_pct": "entity_a_recent_win_pct",
    "team_b_recent_win_pct": "entity_b_recent_win_pct",
    "team_a_points_per_game": "entity_a_points_per_game",
    "team_b_points_per_game": "entity_b_points_per_game",
    "team_a_points_allowed_per_game": "entity_a_points_allowed_per_game",
    "team_b_points_allowed_per_game": "entity_b_points_allowed_per_game",
    "team_a_turnover_diff": "entity_a_turnover_diff",
    "team_b_turnover_diff": "entity_b_turnover_diff",
    "team_a_rest_days": "entity_a_rest_days",
    "team_b_rest_days": "entity_b_rest_days",
    "is_team_a_home": "primary_plays_at_home",
    "team_a_starting_qb_status": "entity_a_lead_status",
    "team_b_starting_qb_status": "entity_b_lead_status",
    "team_a_won": "primary_outcome_positive",
}


def normalize_training_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {k: v for k, v in LEGACY_COLUMN_RENAME.items() if k in df.columns}
    return df.rename(columns=rename)
