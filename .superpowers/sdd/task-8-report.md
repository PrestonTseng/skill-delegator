# Task 8 Gate A release-candidate report

## Status

`DONE_WITH_CONCERNS` for the generic Gate A release-candidate commit. Generic code, docs, tests, package artifacts, and an installed-wheel smoke are complete. Authority branch bootstrap and all real-authority operations remain excluded. No independent review verdict exists in this worker; parent acceptance remains a separate gate.

- Base: `8f24a8960cf7163bf968226894c166c98a05bcbe`
- Branch: `feat/skill-delegator-v1`
- Requested commit: `feat: complete skill delegator v1`

## RED findings and fixes

The inherited worker summary records three concrete Gate A RED findings. The raw first-failure pytest transcript is not retained in the handoff, so its exact initial failure count/output is **CANNOT VERIFY**; no retroactive RED is claimed.

1. Filesystem-source configuration was normalized with `Path.resolve(strict=False)`, erasing the lexical path needed to reject a symlinked ancestor. Regression: `test_filesystem_source_ancestor_escape_fails_closed_without_cache_publication[symlink|file]`. Fix: retain an absolute lexical path and reject every symlink/non-directory/missing/unreadable source component before cache publication.
2. Safe-main-example target validation rejected symlink components but not an existing non-directory component. Regression: `test_target_ancestor_escape_fails_validation_without_outside_writes[file]`. Fix: reject existing non-directories during lexical target-component validation.
3. Runtime names were not one consistent bounded contract across source inventory, lock schema, and lock consumption. Regressions: hostile discovered runtime name and tampered lock runtime name in `test_lock_tampering.py`. Fix: enforce `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` in inventory, `lock.schema.json`, and resolver consumption.

This continuation found and reproduced one additional packaging RED:

```text
uv run --frozen pytest -q tests/integration/test_schema_artifacts.py
1 failed in 1.17s
```

The sdist included `.superpowers/sdd/*` task/review files and `var/cache/...`. A regression assertion was added, and Hatch sdist exclusions now omit `/.superpowers` and `/var`. GREEN:

```text
1 passed in 0.82s
```

## Final source gates

Fresh commands from this worktree after all source changes:

```text
uv lock --check
Resolved 15 packages in 2ms

uv sync --locked --python 3.12
Resolved 15 packages in 1ms
Checked 14 packages in 3ms

uv run --frozen ruff format --check .
50 files already formatted

uv run --frozen ruff check .
All checks passed!

uv run --frozen pytest -q \
  tests/integration/test_main_example_e2e.py \
  tests/adversarial/test_path_escape_matrix.py \
  tests/adversarial/test_unmanaged_preservation.py \
  tests/adversarial/test_lock_tampering.py \
  tests/integration/test_schema_artifacts.py
25 passed in 12.94s

uv run --frozen pytest -q
302 passed in 22.86s

uv run --frozen python -m compileall -q src tests
exit 0

uv run --frozen skillctl validate
Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets

uv build
Successfully built dist/skill_delegator-0.1.0.tar.gz
Successfully built dist/skill_delegator-0.1.0-py3-none-any.whl

uv run --frozen pytest -q tests/integration/test_schema_artifacts.py
1 passed in 0.81s

git diff --check
exit 0
```

The focused package test was rerun after the packaging correction; the complete focused/full/lint sequence is rerun once more immediately before commit, as recorded by the final closure evidence below.

## Package inventory

A byte-for-byte archive probe checked 18 expected source files in both wheel and sdist:

- 7 schemas: authority, delegations, lock, pool, receipt, sources, verification-receipt
- 4 docs: architecture, configuration, threat-model, update-workflow
- 6 checked example-config files: README plus five YAML files
- 1 example fixture: `tests/fixtures/example-source/hello/SKILL.md`

Results after the packaging fix:

```text
ARTIFACT_BYTES verified=18
WHEEL file_count=39
SDIST file_count=66
FORBIDDEN task-report/review/local-var=absent
```

The wheel locations are `skill_delegator/{schemas,docs}/...` and `skill_delegator/example/{config,tests/fixtures/example-source}/...`. The sdist contains the corresponding source paths. Exact bytes matched. Neither archive contains `.superpowers`, task/review reports, or generated cache/example-target/receipt output.

`.gitignore` is intentionally narrow:

```text
/var/cache/
/var/example-targets/
/var/receipts/
```

`git check-ignore --no-index` matched those three generated families. Probes under `var/other`, `var/cache-other`, `var/example-targets-other`, and `var/receipts-other` were not ignored.

## Fresh installed-wheel smoke

The just-built wheel was installed offline from local cache into a fresh uv Python `3.12.13` venv. `skillctl --help` exited 0 and listed all public commands: `validate`, `lock`, `resolve`, `plan`, `apply`, `verify`, `status`, `update`.

Packaged `example/config` and `example/tests/fixtures/example-source` were copied from `importlib.resources` into a fresh temporary Git project. Exact command exits across two runs:

| Command | Run 1 | Run 2 |
|---|---:|---:|
| `validate` | 0 | 0 |
| `lock` | 0 | 0 |
| `resolve --json` | 0 | 0 |
| `plan --json` | 1 (`CREATE`, `CREATE`) | 0 (`KEEP`, `KEEP`) |
| `apply` | 0, `Applied 2 changes to 2 targets` | 0, `Already converged` |
| `verify` | 0, `converged: 2/2 links verified across 2 targets` | same |
| `status --json` | 0, `result=converged` | same |

Final disk evidence:

```text
SUMMARY symlinks=2 receipts=1
LINKS var/example-targets/reviewer/example/hello,var/example-targets/worker/example/hello
RECEIPTS a0078dd972764d0719eed444a9b7876ced9eab8f2cfe608c54a06518957ffe55.json
RECEIPT_FIRST .../a0078dd972764d0719eed444a9b7876ced9eab8f2cfe608c54a06518957ffe55.json a0078dd972764d0719eed444a9b7876ced9eab8f2cfe608c54a06518957ffe55
RECEIPT_SECOND .../a0078dd972764d0719eed444a9b7876ced9eab8f2cfe608c54a06518957ffe55.json a0078dd972764d0719eed444a9b7876ced9eab8f2cfe608c54a06518957ffe55
CONVERGENCE deterministic-receipt=yes tracked-status-clean=yes
```

The receipt filename equals the SHA-256 of its bytes and the exact path/bytes were reused on run 2.

## Scope exclusions

No authority branches were created or updated. No real authority config, real target, or real apply was used. No GitHub operation, push, merge, PR, T8 Gate B, external network access, `/opt/knowledge` mutation, credential access, runtime restart, or publication occurred.

## CANNOT VERIFY / release concerns

- No independent security/correctness review verdict exists. An earlier `codex` attempt was unavailable and produced no verdict; this worker was explicitly told not to attempt a replacement. Parent review/independent Gate A acceptance remains required.
- The exact raw original RED transcript/count for the three inherited production hardening findings is unavailable; the handoff summary and retained regression tests establish the findings, not exact historical stdout.
- Kernel/filesystem race interleavings, power-loss durability, macOS/Windows/network filesystems, and hostile same-privilege processes are not exhaustively verified. See `docs/threat-model.md`.
- The wheel smoke used only local package cache/resolution. It does not prove installation from a public index or publication metadata on an external package service.
