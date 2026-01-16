"""AIS data adapters for different data sources."""

from app.ais.adapters.base import (
    AISDataAdapter,
    AISDataFetchError,
    SourceInfo,
)

__all__ = [
    "AISDataAdapter",
    "AISDataFetchError",
    "SourceInfo",
]
