"""GraphRetriever: top-k seeding + one-hop expansion."""

from distillation.adapters.embedders.fake import FakeEmbedder
from distillation.adapters.graph.in_memory import InMemoryGraphRepository
from distillation.domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from distillation.retrieval import GraphRetriever, _node_text


async def _repo() -> InMemoryGraphRepository:
    repo = InMemoryGraphRepository()
    a = GraphNode(node_id="a", type=GraphNodeType.TECHNOLOGY, name="Transformer")
    b = GraphNode(node_id="b", type=GraphNodeType.PROBLEM, name="Scaling")
    c = GraphNode(node_id="c", type=GraphNodeType.DATASET, name="WikiText")
    await repo.upsert_nodes([a, b, c])
    # a → b only; c is unconnected.
    await repo.upsert_edges(
        [GraphEdge(source_node_id="a", target_node_id="b", type=GraphEdgeType.ABOUT)]
    )
    return repo


async def test_one_hop_includes_neighbours_and_touching_edges():
    repo = await _repo()
    retriever = GraphRetriever(repo, FakeEmbedder())

    seed = GraphNode(node_id="a", type=GraphNodeType.TECHNOLOGY, name="Transformer")
    nodes, edges = await retriever.retrieve(_node_text(seed), k=1)

    ids = {n.node_id for n in nodes}
    # Seed 'a' plus its one-hop neighbour 'b'; unconnected 'c' excluded.
    assert "a" in ids and "b" in ids
    assert "c" not in ids
    assert any(e.source_node_id == "a" and e.target_node_id == "b" for e in edges)


async def test_retrieve_on_empty_graph_returns_empty():
    repo = InMemoryGraphRepository()
    retriever = GraphRetriever(repo, FakeEmbedder())
    nodes, edges = await retriever.retrieve("anything", k=5)
    assert nodes == []
    assert edges == []
