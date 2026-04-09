from __future__ import annotations

from typing import Dict, List

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class PairwiseMetricsRequest(BaseModel):
    """
    Structured payload for the **optional** ``pairwise_scoring`` processor and offline training.

    Not used by core event APIs unless that processor is enabled. Accepts ``entity_*`` or
    legacy ``team_*`` JSON keys.
    """

    model_config = ConfigDict(populate_by_name=True)

    entity_a: str = Field(
        ...,
        validation_alias=AliasChoices("entity_a", "team_a"),
        description="Label for the primary side (e.g. competitor A)",
    )
    entity_b: str = Field(
        ...,
        validation_alias=AliasChoices("entity_b", "team_b"),
        description="Label for the counterpart side (e.g. competitor B)",
    )

    entity_a_elo: int = Field(..., validation_alias=AliasChoices("entity_a_elo", "team_a_elo"))
    entity_b_elo: int = Field(..., validation_alias=AliasChoices("entity_b_elo", "team_b_elo"))

    entity_a_recent_win_pct: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("entity_a_recent_win_pct", "team_a_recent_win_pct"),
    )
    entity_b_recent_win_pct: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("entity_b_recent_win_pct", "team_b_recent_win_pct"),
    )

    entity_a_points_per_game: float = Field(
        ..., validation_alias=AliasChoices("entity_a_points_per_game", "team_a_points_per_game")
    )
    entity_b_points_per_game: float = Field(
        ..., validation_alias=AliasChoices("entity_b_points_per_game", "team_b_points_per_game")
    )

    entity_a_points_allowed_per_game: float = Field(
        ...,
        validation_alias=AliasChoices(
            "entity_a_points_allowed_per_game", "team_a_points_allowed_per_game"
        ),
    )
    entity_b_points_allowed_per_game: float = Field(
        ...,
        validation_alias=AliasChoices(
            "entity_b_points_allowed_per_game", "team_b_points_allowed_per_game"
        ),
    )

    entity_a_turnover_diff: float = Field(
        ..., validation_alias=AliasChoices("entity_a_turnover_diff", "team_a_turnover_diff")
    )
    entity_b_turnover_diff: float = Field(
        ..., validation_alias=AliasChoices("entity_b_turnover_diff", "team_b_turnover_diff")
    )

    entity_a_rest_days: int = Field(
        ..., ge=0, validation_alias=AliasChoices("entity_a_rest_days", "team_a_rest_days")
    )
    entity_b_rest_days: int = Field(
        ..., ge=0, validation_alias=AliasChoices("entity_b_rest_days", "team_b_rest_days")
    )

    primary_plays_at_home: bool = Field(
        ...,
        validation_alias=AliasChoices("primary_plays_at_home", "is_team_a_home"),
        description="True if entity A has home-field-style advantage applied at scoring time",
    )

    entity_a_lead_status: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "entity_a_lead_status", "team_a_starting_qb_status"
        ),
        description="Normalized strength/availability signal for entity A (0–1)",
    )
    entity_b_lead_status: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "entity_b_lead_status", "team_b_starting_qb_status"
        ),
        description="Normalized strength/availability signal for entity B (0–1)",
    )

    @field_validator("entity_a", "entity_b")
    @classmethod
    def non_empty_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Entity labels must be non-empty")
        return value


class PairwiseOutcomeResponse(BaseModel):
    """Scoring output for a pairwise metrics payload (offline / future API use)."""

    entity_a: str
    entity_b: str
    primary_win_probability: float = Field(..., ge=0.0, le=1.0)
    counterpart_win_probability: float = Field(..., ge=0.0, le=1.0)
    scoring_mode: str = Field(..., description='e.g. "model" or "elo_only"')
    model_version: str
    engineered_features: Dict[str, float]
