"""EdgeLinker: relationship + structural edges, with dangling-edge filtering."""

from distillation.domain.distillate import (
    AssumptionMention,
    CapabilityMention,
    ClaimMention,
    Distillate,
    EvidenceMention,
    ProblemMention,
)
from distillation.domain.graph import GraphEdgeType
from distillation.domain.ontology import EvidenceType
from distillation.mapping.domain_writer import DomainWriter
from distillation.mapping.edges import EdgeLinker
from distillation.mapping.epistemic_writer import EpistemicWriter
from distillation.mapping.provenance_writer import ProvenanceWriter

TENANT = "t"
PAPER = "paper1"


def _linker() -> EdgeLinker:
    return EdgeLinker(EpistemicWriter(DomainWriter()), ProvenanceWriter())


def test_addresses_edge_created_when_problem_exists():
    dw = DomainWriter()
    caps = [CapabilityMention(name="Efficient attention", addresses="Scaling")]
    probs = [ProblemMention(name="Scaling")]
    nodes = dw.write_capabilities(caps, TENANT) + dw.write_problems(probs, TENANT)
    dist = Distillate(paper_id=PAPER, chunk_ids=[], capabilities=caps, problems=probs)

    edges = _linker().link(nodes, dist, tenant_id=TENANT, paper_id=PAPER)
    addresses = [e for e in edges if e.type is GraphEdgeType.ADDRESSES]
    assert len(addresses) == 1
    assert addresses[0].extraction_confidence is not None


def test_dangling_edge_is_dropped():
    """A reference to an entity that was not extracted produces no edge."""
    dw = DomainWriter()
    caps = [CapabilityMention(name="X", addresses="NoSuchProblem")]
    nodes = dw.write_capabilities(caps, TENANT)
    dist = Distillate(paper_id=PAPER, chunk_ids=[], capabilities=caps)

    edges = _linker().link(nodes, dist, tenant_id=TENANT, paper_id=PAPER)
    assert not any(e.type is GraphEdgeType.ADDRESSES for e in edges)


def test_supported_by_vs_refuted_by_from_evidence_type():
    dw = DomainWriter()
    ew = EpistemicWriter(dw)
    claim = ClaimMention(name="Beats baseline", text="Our method beats the baseline")
    supporting = EvidenceMention(name="Gain", type=EvidenceType.supporting, claim="Beats baseline")
    refuting = EvidenceMention(name="Regression", type=EvidenceType.refuting, claim="Beats baseline")

    claim_nodes, _ = ew.write_claims([claim], paper_id=PAPER, tenant_id=TENANT)
    ev_nodes, _ = ew.write_evidence([supporting, refuting], paper_id=PAPER, tenant_id=TENANT)
    dist = Distillate(
        paper_id=PAPER, chunk_ids=[], claims=[claim], evidence=[supporting, refuting]
    )

    edges = _linker().link(claim_nodes + ev_nodes, dist, tenant_id=TENANT, paper_id=PAPER)
    kinds = {e.type for e in edges}
    assert GraphEdgeType.SUPPORTED_BY in kinds
    assert GraphEdgeType.REFUTED_BY in kinds


def test_assumes_links_only_referenced_assumptions():
    """Regression: a claim links to the assumptions in its ``assumes`` list only,
    not to every assumption in the paper (the old cross-product bug)."""
    dw = DomainWriter()
    ew = EpistemicWriter(dw)
    a1 = AssumptionMention(name="A1")
    a2 = AssumptionMention(name="A2")
    c1 = ClaimMention(name="c1", text="claim one", assumes=["A1"])
    c2 = ClaimMention(name="c2", text="claim two")  # rests on no assumption

    claim_nodes, _ = ew.write_claims([c1, c2], paper_id=PAPER, tenant_id=TENANT)
    assum_nodes = dw.write_assumptions([a1, a2], TENANT)
    dist = Distillate(
        paper_id=PAPER, chunk_ids=[], claims=[c1, c2], assumptions=[a1, a2]
    )

    edges = _linker().link(
        claim_nodes + assum_nodes, dist, tenant_id=TENANT, paper_id=PAPER
    )
    assumes = [e for e in edges if e.type is GraphEdgeType.ASSUMES]
    assert len(assumes) == 1  # NOT 4 — no cross-product
    assert assumes[0].source_node_id == ew.claim_id(c1, PAPER, TENANT)
    assert assumes[0].target_node_id == dw.assumption_id(a1, TENANT)


def test_write_claims_emits_no_assumes_edge():
    """ASSUMES is now built by the EdgeLinker, not the claim writer."""
    ew = EpistemicWriter(DomainWriter())
    _, edges = ew.write_claims(
        [ClaimMention(name="x", text="t", assumes=["A"])],
        paper_id=PAPER,
        tenant_id=TENANT,
    )
    assert all(e.type is not GraphEdgeType.ASSUMES for e in edges)
    assert any(e.type is GraphEdgeType.MAKES_CLAIM for e in edges)


def test_every_linked_edge_has_confidence_in_range():
    dw = DomainWriter()
    caps = [CapabilityMention(name="C", addresses="P", extraction_confidence=0.4)]
    probs = [ProblemMention(name="P")]
    nodes = dw.write_capabilities(caps, TENANT) + dw.write_problems(probs, TENANT)
    dist = Distillate(paper_id=PAPER, chunk_ids=[], capabilities=caps, problems=probs)

    edges = _linker().link(nodes, dist, tenant_id=TENANT, paper_id=PAPER)
    assert edges
    for e in edges:
        assert e.extraction_confidence is not None
        assert 0.0 <= e.extraction_confidence <= 1.0
