# Task 8 Gate A release-hardening report

## Status

`DONE_WITH_CONCERNS` for the generic Gate A release candidate. The release-hardening implementation, regressions, documentation, package artifacts, and an offline installed-wheel smoke are complete. Authority branches, real authority configuration/targets/apply, GitHub operations, external network access, `/opt/knowledge`, and credentials remained excluded. A fresh independent post-fix security verdict is still outside this worker.

- Hardening base: `b92927770841b52d2ba3178035fdcf48dec3c536`
- Branch: `feat/skill-delegator-v1`
- Commit message: `fix: harden skill delegator v1 release evidence`

## Original and review RED evidence

### Original Gate A implementation RED

The inherited Task 8 report retained these original behavioral failures and fixes:

1. Filesystem-source configuration had erased lexical identity with `Path.resolve(strict=False)`. Regression: `test_filesystem_source_ancestor_escape_fails_closed_without_cache_publication[symlink|file]`.
2. Safe-main-example target validation had rejected symlinks but not existing non-directory ancestors. Regression: `test_target_ancestor_escape_fails_validation_without_outside_writes[file]`.
3. Runtime names had not shared one bounded grammar across discovery, schema, and lock consumption. Regressions were retained in lock-tampering coverage.
4. The sdist included `.superpowers/sdd/*` and generated `var/cache`. The recorded packaging RED was `1 failed in 1.17s`; its exclusion regression then passed `1 passed in 0.82s`.

The continuation handoff recorded that the first supplemental focused collection failed because `DesiredSource` did not exist. After the first implementation pass it recorded `9 passed / 29 failed`; 28 were stale schema-first message expectations and one was an argparse help expectation. The raw collection transcript is unavailable, so any more exact original count or traceback is **CANNOT VERIFY** rather than reconstructed.

### Formal Gate A review RED

The formal review rejected `b92927770841b52d2ba3178035fdcf48dec3c536` for an ancestor/final filesystem-source swap race. Its deterministic probe reported:

```json
{
  "cache_published": true,
  "cached_outside_content": true,
  "lexical_source_is_symlink_after_swap": true,
  "resolved_runtime_name": "raced",
  "swap_fired": true
}
```

The fix retains descriptor/inode evidence for every existing source component and performs source resolution from the retained descriptor path. Direct regressions cover both final-source and ancestor replacement and prove outside bytes are never cached.

### Supplemental review RED

The supplemental review found three Important defects:

1. Verification could claim a locked source identity after ungranted whole-cache tampering because only granted skill directories were re-hashed.
2. `--lock-timeout nan` could bypass `< 0` validation and block indefinitely under lock contention.
3. Hostile newline/control/hidden canonical path segments could enter generated locks.

It also identified stale release claims: POSIX/Linux-only implementation metadata, a broken packaged documentation link, and documentation that incorrectly said all `var/` was ignored.

On this continuation's first untouched full-suite run, the exact result was `315 passed, 6 failed in 23.89s`. All six were integration expectations made stale by the already-implemented stricter contracts: canonical schema rejection order/UTF-8 diagnostics, the former Unicode discovery allowance, and receipts that formerly permitted Git without snapshot evidence. No production contract was weakened to clear them.

## Final schema and evidence contract

- Filesystem source resolution retains existing-directory descriptors and inode identities through snapshot validation/copying; changed final or ancestor pathname components cannot redirect published cache content.
- Git locks require both `resolved_commit` and a directly computed full-snapshot `tree_hash`. Filesystem locks use the same full-snapshot hash as revision and tree identity.
- `DesiredSource` carries one expected full-cache snapshot identity per source. Verification freshly hashes each complete cached snapshot exactly once per source, before receipt publication, including ungranted content.
- Receipt evidence is strict and coherent: Git receipt identities require commit plus full tree identity; filesystem receipt revision and tree identity must match. Missing or incoherent source evidence cannot produce a receipt.
- A shared canonical grammar is used by discovery, schemas, configuration, and resolution. Direct discovery regressions reject newline, ASCII control, hidden, Unicode/non-ASCII, and non-UTF-8 segments.
- Lock timeout must be finite and non-negative. A real held `flock` contention regression proves NaN is rejected before acquisition rather than hanging.
- `fcntl` import is conditional; help remains available without it, and unsupported operational use emits one bounded `skillctl error: V1 requires POSIX` diagnostic.
- Project metadata declares POSIX and Linux and contains no Windows classifier. Windows remains unsupported.
- Source docs use `docs/configuration.md`; installed-wheel docs use `skill_delegator/docs/configuration.md`.
- Generated-state documentation names only `var/cache/`, `var/example-targets/`, and `var/receipts/` as ignored.

## Final fresh source gates

All commands were rerun after formatting/import fixes against the final pre-commit bytes:

```text
uv lock --check
Resolved 15 packages in 1ms

uv sync --locked --python 3.12
Resolved 15 packages in 1ms
Checked 14 packages in 0.45ms

uv run --frozen ruff format --check .
52 files already formatted

uv run --frozen ruff check .
All checks passed!

focused release suite
161 passed in 13.70s

uv run --frozen pytest -q
326 passed in 23.26s

uv run --frozen python -m compileall -q src tests
exit 0

uv run --frozen skillctl validate
Valid configuration: 1 authority, 1 source, 1 pool entry, 2 targets

uv build
Successfully built dist/skill_delegator-0.1.0.tar.gz
Successfully built dist/skill_delegator-0.1.0-py3-none-any.whl

uv run --frozen pytest -q tests/integration/test_schema_artifacts.py
1 passed in 0.82s
```

The focused release suite included the main example, path escape, unmanaged preservation, lock tampering, artifact package test, and changed lockfile/verifier/config/reconciler/platform suites.

## Package and archive evidence

A direct archive probe compared 18 expected source files byte-for-byte in both artifacts:

- 7 schemas;
- 4 documentation files;
- README plus 5 checked example configuration files;
- the packaged example `SKILL.md` fixture.

```text
ARTIFACT_BYTES verified=18
WHEEL file_count=40
SDIST member_count=68
FORBIDDEN internal-review/local-var/credentials/residue=absent
METADATA platform=POSIX,Linux; Windows=absent
```

Neither archive contains `.superpowers`, task/review reports, generated `var` state, credentials, `.git` residue, bytecode, or `__pycache__`. Updated schemas, docs, config, and fixture bytes are present.

## Fresh offline installed-wheel smoke

The just-built wheel was installed with `uv pip install --offline` into a new uv venv using Python `3.12.13`. `skillctl --help` exposed all eight commands: `validate`, `lock`, `resolve`, `plan`, `apply`, `verify`, `status`, and `update`.

Packaged config and fixture resources were copied into a fresh temporary project and run for two rounds:

```text
ROUND1 plan=CREATE,CREATE apply=Applied 2 changes to 2 targets
ROUND1 verify=converged: 2/2 links verified across 2 targets
ROUND2 plan=KEEP,KEEP apply=Already converged
ROUND2 verify=converged: 2/2 links verified across 2 targets
FINAL symlinks=2 managed=2 receipts=1
RECEIPT deterministic=yes
SECOND_ROUND target_and_receipt_bytes_unchanged=yes status=converged
```

The single receipt filename equals SHA-256 of its exact bytes, and the second round reused the same path/bytes without target or receipt mutation.

## CANNOT VERIFY / concerns

- No fresh independent post-fix security/correctness acceptance verdict was produced by this worker; parent review remains the external Gate A acceptance step.
- Exhaustive kernel/filesystem race interleavings, hostile same-privilege processes, power-loss durability, unusual/network filesystems, macOS, and Windows are not verified. The release contract is POSIX/Linux; it does not claim Windows support.
- Offline local-cache installation does not prove public-index publication, external package metadata rendering, or installation from a public service.
- Gate B authority branches and real-profile targets/apply are intentionally excluded.
