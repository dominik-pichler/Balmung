```
                ,-----.
               #,-. ,-.#
              () a   e ()
              (   (_)   )
              #\_  -  _/#
            ,'   `"""`    `.
          ,'      \X/      `.
         /         X     ____\
        /          v   ,`  v  `,
       /    /         ( <==+==> )
       `-._/|__________\   ^   /
      (\\)  |______@____\  ^  /
        \\  |     ( )    \ ^ /
         )  |             \^/
        (   |             |v
       <(^)>|             |
         v  |             |
            |             |
            |_.--.__ .--._|
              `==='  `==='
```

# Balmung

> Thoughts, experiments, and code about information, chaos, and everything in between.

A personal workspace for one long question: **where does information come from, how does it become knowledge, and where does it break down?** It collects theoretical notes, small experiments, and working implementations — from spectral graph theory to neural rerankers.

---

## The Thread

The documentation follows a single line of inquiry:

**What is information? → How does it become knowledge? → What stays unknowable? → How do I organize the flow?**

Everything under `docs/` is a station along that path.

---

## Start Here

- **[`docs/`](docs/README.md)** — theoretical notes, concept studies, philosophical reflections
- **[`code/`](code/)** — implementations, notebooks, training scripts
- **[`library/`](library/)** — working templates for notes & project docs

---

## Documentation

### 1 · Foundations & Philosophy
Definitions and reflections on information, knowledge, undecidability, and systems.

- **[What is information?](docs/01_foundations/01_what_is_information.md)** — lexical, philosophical, mathematical & epistemological views
- **[The quest for knowledge](docs/01_foundations/02_quest_for_knowledge.md)** — how information becomes knowledge: Descartes → Popper → modern epistemology
- **[The unknown](docs/01_foundations/03_the_unkown.md)** — what cannot be known: Turing's undecidability & Gödel's incompleteness
- **[Chaos & complexity](docs/01_foundations/04_chaos_and_complexity.md)** — missing information: system theory, chaos, complex dynamics
- **[Semantic systems](docs/01_foundations/05_semantic_systems.md)** — machine understanding vs. human meaning
- **[Turing machines](docs/01_foundations/06_turing_machines.md)** — the fundamental model of computation

### 2 · NLP & Embeddings
Entity recognition, embedding strategies, and model definitions.

- **[ER + Offeneregister.de](docs/02_nlp_embeddings/01_er_nlp_document.md)** — export pipeline & preparation
- **[BERT embeddings](docs/02_nlp_embeddings/02_bert_embeddings.md)** — architecture & embedding strategies
- **[Models and other mysteries](docs/02_nlp_embeddings/03_models_and_other_mysteries.md)** — model definitions, business vs. academic perspectives

### 3 · Knowledge Graphs & Applications
Concept papers and pitches on knowledge graphs and graph neural networks.

- **[KG applications](docs/03_knowledge_graphs/01_kg_applications.md)** — fraud detection, AML, credit scoring & personalization
- **[KG pitch](docs/03_knowledge_graphs/02_kg_pitch.md)** — revolutionizing banking with knowledge graphs & GNNs
- **[Kant's ramble](docs/03_knowledge_graphs/03_kants_ramble.md)** — Kant's epistemology as a graph reference

### 4 · Systems & Pipelines
Architecture concepts, topic modeling, and descriptive analysis.

- **[Orchestrating information](docs/04_systems_pipelines/01_orchestrating_information.md)** — taming overload: sources, distillation & extraction
- **[Topic modeling as fishing](docs/04_systems_pipelines/02_topic_modeling_fishing.md)** — traditional TM → Word2Vec → BERTopic
- **[Descriptive analysis](docs/04_systems_pipelines/03_descriptive_analysis_test.md)** — booking rates, evaluations, working hours

→ **Full index:** [`docs/README.md`](docs/README.md)

---

## Code

| Project | Question | Status |
|---------|----------|--------|
| **[Kant's Knowledge Graph](code/kants_knowledge_graph/)** | Philosophical ideas → knowledge graphs (rule-based + LLM + BERT) | Demo |
| **[Ishmael's Guide to (Topic) Fishing](code/ismails_guide_to_fishing/)** | Automated identification of central topics in corpora | Ready |
| **[Neural (Re-)Rankers](code/reranking/)** | K-NRM & TK — implementation, training & evaluation | Ready |
| **[RAG-based QA System](code/Q_and_A/)** | Extending rankers with OOV queries | Ready |
| **[Graph RAG QA](#)** | KG-based question answering | In progress |
| **[Data Compressors](code/utils/)** | Shannon-Fano, neural compression, morpheme identification | Demo |

---

*Questioned, researched, implemented. Feel free to reach out if any of this interests you.*