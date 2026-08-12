"""Port: graph persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from ..domain.graph import GraphEdge, GraphNode


class GraphRepository(ABC):
    """Idempotent upsert of nodes and edges.

    Implementations MUST treat ``GraphNode.node_id`` and the
    ``(source, type, target)`` triple as primary keys for upsert semantics.
    Re-ingesting the same source must not duplicate anything.
    """

    @abstractmethod
    async def upsert_nodes(self, nodes: Iterable[GraphNode]) -> None:
        """Insert or update nodes by ``node_id``."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_edges(self, edges: Iterable[GraphEdge]) -> None:
        """Insert or update edges by ``(source_id, type, target_id)``."""
        raise NotImplementedError

    @abstractmethod
    async def count_nodes(self) -> int:
        """Total number of stored nodes — useful for tests and health checks."""
        raise NotImplementedError

    @abstractmethod
    async def count_edges(self) -> int:
        """Total number of stored edges."""
        raise NotImplementedError

    @abstractmethod
    async def all_nodes(self) -> list[GraphNode]:
        """Return every node in the repository."""
        raise NotImplementedError

    @abstractmethod
    async def all_edges(self) -> list[GraphEdge]:
        """Return every edge in the repository."""
        raise NotImplementedError

    async def close(self) -> None:
        """Release any underlying connections. Default is a no-op."""
        return
