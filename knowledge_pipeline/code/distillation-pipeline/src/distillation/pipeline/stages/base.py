"""Pipeline stage protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

TIn = TypeVar("TIn", contravariant=True)
TOut = TypeVar("TOut", covariant=True)


class Stage(Protocol[TIn, TOut]):
    """A pipeline stage transforms one typed input into one typed output.

    Stages are pure async callables so they compose with ``asyncio.gather``
    where parallelism is wanted (the distill stage uses this internally).
    """

    async def run(self, value: TIn, /) -> TOut: ...
