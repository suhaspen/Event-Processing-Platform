"""
Backward-compatible re-exports for pairwise ML schemas.

Prefer importing from ``app.schemas.pairwise_ml`` in new code.
"""

from __future__ import annotations

from app.schemas.pairwise_ml import PairwiseMetricsRequest, PairwiseOutcomeResponse

# Legacy aliases for older imports; prefer ``pairwise_ml`` types in new code.
WinProbabilityRequest = PairwiseMetricsRequest
WinProbabilityResponse = PairwiseOutcomeResponse

__all__ = [
    "PairwiseMetricsRequest",
    "PairwiseOutcomeResponse",
    "WinProbabilityRequest",
    "WinProbabilityResponse",
]
