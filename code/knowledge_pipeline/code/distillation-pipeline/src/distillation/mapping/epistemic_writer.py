"""EpistemicWriter — writes Level 2 (paper-scoped) nodes and edges.

Writes ``Claim``, ``Evidence``, ``Experiment``, ``Scope`` nodes, plus edges
between claims and their domain anchors.

Crucial invariant: epistemik nodes are NEVER merged across papers. Their
``node_id`` folds in the anchoring ``paper_id`` (via
:func:`distillation.domain.ids.node_id`), so two papers that surface an
identically-named claim/evidence get distinct nodes. Each paper creates fresh
Claim/Evidence/Experiment/Scope nodes, linked to persistent domain anchors.

The old ``confirmed``/``falsified`` boolean on conclusions is replaced by
Claim polarity + Evidence.type (supporting/refuting).
"""

from __future__ import annotations

from collections.abc import Iterable

from ..domain.distillate import (
    ClaimMention,
    EvidenceMention,
    ExperimentMention,
    ScopeMention,
)
from ..domain.graph import (
    GraphEdge,
    GraphEdgeType,
    GraphNode,
    GraphNodeType,
)
from ..domain.ids import node_id
from .domain_writer import DomainWriter


class EpistemicWriter:
    """Produces paper-scoped (CREATE) epistemik nodes and edges."""

    def __init__(self, domain_writer: DomainWriter) -> None:
        self._domain = domain_writer

    # --- public API -----------------------------------------------------

    def write_claims(
        self,
        entities: Iterable[ClaimMention],
        paper_id: str,
        tenant_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        # Only the structural Paper→Claim (MAKES_CLAIM) edge is emitted here.
        # Claim→Assumption (ASSUMES) is a reference-driven edge built by the
        # EdgeLinker from each claim's ``assumes`` field, so a claim links only
        # to the assumptions it actually rests on (not every assumption in the
        # paper — that was a cross-product bug).
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for claim in entities:
            n, e = self._write_claim(claim, paper_id, tenant_id)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_evidence(
        self,
        entities: Iterable[EvidenceMention],
        paper_id: str,
        tenant_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for ev in entities:
            n, e = self._write_evidence(ev, paper_id, tenant_id)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_experiments(
        self,
        entities: Iterable[ExperimentMention],
        paper_id: str,
        tenant_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for exp in entities:
            n, e = self._write_experiment(exp, paper_id, tenant_id)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_scopes(
        self,
        entities: Iterable[ScopeMention],
        paper_id: str,
        tenant_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for scope in entities:
            n, e = self._write_scope(scope, paper_id, tenant_id)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    # --- claim ----------------------------------------------------------

    def claim_id(self, mention: ClaimMention, paper_id: str, tenant_id: str) -> str:
        """Paper-scoped id: sha256(tenant || Claim || paper_id || text[:50])[:16]."""
        text_slice = mention.text.strip()[:50] if mention.text else ""
        return node_id(
            tenant_id, GraphNodeType.CLAIM, text_slice, paper_id=paper_id
        )

    def _write_claim(
        self, claim: ClaimMention, paper_id: str, tenant_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        edges: list[GraphEdge] = []
        cid = self.claim_id(claim, paper_id, tenant_id)

        props: dict = {
            "text": claim.text,
            "extraction_confidence": claim.extraction_confidence,
        }
        if claim.claim_type is not None:
            props["claim_type"] = claim.claim_type.value
        if claim.polarity is not None:
            props["polarity"] = claim.polarity.value
        if claim.stated_confidence is not None:
            props["stated_confidence"] = claim.stated_confidence
        if claim.prior_implausibility is not None:
            props["prior_implausibility"] = claim.prior_implausibility
        props["decay_immune"] = claim.decay_immune

        node = GraphNode(
            node_id=cid,
            type=GraphNodeType.CLAIM,
            name=claim.name,
            properties=props,
        )

        # Paper → Claim: MAKES_CLAIM
        edges.append(
            GraphEdge(
                source_node_id=paper_id,
                target_node_id=cid,
                type=GraphEdgeType.MAKES_CLAIM,
                extraction_confidence=claim.extraction_confidence,
            )
        )
        return node, edges

    # --- evidence -------------------------------------------------------

    def evidence_id(
        self, mention: EvidenceMention, paper_id: str, tenant_id: str
    ) -> str:
        return node_id(
            tenant_id, GraphNodeType.EVIDENCE, mention.name, paper_id=paper_id
        )

    def _write_evidence(
        self, evidence: EvidenceMention, paper_id: str, tenant_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        props: dict = {
            "extraction_confidence": evidence.extraction_confidence,
        }
        if evidence.type is not None:
            props["type"] = evidence.type.value
        if evidence.effect_size is not None:
            props["effect_size"] = evidence.effect_size
        if evidence.significance is not None:
            props["significance"] = evidence.significance
        if evidence.direction is not None:
            props["direction"] = evidence.direction.value

        node = GraphNode(
            node_id=self.evidence_id(evidence, paper_id, tenant_id),
            type=GraphNodeType.EVIDENCE,
            name=evidence.name,
            properties=props,
        )
        return node, []

    # --- experiment -----------------------------------------------------

    def experiment_id(
        self, mention: ExperimentMention, paper_id: str, tenant_id: str
    ) -> str:
        return node_id(
            tenant_id, GraphNodeType.EXPERIMENT, mention.name, paper_id=paper_id
        )

    def _write_experiment(
        self, experiment: ExperimentMention, paper_id: str, tenant_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        props: dict = {
            "extraction_confidence": experiment.extraction_confidence,
        }
        if experiment.experiment_type is not None:
            props["experiment_type"] = experiment.experiment_type.value
        if experiment.sample_size is not None:
            props["sample_size"] = experiment.sample_size
        if experiment.has_baseline is not None:
            props["has_baseline"] = experiment.has_baseline
        if experiment.replication_status is not None:
            props["replication_status"] = experiment.replication_status.value
        if experiment.leakage_risk is not None:
            props["leakage_risk"] = experiment.leakage_risk.value
        props["preregistered"] = experiment.preregistered

        node = GraphNode(
            node_id=self.experiment_id(experiment, paper_id, tenant_id),
            type=GraphNodeType.EXPERIMENT,
            name=experiment.name,
            properties=props,
        )
        return node, []

    # --- scope ----------------------------------------------------------

    def _scope_id(self, mention: ScopeMention, paper_id: str, tenant_id: str) -> str:
        return node_id(
            tenant_id, GraphNodeType.SCOPE, mention.name, paper_id=paper_id
        )

    def _write_scope(
        self, scope: ScopeMention, paper_id: str, tenant_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        props: dict = {
            "extraction_confidence": scope.extraction_confidence,
        }
        if scope.data_domain is not None:
            props["data_domain"] = scope.data_domain
        if scope.language is not None:
            props["language"] = scope.language
        if scope.scale is not None:
            props["scale"] = scope.scale
        if scope.data_regime is not None:
            props["data_regime"] = scope.data_regime.value
        if scope.hardware is not None:
            props["hardware"] = scope.hardware
        if scope.time_window is not None:
            props["time_window"] = scope.time_window

        node = GraphNode(
            node_id=self._scope_id(scope, paper_id, tenant_id),
            type=GraphNodeType.SCOPE,
            name=scope.name,
            properties=props,
        )
        return node, []
