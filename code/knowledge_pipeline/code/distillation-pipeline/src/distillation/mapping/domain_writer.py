"""DomainWriter — writes Level 1 (persistent) nodes to the graph.

Writes ``Technology``, ``Problem``, ``Capability``, ``Metric``,
``Dataset``, ``Assumption``, ``Limitation`` via MERGE on ``node_id``.

These nodes are persistent across papers: same canonical name (for a given
tenant + node type) → same ``node_id`` → MERGE ON MATCH ON CREATE. Node ids
follow the ontology formula ``sha256(tenant || type || canonical_name)[:16]``
(see :func:`distillation.domain.ids.node_id`); they deliberately omit the
paper id so the same entity merges across papers.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..domain.distillate import (
    AssumptionMention,
    CapabilityMention,
    DatasetMention,
    LimitationMention,
    MetricMention,
    ProblemMention,
    TechnologyMention,
)
from ..domain.graph import GraphNode, GraphNodeType
from ..domain.ids import canonicalize, node_id


class DomainWriter:
    """Produces persistent (MERGE'd) domain nodes."""

    # --- public API -----------------------------------------------------

    def write_technologies(
        self, entities: Iterable[TechnologyMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_technology(e, tenant_id) for e in entities]

    def write_problems(
        self, entities: Iterable[ProblemMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_problem(e, tenant_id) for e in entities]

    def write_capabilities(
        self, entities: Iterable[CapabilityMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_capability(e, tenant_id) for e in entities]

    def write_metrics(
        self, entities: Iterable[MetricMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_metric(e, tenant_id) for e in entities]

    def write_datasets(
        self, entities: Iterable[DatasetMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_dataset(e, tenant_id) for e in entities]

    def write_assumptions(
        self, entities: Iterable[AssumptionMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_assumption(e, tenant_id) for e in entities]

    def write_limitations(
        self, entities: Iterable[LimitationMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_limitation(e, tenant_id) for e in entities]

    # --- id helpers -----------------------------------------------------

    def assumption_id(self, m: AssumptionMention, tenant_id: str) -> str:
        """Public: EpistemicWriter needs this to link claims → assumptions."""
        return node_id(tenant_id, GraphNodeType.ASSUMPTION, m.name)

    # --- internal builders ----------------------------------------------

    def _write_technology(self, m: TechnologyMention, tenant_id: str) -> GraphNode:
        # Collect aliases from the mention + canonical name.
        aliases = list(
            dict.fromkeys(
                [canonicalize(m.name)] + [canonicalize(a) for a in m.aliases if a]
            )
        )
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
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.TECHNOLOGY, m.name),
            type=GraphNodeType.TECHNOLOGY,
            name=m.name,
            properties=props,
        )

    def _write_problem(self, m: ProblemMention, tenant_id: str) -> GraphNode:
        props: dict = {
            "canonical_name": canonicalize(m.name),
            "extraction_confidence": m.extraction_confidence,
        }
        if m.domain is not None:
            props["domain"] = m.domain
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.PROBLEM, m.name),
            type=GraphNodeType.PROBLEM,
            name=m.name,
            properties=props,
        )

    def _write_capability(self, m: CapabilityMention, tenant_id: str) -> GraphNode:
        props: dict = {
            "canonical_name": canonicalize(m.name),
            "description": m.description,
            "extraction_confidence": m.extraction_confidence,
        }
        if m.capability_type is not None:
            props["capability_type"] = m.capability_type.value
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.CAPABILITY, m.name),
            type=GraphNodeType.CAPABILITY,
            name=m.name,
            properties=props,
        )

    def _write_metric(self, m: MetricMention, tenant_id: str) -> GraphNode:
        props: dict = {
            "canonical_name": canonicalize(m.name),
            "extraction_confidence": m.extraction_confidence,
        }
        if m.unit is not None:
            props["unit"] = m.unit
        if m.direction is not None:
            props["direction"] = m.direction.value
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.METRIC, m.name),
            type=GraphNodeType.METRIC,
            name=m.name,
            properties=props,
        )

    def _write_dataset(self, m: DatasetMention, tenant_id: str) -> GraphNode:
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
            node_id=node_id(tenant_id, GraphNodeType.DATASET, m.name),
            type=GraphNodeType.DATASET,
            name=m.name,
            properties=props,
        )

    def _write_assumption(self, m: AssumptionMention, tenant_id: str) -> GraphNode:
        props: dict = {
            "statement": m.statement,
            "extraction_confidence": m.extraction_confidence,
        }
        if m.assumption_type is not None:
            props["type"] = m.assumption_type.value
        return GraphNode(
            node_id=self.assumption_id(m, tenant_id),
            type=GraphNodeType.ASSUMPTION,
            name=m.name,
            properties=props,
        )

    def _write_limitation(self, m: LimitationMention, tenant_id: str) -> GraphNode:
        props: dict = {
            "statement": m.statement,
            "extraction_confidence": m.extraction_confidence,
        }
        if m.severity is not None:
            props["severity"] = m.severity.value
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.LIMITATION, m.name),
            type=GraphNodeType.LIMITATION,
            name=m.name,
            properties=props,
        )
