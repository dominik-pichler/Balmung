from distillation.adapters.graph.in_memory import InMemoryGraphRepository
from distillation.domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType


async def test_upsert_nodes_is_idempotent():
    repo = InMemoryGraphRepository()
    node = GraphNode(node_id="abc", type=GraphNodeType.TOPIC, name="ML")
    await repo.upsert_nodes([node, node])
    assert await repo.count_nodes() == 1


async def test_upsert_nodes_merges_properties():
    repo = InMemoryGraphRepository()
    await repo.upsert_nodes(
        [GraphNode(node_id="abc", type=GraphNodeType.TOPIC, name="ML", properties={"a": 1})]
    )
    await repo.upsert_nodes(
        [GraphNode(node_id="abc", type=GraphNodeType.TOPIC, name="ML", properties={"b": 2})]
    )
    nodes = repo.nodes()
    assert nodes[0].properties == {"a": 1, "b": 2}


async def test_upsert_edges_merges_provenance():
    repo = InMemoryGraphRepository()
    await repo.upsert_edges(
        [
            GraphEdge(
                source_node_id="s",
                target_node_id="t",
                type=GraphEdgeType.DISCUSSES,
                provenance_chunk_ids=["c0"],
            )
        ]
    )
    await repo.upsert_edges(
        [
            GraphEdge(
                source_node_id="s",
                target_node_id="t",
                type=GraphEdgeType.DISCUSSES,
                provenance_chunk_ids=["c1"],
            )
        ]
    )
    assert await repo.count_edges() == 1
    assert repo.edges()[0].provenance_chunk_ids == ["c0", "c1"]
