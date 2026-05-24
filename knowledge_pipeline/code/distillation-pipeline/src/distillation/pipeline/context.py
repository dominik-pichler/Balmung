"""Pipeline context — a small dependency-injection container.

Holds wired dependencies so the orchestrator stays declarative. Kept minimal
on purpose: anything more sophisticated belongs to a real DI framework.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ports.dead_letter_store import DeadLetterStore
from ..ports.graph_repository import GraphRepository
from .stages.distill import DistillStage
from .stages.persist import PersistStage
from .stages.preprocess import PreprocessStage
from .stages.synthesize import SynthesizeStage


@dataclass(slots=True)
class PipelineContext:
    """All collaborators the orchestrator needs.

    Constructed once at CLI startup, passed by reference into the pipeline.
    """

    preprocess: PreprocessStage
    distill: DistillStage
    synthesize: SynthesizeStage
    persist: PersistStage
    graph_repository: GraphRepository
    dead_letter: DeadLetterStore
