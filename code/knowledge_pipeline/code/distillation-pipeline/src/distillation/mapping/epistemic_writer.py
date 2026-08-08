"""EpistemicWriter — writes Level 2 (paper-scoped) nodes and edges.

Writes ``Claim``, ``Evidence``, ``Experiment``, ``Scope`` nodes, plus
all edges between claims and their domain anchors (Technology, Problem,
Capability, Dataset, Assumption, Limitation, Scope).

Crucial invariant: epistemik nodes are NEVER merged across papers.
Each paper creates new Claim/Evidence/Experiment/Scope nodes, linked
to persistent domain anchors via MERGE.

The old ``confirmed``/``falsified`` boolean on conclusions is replaced
by Claim polarity + Evidence.type (supporting/refuting).
"""

from __future__ import annotations

from typing import Iterable

from ..domain.distillate import (
    AssumptionMention,
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
from ..domain.ids import canonicalize, deterministic_id
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
        assumptions: Iterable[AssumptionMention] = (),
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        # Within-document heuristic: the paper's claims rest on the paper's
        # surfaced assumptions. Extraction does not map individual claims to
        # individual assumptions, so we link each claim to every assumption
        # in the same document.
        assumption_ids = [self._domain._assumption_id(a) for a in assumptions]
        for claim in entities:
            n, e = self._write_claim(claim, paper_id)
            for assumption_id in assumption_ids:
                e.append(
                    GraphEdge(
                        source_node_id=n.node_id,
                        target_node_id=assumption_id,
                        type=GraphEdgeType.ASSUMES,
                        extraction_confidence=claim.extraction_confidence,
                    )
                )
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_evidence(
        self, entities: Iterable[EvidenceMention],
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for ev in entities:
            n, e = self._write_evidence(ev)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_experiments(
        self, entities: Iterable[ExperimentMention],
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for exp in entities:
            n, e = self._write_experiment(exp)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_scopes(
        self, entities: Iterable[ScopeMention],
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for scope in entities:
            n, e = self._write_scope(scope)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    # --- claim ----------------------------------------------------------

    def _claim_id(self, mention: ClaimMention, paper_id: str) -> str:
        """Deterministic ID: sha256(paper_id|claim_text[:50])[:16]."""
        text_slice = mention.text.strip()[:50] if mention.text else ""
        return deterministic_id(paper_id, canonicalize(text_slice))

    def _write_claim(
        self, claim: ClaimMention, paper_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        node_id = self._claim_id(claim, paper_id)
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
            node_id=node_id,
            type=GraphNodeType.CLAIM,
            name=claim.name,
            properties=props,
        )
        nodes.append(node)

        # Paper → Claim: MAKES_CLAIM
        edges.append(
            GraphEdge(
                source_node_id=paper_id,
                target_node_id=node_id,
                type=GraphEdgeType.MAKES_CLAIM,
                extraction_confidence=claim.extraction_confidence,
            )
        )

        return node, edges

    # --- evidence -------------------------------------------------------

    def _evidence_id(self, mention: EvidenceMention) -> str:
        """Evidence is paper-scoped: sha256(text_hash)[:16]."""
        return deterministic_id(canonicalize(mention.name))

    def _write_evidence(
        self, evidence: EvidenceMention
    ) -> tuple[GraphNode, list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        node_id = self._evidence_id(evidence)
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
            node_id=node_id,
            type=GraphNodeType.EVIDENCE,
            name=evidence.name,
            properties=props,
        )
        nodes.append(node)

        return node, edges

    # --- experiment -----------------------------------------------------

    def _experiment_id(self, mention: ExperimentMention) -> str:
        return deterministic_id(canonicalize(mention.name))

    def _write_experiment(
        self, experiment: ExperimentMention
    ) -> tuple[GraphNode, list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        node_id = self._experiment_id(experiment)
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
            node_id=node_id,
            type=GraphNodeType.EXPERIMENT,
            name=experiment.name,
            properties=props,
        )
        nodes.append(node)

        return node, edges

    # --- scope ----------------------------------------------------------

    def _scope_id(self, mention: ScopeMention) -> str:
        return deterministic_id(canonicalize(mention.name))

    def _write_scope(
        self, scope: ScopeMention
    ) -> tuple[GraphNode, list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        node_id = self._scope_id(scope)
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
            node_id=node_id,
            type=GraphNodeType.SCOPE,
            name=scope.name,
            properties=props,
        )
        nodes.append(node)

        return node, edges
