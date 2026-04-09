"""
Pluggable post-ingestion processors.

Core platform behavior does not depend on optional modules (e.g. pairwise scoring).
"""

from app.services.processors.base_processor import (
    BaseProcessor,
    ProcessingContext,
    ProcessorResult,
)
from app.services.processors.registry import build_default_processors

__all__ = [
    "BaseProcessor",
    "ProcessingContext",
    "ProcessorResult",
    "build_default_processors",
]
