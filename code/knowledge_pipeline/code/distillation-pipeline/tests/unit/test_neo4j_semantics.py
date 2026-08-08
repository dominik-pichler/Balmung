"""Neo4j write semantics via a fake async driver (no live database).

Verifies the ontology's MERGE/CREATE contract at the Cypher level:
  * L1 domain + L3 provenance nodes MERGE on ``id`` (persistent, cross-paper).
  * L2 epistemik nodes MERGE on their *paper-scoped* ``id`` (C3): re-ingesting
    the same paper is idempotent, yet nodes never merge across papers because
    the id differs per paper.
"""

from typing import Self

from distillation.adapters.graph.neo4j import Neo4jGraphRepository
from distillation.domain.graph import GraphNode, GraphNodeType


class _FakeResult:
    async def single(self):
        return None

    def __aiter__(self):
        async def _gen():
            for _ in ():
                yield None

        return _gen()


class _FakeSession:
    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def run(self, query: str, **_: object) -> _FakeResult:
        self._log.append(query)
        return _FakeResult()


class _FakeDriver:
    def __init__(self) -> None:
        self.log: list[str] = []

    def session(self, database: str | None = None) -> _FakeSession:
        return _FakeSession(self.log)

    async def close(self) -> None:
        return None


def _repo_with_fake_driver() -> tuple[Neo4jGraphRepository, _FakeDriver]:
    repo = Neo4jGraphRepository.__new__(Neo4jGraphRepository)
    driver = _FakeDriver()
    repo._driver = driver  # type: ignore[attr-defined]
    repo._database = "neo4j"  # type: ignore[attr-defined]
    repo._constraints_checked = True  # skip constraint provisioning noise  # type: ignore[attr-defined]
    return repo, driver


async def test_domain_nodes_use_merge():
    repo, driver = _repo_with_fake_driver()
    await repo.upsert_domain_nodes(
        [GraphNode(node_id="x", type=GraphNodeType.TECHNOLOGY, name="BERT")]
    )
    writes = [q for q in driver.log if ":Technology" in q]
    assert writes and all("MERGE" in q for q in writes)


async def test_l2_nodes_use_merge_not_create():
    """C3: L2 must MERGE on the paper-scoped id, never CREATE (idempotent)."""
    repo, driver = _repo_with_fake_driver()
    claim = GraphNode(node_id="c1", type=GraphNodeType.CLAIM, name="A claim")
    await repo.create_epistemic_nodes([claim])
    writes = [q for q in driver.log if ":Claim" in q]
    assert writes
    assert all("MERGE" in q for q in writes)
    assert not any(q.strip().startswith("CREATE") for q in writes)


async def test_l2_reingest_is_idempotent_cypher():
    """Re-writing the same L2 node issues the same MERGE (a no-op in Neo4j)."""
    repo, driver = _repo_with_fake_driver()
    claim = GraphNode(node_id="c1", type=GraphNodeType.CLAIM, name="A claim")
    await repo.create_epistemic_nodes([claim])
    await repo.create_epistemic_nodes([claim])
    claim_writes = [q for q in driver.log if ":Claim" in q]
    assert len(claim_writes) == 2
    assert claim_writes[0] == claim_writes[1]
    assert "MERGE" in claim_writes[0]
