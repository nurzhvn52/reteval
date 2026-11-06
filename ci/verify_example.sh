#!/bin/sh
set -eu
out=$(mktemp -d)
reteval evaluate --qrels examples/data/qrels.txt \
  --run bm25=examples/data/runs/bm25.run \
  --run "dense=examples/data/runs/dense.seed*.run" \
  --run "hybrid=examples/data/runs/hybrid.seed*.run" \
  --metrics ndcg@10 recall@10 mrr@10 map --baseline bm25 \
  --output "$out/report.md" --plot "$out/report.png"
diff -u examples/expected/report.md "$out/report.md"
echo "example report matches examples/expected/report.md"
