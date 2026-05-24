from distillation.domain.distillate import (
    AffiliationMention,
    AuthorMention,
    ConclusionMention,
    Distillate,
    MethodologyMention,
    TheoryMention,
    TopicMention,
)
from distillation.domain.document import DocumentFormat, DocumentMetadata, SourceDocument
from distillation.domain.graph import GraphEdgeType, GraphNodeType
from distillation.mapping.graph_mapper import GraphMapper


def _doc() -> SourceDocument:
    return SourceDocument(
        metadata=DocumentMetadata(
            tenant_id="test", source_id="paper.txt", uri="file:///paper.txt"
        ),
        format=DocumentFormat.TEXT,
        raw_bytes=b"contents",
    )


def _distillate(doc: SourceDocument) -> Distillate:
    return Distillate(
        document_id=doc.document_id,
        chunk_ids=["c0", "c1"],
        topics=[
            TopicMention(name="Knowledge Graphs", theme="AI", provenance_chunk_ids=["c0"]),
        ],
        authors=[
            AuthorMention(
                name="Alice Smith",
                affiliation=AffiliationMention(name="MIT"),
                interests=["Knowledge Graphs"],
                provenance_chunk_ids=["c0"],
            )
        ],
        theories=[TheoryMention(name="Lens Theory", provenance_chunk_ids=["c0"])],
        conclusions=[
            ConclusionMention(
                name="Lenses Work",
                statement="Lens-based distillation works.",
                supports_theories=["Lens Theory"],
                provenance_chunk_ids=["c1"],
            )
        ],
        methodologies=[MethodologyMention(name="LLM Extraction", provenance_chunk_ids=["c1"])],
    )


def test_mapper_produces_expected_node_types():
    doc = _doc()
    d = _distillate(doc)
    nodes, _ = GraphMapper("test").map(doc, d)
    node_types = {n.type for n in nodes}
    assert node_types == {
        GraphNodeType.SOURCE,
        GraphNodeType.TOPIC,
        GraphNodeType.THEME,
        GraphNodeType.AUTHOR,
        GraphNodeType.AFFILIATION,
        GraphNodeType.THEORY,
        GraphNodeType.CONCLUSION,
        GraphNodeType.METHODOLOGY,
    }


def test_mapper_produces_solid_arrow_edges():
    doc = _doc()
    d = _distillate(doc)
    _, edges = GraphMapper("test").map(doc, d)
    edge_types = {e.type for e in edges}
    # Solid (Source → entity) arrows we expect for this distillate
    assert {
        GraphEdgeType.DISCUSSES,
        GraphEdgeType.AUTHORED_BY,
        GraphEdgeType.BUILDS,
        GraphEdgeType.CONCLUDES,
        GraphEdgeType.USES,
        GraphEdgeType.IS_AT,
        GraphEdgeType.BELONGS_TO,
        GraphEdgeType.HAS_INTEREST,
        GraphEdgeType.SUPPORTS,
    }.issubset(edge_types)


def test_mapper_is_deterministic():
    doc = _doc()
    d = _distillate(doc)
    n1, e1 = GraphMapper("test").map(doc, d)
    n2, e2 = GraphMapper("test").map(doc, d)
    assert {n.node_id for n in n1} == {n.node_id for n in n2}
    assert {e.edge_key for e in e1} == {e.edge_key for e in e2}


def test_mapper_carries_provenance_on_edges():
    doc = _doc()
    d = _distillate(doc)
    _, edges = GraphMapper("test").map(doc, d)
    # Every primary edge should carry at least one chunk in provenance.
    primary_types = {
        GraphEdgeType.DISCUSSES,
        GraphEdgeType.AUTHORED_BY,
        GraphEdgeType.BUILDS,
        GraphEdgeType.CONCLUDES,
        GraphEdgeType.USES,
    }
    for e in edges:
        if e.type in primary_types:
            assert e.provenance_chunk_ids, f"Edge {e.type} missing provenance"
