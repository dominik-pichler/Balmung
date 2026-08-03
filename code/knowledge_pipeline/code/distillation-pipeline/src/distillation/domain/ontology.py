"""New ontology for Paper-to-Neo4j ingestion.

Defines the four-layer knowledge graph model:
  1. **Domain** — persistent, shared across papers (Technology, Problem, …)
  2. **Epistemik** — paper-scoped, reified claims and evidence (Claim, Evidence, …)
  3. **Provenanz** — paper metadata for independence analysis (Paper, Author, …)
  4. **Assessment** — NOT produced by ingestion; reserved for a separate engine.

This module is imported by both the mapping layer (writer) and the port
interface (validation). It is pure data — no I/O lives here.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ====================================================================
# Node types
# ====================================================================


class GraphNodeType(str, Enum):
    """The four-layer ontology's node labels."""

    # --- Level 1: Domain (persistent, MERGE'd) ---
    TECHNOLOGY = "Technology"
    PROBLEM = "Problem"
    CAPABILITY = "Capability"
    METRIC = "Metric"
    DATASET = "Dataset"
    ASSUMPTION = "Assumption"
    LIMITATION = "Limitation"

    # --- Level 2: Epistemik (reified, CREATE per paper) ---
    CLAIM = "Claim"
    EVIDENCE = "Evidence"
    EXPERIMENT = "Experiment"
    SCOPE = "Scope"

    # --- Level 3: Provenanz (persistent, MERGE'd) ---
    PAPER = "Paper"
    AUTHOR = "Author"
    VENUE = "Venue"
    ORGANIZATION = "Organization"
    FUNDING_SOURCE = "FundingSource"


# ====================================================================
# Edge types
# ====================================================================


class GraphEdgeType(str, Enum):
    """The ontology's edge labels.

    Only extraction-layer edges are defined here.
    Assessment-layer edges (defeats, has_credence, etc.) are NOT here.
    """

    # --- Level 1→2: Claim relationships ---
    MAKES_CLAIM = "MAKES_CLAIM"

    # --- Level 2→1: Claim → domain anchors ---
    ABOUT = "ABOUT"
    ADDRESSES = "ADDRESSES"
    CONCERNS = "CONCERNS"
    HOLDS_UNDER = "HOLDS_UNDER"

    # --- Level 2 internal: Claim ↔ Evidence ↔ Experiment ---
    SUPPORTED_BY = "SUPPORTED_BY"
    REFUTED_BY = "REFUTED_BY"
    ASSUMES = "ASSUMES"
    PRODUCED_BY = "PRODUCED_BY"
    EVALUATED_ON = "EVALUATED_ON"
    MEASURED_BY = "MEASURED_BY"
    COMPARED_TO = "COMPARED_TO"

    # --- Level 3: Provenanz ---
    CITES = "CITES"
    AUTHORED_BY = "AUTHORED_BY"
    AFFILIATED_WITH = "AFFILIATED_WITH"
    FUNDED_BY = "FUNDED_BY"


# ====================================================================
# Node schemas (property descriptors)
# ====================================================================


class GraphNode(BaseModel):
    """A node in the knowledge graph.

    ``node_id`` is deterministic so re-ingests upsert cleanly. ``properties``
    is a flat dict of primitive JSON-serializable values — Neo4j friendly.
    ``extraction_confidence`` (float 0–1) is present on ALL extraction-layer
    nodes (claims, evidence, experiments, scopes).
    """

    node_id: str
    type: GraphNodeType
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)

    @property
    def extraction_confidence(self) -> Optional[float]:
        """Convenience accessor for the epistemik confidence field."""
        raw = self.properties.get("extraction_confidence")
        if raw is not None:
            return float(raw)
        return None


class GraphEdge(BaseModel):
    """An edge in the knowledge graph.

    Properties can hold typed edge metadata (e.g. ``CITES {intent: "refutes"}``
    or ``MEASURED_BY {value: 0.85}``).

    ``extraction_confidence`` on edges is optional — only set when the
    parser has confidence in the relationship itself.
    """

    source_node_id: str
    target_node_id: str
    type: GraphEdgeType
    properties: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence: Optional[float] = None

    @property
    def edge_key(self) -> tuple[str, str, str]:
        """Tuple key suitable for dedup/upsert in any backend."""
        return (self.source_node_id, self.type.value, self.target_node_id)


# ====================================================================
# Enums for typed properties
# ====================================================================


class TechnologyType(str, Enum):
    model = "Model"
    algorithm = "Algorithm"
    architecture = "Architecture"
    system = "System"
    tool = "Tool"


class CapabilityType(str, Enum):
    functional = "functional"
    performance = "performance"
    robustness = "robustness"
    safety = "safety"


class MetricDirection(str, Enum):
    higher_better = "higher_better"
    lower_better = "lower_better"


class DatasetContaminationRisk(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    unknown = "unknown"


class AssumptionType(str, Enum):
    data = "data"
    environmental = "environmental"
    theoretical = "theoretical"


class LimitationSeverity(str, Enum):
    """How severely a limitation constrains a claim's applicability."""

    minor = "minor"
    moderate = "moderate"
    severe = "severe"
    critical = "critical"


class ClaimType(str, Enum):
    capability = "capability"
    comparative = "comparative"
    causal = "causal"
    limitation = "limitation"
    existence = "existence"


class Polarity(str, Enum):
    positive = "positive"
    negative = "negative"


class EvidenceType(str, Enum):
    supporting = "supporting"
    refuting = "refuting"


class EvidenceDirection(str, Enum):
    """Whether the evidence points positively or negatively toward the claim."""

    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class ExperimentType(str, Enum):
    formal_proof = "formal_proof"
    controlled_ablation = "controlled_ablation"
    controlled = "controlled"
    benchmark_with_baseline = "benchmark_with_baseline"
    benchmark_no_baseline = "benchmark_no_baseline"
    user_study = "user_study"
    simulation = "simulation"
    observational = "observational"
    case_study = "case_study"


class ReplicationStatus(str, Enum):
    none = "none"
    internal = "internal"
    independent = "independent"


class DataRegime(str, Enum):
    low_resource = "low_resource"
    high_resource = "high_resource"


class OrganizationType(str, Enum):
    academic = "academic"
    industry = "industry"
    gov = "gov"


class FundingType(str, Enum):
    public = "public"
    industry = "industry"
    mixed = "mixed"


class VenueTier(str, Enum):
    a_star = "A*"
    a = "A"
    b = "B"
    c = "C"
    unknown = "unknown"
