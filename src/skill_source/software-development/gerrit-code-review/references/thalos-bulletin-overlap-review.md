# Thalos bulletin overlap Gerrit review notes

Use these notes when reviewing thalos patches that touch bulletin range enforcement, TSR applicability, or milepost overlap logic.

## Source-of-truth pattern

- Read Gerrit metadata for the exact patch set first.
- If the subject references a Jira ticket, fetch that issue directly. Some thalos bug tickets may contain only a summary/template and no acceptance criteria; in that case, say the review is grounded in the Gerrit subject plus implementation context rather than inventing requirements.

## Local checkout and dependency setup

For exact patch-set review:

```bash
git clone https://lilee-ci-tw.lileesystems.com/gerrit/tcloud/safeart/thalos /tmp/thalos-review-CHANGE
git fetch origin refs/changes/NN/CHANGE/PS
git checkout --detach FETCH_HEAD
uv sync --group dev
```

If system Python lacks project dependencies, do not stop at `No module named pytest` / `No module named pydantic`; thalos has `pyproject.toml` + `uv.lock`, so `uv sync --group dev` is the correct local setup path.

## Verification layers that worked

```bash
uv run pytest test/unit_test/bulletin_service/test_enforce.py test/unit_test/bulletin_service/test__find_overlaps.py -q
uv run pyright thalos/core/bulletin_service.py test/unit_test/bulletin_service/test_enforce.py
./build.sh --run-tests
```

`./build.sh --run-tests` is the CI-like path: it runs pyright, all tests in Docker, then production image build. Prefer reporting this output over only local targeted tests when Docker is available.

## Bulletin overlap semantics

For milepost ranges, thalos code elsewhere already treats ranges direction-independently by normalizing endpoints with `min()` / `max()` before checking overlap. A review of bulletin enforcement should check that it preserves the strict half-open predicate:

```python
start_a < end_b and start_b < end_a
```

Important edge probes:

- descending overlap, e.g. existing `11500 -> 10500`, target `11500 -> 11200` should conflict;
- descending adjacency, e.g. existing `11500 -> 10500`, target `10500 -> 10000` should not conflict;
- mixed ascending/descending order should still conflict when normalized intervals overlap.

## Lint interpretation pitfall

If manual pylint flags a new warning, compare against the parent revision and against the project's actual CI path before calling it blocking. In this review class, `build.sh --run-tests` did not run pylint; a new pylint-only `too-many-locals` was non-blocking when pyright, targeted tests, and full Docker test/build passed.
