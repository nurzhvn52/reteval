# Contributing

## Set up

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install   # optional, runs ruff before every commit
```

Before opening a pull request, run the same checks as CI:

```bash
ruff check . && ruff format --check . && mypy && pytest --cov
```

## Workflow

The project follows GitHub Flow: `main` is always releasable and every change goes
through a pull request.

1. Open an issue, or pick one, describing the problem or feature.
2. Create a short-lived branch from `main`: `feature/<topic>`, `fix/<topic>`,
   `docs/<topic>` or `ci/<topic>`.
3. Commit in small steps. Messages follow
   [Conventional Commits](https://www.conventionalcommits.org/):
   `feat: add hit@k metric`, `fix: ...`, `test: ...`, `docs: ...`, `ci: ...`.
4. Open a pull request that says `Closes #<issue>`. CI must pass before merging;
   `main` is protected and cannot be pushed to directly.
5. Merge with a merge commit and delete the branch.

## Adding a metric

1. Add the function to `src/reteval/metrics.py` with the common signature
   `(ranking, judgements, k=None, min_rel=1) -> float` and register it in `_REGISTRY`.
2. Add a test with a value computed by hand in `tests/test_metrics.py`, and the metric
   to the invariants in `tests/test_properties.py`.
3. Give a reference (paper or tool) for the definition in the pull request.

## Changing results

If a change alters the numbers in `examples/expected/report.md`, the reproducibility
job fails. Regenerate the file with the command in [examples/README.md](examples/README.md)
and explain in the pull request why the results changed.

## Releasing

1. Update `version` in `pyproject.toml` and `CITATION.cff`, and move the entries under
   `Unreleased` in `CHANGELOG.md` to the new version.
2. Merge the pull request, then tag the merge commit and push the tag:
   `git tag -a v0.2.0 -m "reteval 0.2.0" && git push origin v0.2.0`.
3. The release workflow checks the version, runs the tests and publishes the release.
