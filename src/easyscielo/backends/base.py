from typing import Iterator, Optional, Protocol, runtime_checkable

from easyscielo.errors import BackendError
from easyscielo.http import HttpClient
from easyscielo.models import Article, Query

__all__ = ["Backend", "BackendError"]


@runtime_checkable
class Backend(Protocol):
    """Protocol that all easyscielo backends must implement."""

    name: str

    def search(
        self,
        query: Query,
        *,
        n_max: Optional[int] = None,
        client: Optional[HttpClient] = None,
    ) -> Iterator[Article]:
        """Search SciELO and return an iterator of Articles."""
        ...
