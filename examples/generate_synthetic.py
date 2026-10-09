"""Generate the synthetic example in ``examples/data``.

The files imitate a retrieval experiment - a lexical baseline (BM25), a dense
retriever trained with three random seeds and a hybrid of the two - but the scores
are random numbers, not the output of real systems. They demonstrate the tool and
serve as a regression test in CI.

About a fifth of the queries are "lexical": they depend on exact terms, the dense
retriever handles them poorly and the hybrid recovers through BM25. This gives the
per-query output realistic failure cases to look at.

Run from the repository root:  python examples/generate_synthetic.py
"""

from pathlib import Path

import numpy as np
import numpy.typing as npt

N_QUERIES = 40
CORPUS_SIZE = 2000
POOL = 100  # candidate documents per query
DEPTH = 20  # documents retrieved per query
SEEDS = (1, 2, 3)
OUT = Path(__file__).parent / "data"

Array = npt.NDArray[np.float64]


def zscore(x: Array) -> Array:
    return (x - x.mean()) / x.std()


def write_run(path: Path, tag: str, results: dict[str, tuple[list[str], Array]]) -> None:
    lines = []
    for qid, (docs, scores) in results.items():
        order = np.argsort(-scores, kind="stable")[:DEPTH]
        for rank, i in enumerate(order, start=1):
            lines.append(f"{qid} Q0 {docs[i]} {rank} {scores[i]:.4f} {tag}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rng = np.random.default_rng(2026)
    corpus = [f"doc{i:04d}" for i in range(1, CORPUS_SIZE + 1)]
    qrels: list[str] = []
    bm25: dict[str, tuple[list[str], Array]] = {}
    dense: dict[int, dict[str, tuple[list[str], Array]]] = {seed: {} for seed in SEEDS}
    hybrid: dict[int, dict[str, tuple[list[str], Array]]] = {seed: {} for seed in SEEDS}

    for q in range(1, N_QUERIES + 1):
        qid = f"q{q:03d}"
        docs = [str(d) for d in rng.choice(corpus, size=POOL, replace=False)]
        n_relevant = int(rng.integers(1, 6))
        grades = np.zeros(POOL)
        grades[:n_relevant] = rng.choice([1, 2], size=n_relevant, p=[0.6, 0.4])
        # judged documents: the relevant ones and five judged non-relevant ones
        qrels += [f"{qid} 0 {docs[i]} {int(grades[i])}" for i in range(n_relevant + 5)]

        difficulty = rng.uniform(0.6, 1.6)
        lexical_query = rng.random() < 0.2
        lexical = difficulty * 1.0 * grades + rng.normal(size=POOL)
        semantic_skill = 0.3 if lexical_query else 1.4
        semantic = difficulty * semantic_skill * grades + 0.8 * rng.normal(size=POOL)
        bm25[qid] = (docs, lexical)

        for seed in SEEDS:
            # the seed changes the trained model, i.e. adds run-specific noise
            seed_noise = np.random.default_rng([seed, q]).normal(size=POOL)
            dense_scores = semantic + 0.6 * seed_noise
            dense[seed][qid] = (docs, dense_scores)
            hybrid[seed][qid] = (docs, 0.5 * zscore(lexical) + 0.5 * zscore(dense_scores))

    (OUT / "runs").mkdir(parents=True, exist_ok=True)
    (OUT / "qrels.txt").write_text("\n".join(qrels) + "\n", encoding="utf-8")
    write_run(OUT / "runs" / "bm25.run", "bm25", bm25)
    for seed in SEEDS:
        write_run(OUT / "runs" / f"dense.seed{seed}.run", f"dense-s{seed}", dense[seed])
        write_run(OUT / "runs" / f"hybrid.seed{seed}.run", f"hybrid-s{seed}", hybrid[seed])


if __name__ == "__main__":
    main()
