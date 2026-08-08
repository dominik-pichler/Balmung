from distillation.adapters.graph.in_memory import InMemoryGraphRepository
from distillation.domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType


async def test_upsert_nodes_is_idempotent():
    repo = InMemoryGraphRepository()
    node = GraphNode(node_id="abc", type=GraphNodeType.ASSUMPTION, name="ML")
    await repo.upsert_nodes([node, node])
    assert await repo.count_nodes() == 1


async def test_upsert_nodes_merges_properties():
    repo = InMemoryGraphRepository()
    await repo.upsert_nodes(
        [GraphNode(node_id="abc", type=GraphNodeType.ASSUMPTION, name="ML", properties={"a": 1})]
    )
    await repo.upsert_nodes(
        [GraphNode(node_id="abc", type=GraphNodeType.ASSUMPTION, name="ML", properties={"b": 2})]
    )
    nodes = repo.nodes()
    assert nodes[0].properties == {"a": 1, "b": 2}


async def test_upsert_edges_merges_properties():
    repo = InMemoryGraphRepository()
    await repo.upsert_edges(
        [
            GraphEdge(
                source_node_id="s",
                target_node_id="t",
                type=GraphEdgeType.ASSUMES,
                properties={"a": 1},
            )
        ]
    )
    await repo.upsert_edges(
        [
            GraphEdge(
                source_node_id="s",
                target_node_id="t",
                type=GraphEdgeType.ASSUMES,
                properties={"b": 2},
                extraction_confidence=0.7,
            )
        ]
    )
    assert await repo.count_edges() == 1
    edge = repo.edges()[0]
    assert edge.properties == {"a": 1, "b": 2}
    assert edge.extraction_confidence == 0.7
