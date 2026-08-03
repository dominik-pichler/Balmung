"""DomainWriter — writes Level 1 (persistent) nodes to the graph.

Writes ``Technology``, ``Problem``, ``Capability``, ``Metric``,
``Dataset``, ``Assumption``, ``Limitation`` via MERGE on ``node_id``.

These nodes are persistent across papers: same ``name`` (canonicalized)
→ same ``node_id`` → MERGE ON MATCH ON CREATE.
"""

from __future__ import annotations

from typing import Iterable

from ..domain.distillate import (
    AssumptionMention,
    CapabilityMention,
    DatasetMention,
    LimitationMention,
    MetricMention,
    ProblemMention,
    TechnologyMention,
)
from ..domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from ..domain.ids import canonicalize, deterministic_id


class DomainWriter:
    """Produces persistent (MERGE'd) domain nodes."""

    def __init__(self) -> None:
        # Technology aliases lookup for dedup
        self._tech_canonical: dict[str, GraphNode] = {}

    # --- public API -----------------------------------------------------

    def write_technologies(
        self, entities: Iterable[TechnologyMention]
    ) -> list[GraphNode]:
        return [self._write_technology(e) for e in entities]

    def write_problems(
        self, entities: Iterable[ProblemMention]
    ) -> list[GraphNode]:
        return [self._write_problem(e) for e in entities]

    def write_capabilities(
        self, entities: Iterable[CapabilityMention]
    ) -> list[GraphNode]:
        return [self._write_capability(e) for e in entities]

    def write_metrics(
        self, entities: Iterable[MetricMention]
    ) -> list[GraphNode]:
        return [self._write_metric(e) for e in entities]

    def write_datasets(
        self, entities: Iterable[DatasetMention]
    ) -> list[GraphNode]:
        return [self._write_dataset(e) for e in entities]

    def write_assumptions(
        self, entities: Iterable[AssumptionMention]
    ) -> list[GraphNode]:
        return [self._write_assumption(e) for e in entities]

    def write_limitations(
        self, entities: Iterable[LimitationMention]
    ) -> list[GraphNode]:
        return [self._write_limitation(e) for e in entities]

    # --- internal builders ----------------------------------------------

    def _tech_id(self, mention: TechnologyMention) -> str:
        """Deterministic ID for Technology: sha256(canonical_name)[:16]."""
        return deterministic_id(canonicalize(mention.name))

    def _write_technology(self, m: TechnologyMention) -> GraphNode:
        node_id = self._tech_id(m)

        # Collect aliases from the mention + canonical name
        aliases = list(dict.fromkeys(
            [canonicalize(m.name)] +
            [canonicalize(a) for a in m.aliases if a]
        ))

        props: dict = {
            "canonical_name": canonicalize(m.name),
            "extraction_confidence": m.extraction_confidence,
        }
        if m.type is not None:
            props["type"] = m.type.value
        if m.first_described_in is not None:
            props["first_described_in"] = m.first_described_in
        if m.aliases:
            props["aliases"] = aliases

        node = GraphNode(
            node_id=node_id,
            type=GraphNodeType.TECHNOLOGY,
            name=m.name,
            properties=props,
        )
        self._tech_canonical[node_id] = node
        return node

    def _problem_id(self, mention: ProblemMention) -> str:
        return deterministic_id(canonicalize(mention.name))

    def _write_problem(self, m: ProblemMention) -> GraphNode:
        props: dict = {
            "canonical_name": canonicalize(m.name),
            "extraction_confidence": m.extraction_confidence,
        }
        if m.domain is not None:
            props["domain"] = m.domain
        return GraphNode(
            node_id=self._problem_id(m),
            type=GraphNodeType.PROBLEM,
            name=m.name,
            properties=props,
        )

    def _capability_id(self, m: CapabilityMention) -> str:
        return deterministic_id(canonicalize(m.name))

    def _write_capability(self, m: CapabilityMention) -> GraphNode:
        props: dict = {
            "canonical_name": canonicalize(m.name),
            "description": m.description,
            "extraction_confidence": m.extraction_confidence,
        }
        if m.capability_type is not None:
            props["capability_type"] = m.capability_type.value
        return GraphNode(
            node_id=self._capability_id(m),
            type=GraphNodeType.CAPABILITY,
            name=m.name,
            properties=props,
        )

    def _metric_id(self, m: MetricMention) -> str:
        return deterministic_id(canonicalize(m.name))

    def _write_metric(self, m: MetricMention) -> GraphNode:
        props: dict = {
            "canonical_name": canonicalize(m.name),
            "extraction_confidence": m.extraction_confidence,
        }
        if m.unit is not None:
            props["unit"] = m.unit
        if m.direction is not None:
            props["direction"] = m.direction.value
        return GraphNode(
            node_id=self._metric_id(m),
            type=GraphNodeType.METRIC,
            name=m.name,
            properties=props,
        )

    def _dataset_id(self, m: DatasetMention) -> str:
        return deterministic_id(canonicalize(m.name))

    def _write_dataset(self, m: DatasetMention) -> GraphNode:
        props: dict = {
            "canonical_name": canonicalize(m.name),
            "extraction_confidence": m.extraction_confidence,
        }
        if m.domain is not None:
            props["domain"] = m.domain
        if m.size is not None:
            props["size"] = m.size
        if m.contamination_risk is not None:
            props["contamination_risk"] = m.contamination_risk.value
        return GraphNode(
            node_id=self._dataset_id(m),
            type=GraphNodeType.DATASET,
            name=m.name,
            properties=props,
        )

    def _assumption_id(self, m: AssumptionMention) -> str:
        return deterministic_id(canonicalize(m.name))

    def _write_assumption(self, m: AssumptionMention) -> GraphNode:
        props: dict = {
            "statement": m.statement,
            "extraction_confidence": m.extraction_confidence,
        }
        if m.assumption_type is not None:
            props["type"] = m.assumption_type.value
        return GraphNode(
            node_id=self._assumption_id(m),
            type=GraphNodeType.ASSUMPTION,
            name=m.name,
            properties=props,
        )

    def _limitation_id(self, m: LimitationMention) -> str:
        return deterministic_id(canonicalize(m.name))

    def _write_limitation(self, m: LimitationMention) -> GraphNode:
        props: dict = {
            "statement": m.statement,
            "extraction_confidence": m.extraction_confidence,
        }
        if m.severity is not None:
            props["severity"] = m.severity.value
        return GraphNode(
            node_id=self._limitation_id(m),
            type=GraphNodeType.LIMITATION,
            name=m.name,
            properties=props,
        )
