from app.core.config import get_settings
from app.services.processors.rating_adjustment import (
    expected_score,
    win_probabilities_with_home_bias,
)


def test_elo_expected_score_symmetry() -> None:
    p_a = expected_score(1600, 1600)
    assert 0.49 < p_a < 0.51


def test_elo_home_field_advantage() -> None:
    """
    Home boost for primary should match neutral odds when counterpart is weakened
    by the same rating margin.
    """
    settings = get_settings()
    h = settings.home_field_elo_bonus
    prob_home, _ = win_probabilities_with_home_bias(1600, 1600, primary_plays_at_home=True)
    prob_equiv, _ = win_probabilities_with_home_bias(
        1600, 1600 - h, primary_plays_at_home=False
    )
    assert abs(prob_home - prob_equiv) < 1e-9
