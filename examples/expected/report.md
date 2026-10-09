## Effectiveness

Mean over 40 queries with at least one document of relevance >= 1. For systems with several runs, ± is the standard deviation of the run means.

| System | Runs | nDCG@10 | Recall@10 | MRR@10 | MAP |
| --- | ---: | ---: | ---: | ---: | ---: |
| bm25 | 1 | 0.4798 | 0.6196 | 0.5328 | 0.3551 |
| dense | 3 | 0.5016 ± 0.0277 | 0.5840 ± 0.0413 | 0.5566 ± 0.0146 | 0.4182 ± 0.0164 |
| hybrid | 3 | 0.6782 ± 0.0147 | 0.7462 ± 0.0190 | 0.7585 ± 0.0152 | 0.5825 ± 0.0136 |

## Comparison with baseline `bm25`

Difference is the mean per-query difference to the baseline, the 95% CI is a percentile bootstrap over queries, and p is from a two-sided paired randomization test (10000 resamples, seed 0).

| System | Metric | Difference | 95% CI | p |
| --- | --- | ---: | ---: | ---: |
| dense | nDCG@10 | +0.0218 | [-0.1073, +0.1466] | 0.7367 |
| dense | Recall@10 | -0.0356 | [-0.1781, +0.0995] | 0.6258 |
| dense | MRR@10 | +0.0238 | [-0.1200, +0.1690] | 0.7385 |
| dense | MAP | +0.0631 | [-0.0505, +0.1729] | 0.2716 |
| hybrid | nDCG@10 | +0.1984 | [+0.1251, +0.2731] | 0.0001 |
| hybrid | Recall@10 | +0.1267 | [+0.0390, +0.2176] | 0.0081 |
| hybrid | MRR@10 | +0.2257 | [+0.1282, +0.3290] | 0.0003 |
| hybrid | MAP | +0.2274 | [+0.1566, +0.3000] | 0.0001 |
