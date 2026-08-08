"""Deterministic node-ID formula (spec: sha256(tenant || type || name)[:16])."""

from distillation.domain.graph import GraphNodeType as T
from distillation.domain.ids import node_id


def test_node_id_is_16_hex_and_stable():
    a = node_id("tenant", T.TECHNOLOGY, "BERT")
    assert len(a) == 16
    assert a == node_id("tenant", T.TECHNOLOGY, "BERT")


def test_node_id_canonicalizes_name_parts():
    assert node_id("t", T.TECHNOLOGY, "  Deep   Learning ") == node_id(
        "t", T.TECHNOLOGY, "deep learning"
    )


def test_node_id_partitions_by_type_and_tenant():
    # C1: same name, different type → different node (no cross-type collision).
    assert node_id("t", T.TECHNOLOGY, "attention") != node_id("t", T.PROBLEM, "attention")
    # Different tenant → different node.
    assert node_id("t1", T.TECHNOLOGY, "attention") != node_id(
        "t2", T.TECHNOLOGY, "attention"
    )


def test_l2_ids_are_paper_scoped():
    # C2: paper_id folds into the id so L2 nodes never merge across papers.
    a = node_id("t", T.CLAIM, "some claim", paper_id="paperA")
    b = node_id("t", T.CLAIM, "some claim", paper_id="paperB")
    assert a != b
    assert a == node_id("t", T.CLAIM, "some claim", paper_id="paperA")


def test_multiple_name_parts_disambiguate():
    # Author fallback: name + affiliation.
    assert node_id("t", T.AUTHOR, "john smith", "mit") != node_id(
        "t", T.AUTHOR, "john smith", "cmu"
    )
