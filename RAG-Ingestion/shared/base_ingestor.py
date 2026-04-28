from abc import ABC, abstractmethod


class BaseIngestor(ABC):
    """Abstract base class for all ingestion pipelines."""

    @abstractmethod
    def ingest(self, *args, **kwargs) -> dict:
        """
        Execute the full ingestion pipeline.

        Returns a stats dict describing what was processed and uploaded.
        """
        ...
