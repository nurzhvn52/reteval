# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-09

### Added

- Readers for TREC qrels and run files with file and line numbers in error messages (#1).
- Metrics P@k, Recall@k, MRR, MAP, nDCG@k and Hit@k with optional cutoffs (#2).
- Aggregation of repeated runs, paired randomization test and bootstrap confidence
  interval of the difference to a baseline (#3).
- `reteval evaluate` and `reteval metrics` commands; Markdown, CSV and JSON reports,
  per-query CSV and a bar chart (#4).
- CI: lint, strict type checking, tests on Python 3.11-3.14 and Windows, package build (#5).
- Synthetic example and a reproducibility check in a pinned environment (#6).
- README, citation metadata, contribution guide, issue and pull request templates (#7).
- Release workflow that publishes a GitHub release for version tags (#8).

[Unreleased]: https://github.com/nurzhvn52/reteval/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nurzhvn52/reteval/releases/tag/v0.1.0
