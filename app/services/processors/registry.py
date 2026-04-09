from __future__ import annotations

from typing import List

from app.services.processors.analytics_rollup_processor import AnalyticsRollupProcessor
from app.services.processors.base_processor import BaseProcessor
from app.services.processors.pairwise_scoring_processor import PairwiseScoringProcessor


def build_default_processors() -> List[BaseProcessor]:
    """
    Ordered processor chain executed after each persisted event.

    Order matters: cheap counters first, heavier optional work last.
    """
    return [
        AnalyticsRollupProcessor(),
        PairwiseScoringProcessor(),
    ]
