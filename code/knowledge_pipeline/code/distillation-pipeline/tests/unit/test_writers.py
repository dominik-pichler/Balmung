"""Writer semantics: MERGE (L1/L3) vs paper-scoped (L2), and edge confidence."""

from distillation.domain.distillate import (
    AuthorMention,
    ClaimMention,
    TechnologyMention,
)
from distillation.domain.graph import GraphEdgeType, GraphNodeType
from distillation.mapping.domain_writer import DomainWriter
from distillation.mapping.epistemic_writer import EpistemicWriter
from distillation.mapping.provenance_writer import ProvenanceWriter


def test_domain_nodes_merge_on_canonical_name():
    """L1: same canonical name (per tenant+type) → same node_id (MERGE key)."""
    dw = DomainWriter()
    a = dw.write_technologies([TechnologyMention(name="BERT")], "t")[0]
    b = dw.write_technologies([TechnologyMention(name=" bert ")], "t")[0]
    assert a.node_id == b.node_id
    assert a.type is GraphNodeType.TECHNOLOGY


def test_l2_claim_nodes_never_merge_across_papers():
    """L2: identical claim in two papers → distinct node ids (CREATE semantics)."""
    ew = EpistemicWriter(DomainWriter())
    claim = ClaimMention(name="x", text="Our method beats the baseline")
    assert ew.claim_id(claim, "paperA", "t") != ew.claim_id(claim, "paperB", "t")


def test_claim_edges_carry_extraction_confidence():
    ew = EpistemicWriter(DomainWriter())
    _, edges = ew.write_claims(
        [ClaimMention(name="x", text="t", extraction_confidence=0.7)],
        paper_id="p",
        tenant_id="t",
    )
    makes = [e for e in edges if e.type is GraphEdgeType.MAKES_CLAIM]
    assert makes and makes[0].source_node_id == "p"
    assert makes[0].extraction_confidence == 0.7


def test_authored_by_anchors_on_paper():
    pw = ProvenanceWriter()
    _, edges = pw.write_authors(
        [AuthorMention(name="Alice", extraction_confidence=0.9)],
        paper_id="p",
        tenant_id="t",
    )
    authored = [e for e in edges if e.type is GraphEdgeType.AUTHORED_BY]
    assert authored and authored[0].source_node_id == "p"
    assert authored[0].extraction_confidence == 0.9


def test_author_orcid_takes_priority_over_name():
    pw = ProvenanceWriter()
    with_orcid = AuthorMention(name="Alice", orcid="0000-0002-1825-0097")
    same_name_no_orcid = AuthorMention(name="Alice")
    assert pw.author_id(with_orcid, "t") != pw.author_id(same_name_no_orcid, "t")
