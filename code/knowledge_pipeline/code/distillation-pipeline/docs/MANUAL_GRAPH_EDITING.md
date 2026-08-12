# Manual Graph Editing — Patching the Knowledge Graph by Hand

> When the LLM under-extracts (misses an edge, drops a node, splits a duplicate,
> or leaves a reference field blank), you can patch the Neo4j graph directly.
> This manual shows how to do that **without breaking re-ingest idempotency**.

**Audience:** anyone fixing a graph produced by `distill ingest`.
**Backend assumed:** Neo4j (Browser at <http://localhost:7474>, or `cypher-shell`).
**Login used in these examples:** `neo4j` / `admin123` (from `.env`).

---

## 0. The one thing you must understand first

Every node is stored as:

```
(:Label { id: "<16-hex-hash>", name: "...", canonical_name: "...", extraction_confidence: 0.87, ... })
```

- **`Label`** is the ontology type (`Technology`, `Claim`, `Paper`, …).
- **`id`** is a **deterministic hash**. It is the MERGE key. Edges are matched by
  it (`MATCH (s {id: ...})`). **This is the single value you must get right.**
- The pipeline recomputes that same `id` on every ingest. So:
  - If you add a node with the **correct** `id`, re-ingesting the same paper
    updates it in place (no duplicate). ✅
  - If you add a node with a **made-up** `id`, the next ingest will create a
    *second* node for the same entity. ❌

### The id formula (from `domain/ids.py`)

```
id = sha256( tenant_id | node_type | [paper_id] | canonical(name) )[:16]
```

- Parts joined by `|`.
- `tenant_id` and `node_type` are used **verbatim**. Default tenant is `default`
  (unless you set `DISTILL_TENANT_ID`). `node_type` is the **label string**
  exactly: `Technology`, `Problem`, `Capability`, `Metric`, `Dataset`,
  `Assumption`, `Limitation`, `Claim`, `Evidence`, `Experiment`, `Scope`,
  `Paper`, `Author`, `Organization`, `Venue`, `FundingSource`.
- `paper_id` is included **only for Level-2 nodes** (Claim, Evidence, Experiment,
  Scope) — those are paper-scoped. Omit it for everything else.
- `name` is canonicalized: NFKC → lowercase → trim → collapse internal whitespace.

**Do not compute this hash by hand.** Use the project's own function so it's
guaranteed identical to what ingestion produces:

```bash
# from the distillation-pipeline dir, with .venv active
python -c "from distillation.domain.ids import node_id; from distillation.domain.ontology import GraphNodeType as T; print(node_id('default', T.TECHNOLOGY, 'transformer'))"
# -> e.g. 9f2c1a...   (paste this as the node's id)

# Level-2 (paper-scoped) needs the paper's document_id:
python -c "from distillation.domain.ids import node_id; from distillation.domain.ontology import GraphNodeType as T; print(node_id('default', T.CLAIM, 'gpt-4 outperforms gpt-3.5', paper_id='662ddf11862045a7'))"
```

> **Golden rule:** *Editing edges is safe and easy — you just match existing
> nodes and add a relationship. Creating nodes is the risky part — always give
> them a computed `id`.* Most LLM misses are missing **edges**, so you'll rarely
> need to create nodes.

### Property-naming gotcha

The writers stamp **node** properties in `snake_case`:
`canonical_name`, `extraction_confidence`, `capability_type`, `contamination_risk`,
`statement`, `severity`, `type`, `domain`, `unit`, `direction`, `aliases`, …

But **edges** store confidence as **`extractionConfidence`** (camelCase).
(The index names in `schema/neo4j_constraints.cypher` use camelCase like
`claimType`/`peerReviewed` — those don't match the real snake_case node props;
ignore them when hand-editing and use the names above.)

### ⚠️ There is NO `name` property on Neo4j nodes (known adapter gap)

The Neo4j adapter writes only `id` + the `properties` dict, and `GraphNode.name`
is **not** part of that dict — so **no node carries a `name`**. Match on these
instead:

| Node group | Match on | Example |
|---|---|---|
| L1 Domain (Technology, Problem, Capability, Metric, Dataset, Limitation) | `canonical_name` (lowercased) | `{canonical_name: 'sparseformer'}` |
| Assumption | `canonical_name` if present, else `statement` | |
| **Claim** | `text` (Claims have no `canonical_name`) | `WHERE toLower(c.text) CONTAINS 'outperforms'` |
| Evidence / Experiment / Scope | check `keys(n)` first — usually `canonical_name` or `text` | |
| Paper | `source_id` / `uri` / `title` | |

So in the Browser, set node captions to `canonical_name` (or `text` for Claims)
or they'll render blank. When in doubt: `MATCH (n {id:'…'}) RETURN keys(n);`
This blank-`name` behavior also degrades `distill export`/`chat` retrieval on the
Neo4j backend — see the "known issues" note from the maintainer.

---

## 1. Read before you write — find the nodes you're patching

```cypher
// What labels/counts exist
MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS n ORDER BY n DESC;

// Find a domain/provenance node by canonical_name and see its id + props
MATCH (n) WHERE n.canonical_name CONTAINS 'sparseformer'
RETURN labels(n)[0] AS label, n.id AS id, properties(n) AS props;

// Find a Claim by its text (Claims have no canonical_name)
MATCH (c:Claim) WHERE toLower(c.text) CONTAINS 'outperforms'
RETURN c.id AS id, c.text AS text, c.polarity AS polarity;

// See everything attached to a node
MATCH (n {id: $id})-[r]-(m) RETURN n, r, m;
```

---

## 2. The most common fix: add a missing edge between two existing nodes

The LLM extracted both nodes but left the reference field blank, so no edge was
built. You don't need any hash here — just match both nodes and `MERGE` the
relationship. **Always set `extractionConfidence`** (the ontology requires every
edge to carry it; use `1.0` for a human-verified edge).

**Edge direction reference** (source → target):

| Edge | From → To | Layer |
|---|---|---|
| `MAKES_CLAIM` | Paper → Claim | L1→L2 |
| `ABOUT` | Claim → Technology/Problem/Capability/Metric/Dataset | L2→L1 |
| `ADDRESSES` | Capability → Problem | L1 |
| `CONCERNS` | Limitation → domain entity | L1 |
| `HOLDS_UNDER` | Assumption → domain entity | L1 |
| `ASSUMES` | Claim → Assumption | L2 |
| `SUPPORTED_BY` | Claim → Evidence | L2 |
| `REFUTED_BY` | Claim → Evidence | L2 |
| `PRODUCED_BY` | Experiment → Technology | L2→L1 |
| `EVALUATED_ON` | Experiment → Dataset | L2→L1 |
| `MEASURED_BY` | Experiment → Metric | L2→L1 |
| `AUTHORED_BY` | Paper → Author | L3 |
| `AFFILIATED_WITH` | Author → Organization | L3 |
| `CITES` | Paper → Paper | L3 |
| `FUNDED_BY` | Paper → FundingSource | L3 |

### Recipe: Claim `ABOUT` Technology (the case you hit)

```cypher
MATCH (c:Claim)      WHERE toLower(c.name) CONTAINS 'outperforms'
MATCH (t:Technology) WHERE t.canonical_name = 'gpt-4'
MERGE (c)-[r:ABOUT]->(t)
SET r.extractionConfidence = 1.0;
```

### Recipe: Capability `ADDRESSES` Problem

```cypher
MATCH (cap:Capability) WHERE cap.canonical_name = 'classification_accuracy'
MATCH (p:Problem)      WHERE p.canonical_name   = 'achieving_state_of_the_art_performance'
MERGE (cap)-[r:ADDRESSES]->(p)
SET r.extractionConfidence = 1.0;
```

### Recipe: Experiment → Technology / Dataset / Metric

```cypher
MATCH (e:Experiment) WHERE toLower(e.name) CONTAINS 'benchmark'
MATCH (t:Technology) WHERE t.canonical_name = 'gpt-4'
MERGE (e)-[:PRODUCED_BY {extractionConfidence: 1.0}]->(t);

MATCH (e:Experiment) WHERE toLower(e.name) CONTAINS 'benchmark'
MATCH (d:Dataset)    WHERE d.canonical_name = 'imdb'
MERGE (e)-[:EVALUATED_ON {extractionConfidence: 1.0}]->(d);

MATCH (e:Experiment) WHERE toLower(e.name) CONTAINS 'benchmark'
MATCH (m:Metric)     WHERE m.canonical_name = 'accuracy'
MERGE (e)-[:MEASURED_BY {extractionConfidence: 1.0}]->(m);
```

### Recipe: link Evidence to its Claim

```cypher
// supporting evidence
MATCH (c:Claim)    WHERE toLower(c.name) CONTAINS 'outperforms'
MATCH (ev:Evidence) WHERE toLower(ev.name) CONTAINS 'benchmark result'
MERGE (c)-[:SUPPORTED_BY {extractionConfidence: 1.0}]->(ev);
// use REFUTED_BY instead when the evidence contradicts the claim
```

> **Why `MERGE` and not `CREATE`?** `MERGE` on the relationship is idempotent —
> running the patch twice won't duplicate the edge. It also mirrors how the
> pipeline writes edges.

---

## 3. Fix or fill a node's properties

The node exists but a field is wrong/empty (e.g. a Claim missing its polarity).
Just `SET` it. Use the **snake_case** node property names.

```cypher
MATCH (c:Claim) WHERE toLower(c.name) CONTAINS 'few-shot'
SET c.polarity = 'positive',
    c.claim_type = 'causal',
    c.stated_confidence = 0.7;

// Fix a canonical_name typo (see §5 before doing this — it affects the id!)
MATCH (t:Technology {id: 'abc123...'}) SET t.name = 'GPT-4';
```

---

## 4. Add a node the LLM missed entirely

Rarer, and the one place you must supply a correct `id`. Compute it with the
helper from §0, then:

### Level 1 / Level 3 node (persistent — no paper_id)

```bash
python -c "from distillation.domain.ids import node_id; from distillation.domain.ontology import GraphNodeType as T; print(node_id('default', T.METRIC, 'f1 score'))"
# -> 3d9e77aa1b2c4f80  (example)
```

```cypher
MERGE (m:Metric {id: '3d9e77aa1b2c4f80'})
SET m.name = 'F1 score',
    m.canonical_name = 'f1 score',
    m.direction = 'higher_better',
    m.unit = '0-1',
    m.extraction_confidence = 1.0;
```

### Level 2 node (paper-scoped — MUST include the paper's document_id)

```bash
python -c "from distillation.domain.ids import node_id; from distillation.domain.ontology import GraphNodeType as T; print(node_id('default', T.EVIDENCE, 'ablation result', paper_id='662ddf11862045a7'))"
```

```cypher
MERGE (ev:Evidence {id: '<computed>'})
SET ev.name = 'ablation result',
    ev.canonical_name = 'ablation result',
    ev.type = 'supporting',
    ev.direction = 'positive',
    ev.extraction_confidence = 1.0;
```

Then wire it up with the edge recipes in §2.

> Find a paper's `document_id`: `MATCH (p:Paper) RETURN p.id, p.name;` — it's the
> `id` on the ingested `Paper` node (also printed by `distill ingest`).

---

## 5. Merge duplicates (LLM split one entity into two)

E.g. it emitted both `Transformer` and `transformers` as separate Technologies.
Canonicalization *should* collapse these, but near-misses ("Transformer model"
vs "transformer") slip through. Fold the stray into the canonical one and move
its edges over. Requires the **APOC** plugin:

```cypher
MATCH (keep:Technology   {canonical_name: 'transformer'})
MATCH (dupe:Technology)   WHERE toLower(dupe.name) = 'transformer model'
CALL apoc.refactor.mergeNodes([keep, dupe], {properties: 'discard', mergeRels: true})
YIELD node
RETURN node;
```

No APOC? Move edges manually, then delete the dupe:

```cypher
MATCH (dupe:Technology {name: 'Transformer model'})-[r]-(x)
MATCH (keep:Technology {canonical_name: 'transformer'})
// recreate each rel on keep (repeat per direction/type as needed), then:
DETACH DELETE dupe;
```

> After merging, the surviving node keeps **its own** `id`. If that `id` doesn't
> match the canonical formula, a future ingest may re-split it. For a permanent
> fix, prefer improving the source text / extraction so both mentions
> canonicalize identically.

---

## 6. Delete a wrong node or edge

```cypher
// one wrong edge
MATCH (:Claim)-[r:ABOUT]->(:Technology {name: 'Bogus'}) DELETE r;

// one wrong node (and all its edges)
MATCH (n {id: '<id>'}) DETACH DELETE n;
```

---

## 7. Verify your patch

```cypher
// every edge should carry a confidence in [0,1]
MATCH ()-[r]->() WHERE r.extractionConfidence IS NULL
RETURN type(r) AS edges_missing_confidence, count(*) ORDER BY count(*) DESC;

// no orphaned Technologies (should have at least one ABOUT/PRODUCED_BY)
MATCH (t:Technology) WHERE NOT (t)--() RETURN t.name AS unconnected_tech;

// re-check the layer-1 slice you were inspecting
MATCH (n) WHERE n:Technology OR n:Problem OR n:Capability OR n:Metric
   OR n:Dataset OR n:Assumption OR n:Limitation
OPTIONAL MATCH (n)-[r]-(m) RETURN n, r, m;
```

---

## 8. Will my manual edits survive re-ingestion?

| You did… | On re-ingest of the same paper |
|---|---|
| Added an **edge** between correct nodes | Survives; pipeline `MERGE`s the same edge (no dup). |
| Added a **node with the computed `id`** | Survives; pipeline `MERGE`s onto it. |
| Added a **node with a made-up `id`** | **Duplicates** — a second node appears. Fix the id. |
| Edited a **node property** the LLM also sets | **Overwritten** — the ingest's value wins (`SET n += props`). |
| Edited a property the LLM leaves blank | Survives (ingest doesn't touch it). |
| Deleted a node/edge the LLM extracts | **Comes back** on re-ingest. |

**Takeaway:** hand-patches are durable for things the extractor *doesn't*
produce (missing edges, missing reference-driven links). For things the
extractor *does* produce, re-ingestion is the source of truth — fix the input
or the lens prompt instead of the graph.

---

## Appendix — why the edge was missing in the first place

Relationship edges are built by `mapping/edges.py` **only** when the extracted
mention carries the reference field, **and** the referenced name canonicalizes
to a node that was actually emitted (otherwise the edge is silently dropped —
no dangling edges). The reference fields, per lens output:

| Missing edge | Needs this field populated | On which mention |
|---|---|---|
| `ABOUT` | `about: [names]` | Claim |
| `ADDRESSES` | `addresses: name` | Capability |
| `CONCERNS` | `concerns: name` | Limitation |
| `HOLDS_UNDER` | `holds_under: name` | Assumption |
| `PRODUCED_BY` / `EVALUATED_ON` / `MEASURED_BY` | `technologies` / `datasets` / `metrics: [names]` | Experiment |
| `SUPPORTED_BY` / `REFUTED_BY` | `claim: label` (+ `type`) | Evidence |
| `AFFILIATED_WITH` | `affiliation` | Author |
| `FUNDED_BY` | a `funding_sources` entry | (paper-level) |
| `CITES` | a cited `papers` entry | (paper-level) |

So a missing edge means *either* the model left the field blank, *or* it filled
it with a name that didn't match the emitted node's canonical form. The second
case is fixable at the source by using consistent terminology; the first is what
this manual patches by hand.
