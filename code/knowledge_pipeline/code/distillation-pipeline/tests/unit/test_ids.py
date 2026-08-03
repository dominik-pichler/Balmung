from distillation.domain.ids import canonicalize, content_hash, deterministic_id


def test_canonicalize_normalizes_case_whitespace_and_unicode():
    assert canonicalize("  Machine   Learning ") == "machine learning"
    assert canonicalize("Café") == canonicalize("Cafe\u0301")  # NFKC


def test_deterministic_id_is_stable():
    a = deterministic_id("tenant", "Topic", "machine learning")
    b = deterministic_id("tenant", "Topic", "machine learning")
    assert a == b
    assert len(a) == 16


def test_deterministic_id_changes_with_parts():
    a = deterministic_id("tenant", "Topic", "machine learning")
    b = deterministic_id("tenant", "Topic", "deep learning")
    assert a != b


def test_content_hash_accepts_str_or_bytes():
    assert content_hash("hello") == content_hash(b"hello")
    assert len(content_hash("hello")) == 64
