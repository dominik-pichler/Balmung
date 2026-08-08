"""Pipeline stage protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

TIn_contra = TypeVar("TIn_contra", contravariant=True)
TOut_co = TypeVar("TOut_co", covariant=True)


class Stage(Protocol[TIn_contra, TOut_co]):
    """A pipeline stage transforms one typed input into one typed output.

    Stages are pure async callables so they compose with ``asyncio.gather``
    where parallelism is wanted (the distill stage uses this internally).
    """

    async def run(self, value: TIn_contra, /) -> TOut_co: ...
