"""
Data access layer (repositories) for persistence abstractions.
"""

from app.repositories.analytics_snapshot_repository import AnalyticsSnapshotRepository
from app.repositories.event_repository import EventRepository
from app.repositories.processor_result_repository import ProcessorResultRepository

__all__ = [
    "AnalyticsSnapshotRepository",
    "EventRepository",
    "ProcessorResultRepository",
]
