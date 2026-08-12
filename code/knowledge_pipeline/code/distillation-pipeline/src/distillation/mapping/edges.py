"""EdgeLinker — builds cross-entity edges from a synthesized ``Distillate``.

The three writers emit the *structural* per-node edges at build time
(``MAKES_CLAIM``, ``ASSUMES``, ``AUTHORED_BY``). This module adds the remaining
ontology edges, which depend on the relationships the extraction surfaced
(reference fields on the mentions) or on within-document structure:

  L1: ADDRESSES (Capability→Problem), CONCERNS (Limitation→Domain entity),
      HOLDS_UNDER (Assumption→Domain entity), PRODUCED_BY (Experiment→Technology),
      EVALUATED_ON (Experiment→Dataset), MEASURED_BY (Experiment→Metric)
  L2: ABOUT (Claim→Domain entity), SUPPORTED_BY / REFUTED_BY (Claim→Evidence)
  L3: CITES (Paper→Paper), AFFILIATED_WITH (Author→Organization),
      FUNDED_BY (Paper→FundingSource)

Endpoint ids are recomputed deterministically (:func:`domain.ids.node_id`),
which is exactly what the writers used, so no lookup table is needed for
type-specific targets. Ambiguous "Domain entity" targets are resolved through
an index of the emitted domain nodes. Every edge carries ``extraction_confidence``
(from the source mention), and any edge whose endpoints are not among the
emitted nodes is dropped, so no dangling edges reach the graph.

This module deliberately produces only *within-document* edges. Cross-document
/ corpus-level edges (APPLIES_TO, UNDERLIES, corpus SUPPORTS/CONTRADICTS) are a
separate job that reads the persisted graph — see the refactor plan.
"""

from __future__ import annotations

from ..domain.distillate import Distillate
from ..domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from ..domain.ids import canonicalize, node_id
from ..domain.ontology import EvidenceType
from .epistemic_writer import EpistemicWriter
from .provenance_writer import ProvenanceWriter

# Domain node labels that an ambiguous "Domain entity" reference may resolve to.
_DOMAIN_INDEX_TYPES = {
    GraphNodeType.TECHNOLOGY,
    GraphNodeType.PROBLEM,
    GraphNodeType.CAPABILITY,
    GraphNodeType.METRIC,
    GraphNodeType.DATASET,
}


class EdgeLinker:
    """Builds relationship + structural edges once all nodes are known."""

    def __init__(
        self,
        epistemic_writer: EpistemicWriter,
        provenance_writer: ProvenanceWriter,
    ) -> None:
        self._epi = epistemic_writer
        self._prov = provenance_writer

    def link(
        self,
        nodes: list[GraphNode],
        distillate: Distillate,
        *,
        tenant_id: str,
        paper_id: str,
    ) -> list[GraphEdge]:
        known = {n.node_id for n in nodes}
        domain_index: dict[str, str] = {}
        for n in nodes:
            if n.type in _DOMAIN_INDEX_TYPES:
                canonical = n.properties.get("canonical_name") or canonicalize(n.name)
                domain_index.setdefault(canonical, n.node_id)

        edges: list[GraphEdge] = []

        def add(src: str, tgt: str, etype: GraphEdgeType, conf: float) -> None:
            if src in known and tgt in known and src != tgt:
                edges.append(
                    GraphEdge(
                        source_node_id=src,
                        target_node_id=tgt,
                        type=etype,
                        extraction_confidence=_clamp(conf),
                    )
                )

        # --- L1 domain edges ---------------------------------------------
        for cap in distillate.capabilities:
            if cap.addresses:
                add(
                    node_id(tenant_id, GraphNodeType.CAPABILITY, cap.name),
                    node_id(tenant_id, GraphNodeType.PROBLEM, cap.addresses),
                    GraphEdgeType.ADDRESSES,
                    cap.extraction_confidence,
                )
        for lim in distillate.limitations:
            tgt = domain_index.get(canonicalize(lim.concerns)) if lim.concerns else None
            if tgt:
                add(
                    node_id(tenant_id, GraphNodeType.LIMITATION, lim.name),
                    tgt,
                    GraphEdgeType.CONCERNS,
                    lim.extraction_confidence,
                )
        for a in distillate.assumptions:
            tgt = domain_index.get(canonicalize(a.holds_under)) if a.holds_under else None
            if tgt:
                add(
                    node_id(tenant_id, GraphNodeType.ASSUMPTION, a.name),
                    tgt,
                    GraphEdgeType.HOLDS_UNDER,
                    a.extraction_confidence,
                )
        for exp in distillate.experiments:
            xid = self._epi.experiment_id(exp, paper_id, tenant_id)
            for tech in exp.technologies:
                add(
                    xid,
                    node_id(tenant_id, GraphNodeType.TECHNOLOGY, tech),
                    GraphEdgeType.PRODUCED_BY,
                    exp.extraction_confidence,
                )
            for ds in exp.datasets:
                add(
                    xid,
                    node_id(tenant_id, GraphNodeType.DATASET, ds),
                    GraphEdgeType.EVALUATED_ON,
                    exp.extraction_confidence,
                )
            for metric in exp.metrics:
                add(
                    xid,
                    node_id(tenant_id, GraphNodeType.METRIC, metric),
                    GraphEdgeType.MEASURED_BY,
                    exp.extraction_confidence,
                )

        # --- L2 epistemik edges ------------------------------------------
        claim_by_label: dict[str, str] = {}
        for claim in distillate.claims:
            cid = self._epi.claim_id(claim, paper_id, tenant_id)
            claim_by_label.setdefault(canonicalize(claim.name), cid)
            for name in claim.about:
                tgt = domain_index.get(canonicalize(name))
                if tgt:
                    add(cid, tgt, GraphEdgeType.ABOUT, claim.extraction_confidence)
            # Claim → Assumption (ASSUMES): only the assumptions this claim
            # actually rests on, matched by name to an emitted Assumption node.
            for aname in claim.assumes:
                add(
                    cid,
                    node_id(tenant_id, GraphNodeType.ASSUMPTION, aname),
                    GraphEdgeType.ASSUMES,
                    claim.extraction_confidence,
                )
        for ev in distillate.evidence:
            target_claim = (
                claim_by_label.get(canonicalize(ev.claim)) if ev.claim else None
            )
            if target_claim:
                etype = (
                    GraphEdgeType.REFUTED_BY
                    if ev.type == EvidenceType.refuting
                    else GraphEdgeType.SUPPORTED_BY
                )
                add(
                    target_claim,
                    self._epi.evidence_id(ev, paper_id, tenant_id),
                    etype,
                    ev.extraction_confidence,
                )

        # --- L3 provenance edges -----------------------------------------
        for fs in distillate.funding_sources:
            add(
                paper_id,
                node_id(tenant_id, GraphNodeType.FUNDING_SOURCE, fs.name),
                GraphEdgeType.FUNDED_BY,
                fs.extraction_confidence,
            )
        for p in distillate.papers:
            add(
                paper_id,
                node_id(tenant_id, GraphNodeType.PAPER, p.name),
                GraphEdgeType.CITES,
                p.extraction_confidence,
            )
        for author in distillate.authors:
            if author.affiliation:
                add(
                    self._prov.author_id(author, tenant_id),
                    node_id(
                        tenant_id,
                        GraphNodeType.ORGANIZATION,
                        author.affiliation.name,
                    ),
                    GraphEdgeType.AFFILIATED_WITH,
                    author.extraction_confidence,
                )

        return edges


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
