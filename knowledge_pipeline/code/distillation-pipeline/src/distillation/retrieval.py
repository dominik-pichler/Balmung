"""Semantic retrieval over the knowledge graph.

Strategy:
  1. Embed all nodes (text derived from type + name + key properties).
  2. Embed the query.
  3. Rank nodes by cosine similarity, take top-k.
  4. Expand one hop: include every edge that touches a seed node, plus the
     neighbour nodes on the other end.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .domain.graph import GraphEdge, GraphNode
from .ports.embedder import Embedder
from .ports.graph_repository import GraphRepository

# Properties whose text content enriches the embedding signal.
_TEXT_PROPS = ("statement", "description", "interests")


class GraphRetriever:
    def __init__(self, repository: GraphRepository, embedder: Embedder) -> None:
        self._repository = repository
        self._embedder = embedder

    async def retrieve(
        self, query: str, *, k: int = 5
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Return the top-k nodes most similar to *query* plus their 1-hop neighbourhood."""
        nodes = await self._repository.all_nodes()
        if not nodes:
            return [], []

        # Embed query and all nodes in one batch call.
        texts = [_node_text(n) for n in nodes]
        embeddings = await self._embedder.embed([query, *texts])
        query_emb = embeddings[0]
        node_embs = embeddings[1:]

        scores = [_cosine(query_emb, e) for e in node_embs]
        top_k = min(k, len(nodes))
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        seed_ids = {nodes[i].node_id for i in top_indices}

        # One-hop expansion.
        all_edges = await self._repository.all_edges()
        subgraph_node_ids: set[str] = set(seed_ids)
        subgraph_edges: list[GraphEdge] = []
        for edge in all_edges:
            if edge.source_node_id in seed_ids or edge.target_node_id in seed_ids:
                subgraph_edges.append(edge)
                subgraph_node_ids.add(edge.source_node_id)
                subgraph_node_ids.add(edge.target_node_id)

        node_map = {n.node_id: n for n in nodes}
        subgraph_nodes = [node_map[nid] for nid in subgraph_node_ids if nid in node_map]
        return subgraph_nodes, subgraph_edges


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_text(node: GraphNode) -> str:
    parts = [f"{node.type.value}: {node.name}"]
    for key in _TEXT_PROPS:
        val = node.properties.get(key)
        if isinstance(val, list):
            parts.extend(str(v) for v in val if v)
        elif val:
            parts.append(str(val))
    return ". ".join(parts)


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
