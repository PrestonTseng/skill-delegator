# Test-scoped pytest and OS-matrix review

Use this checklist when a bounded change relocates pytest configuration and deduplicates OS-specific CI jobs.

## Pytest relocation

1. Read the exact diff and current files. Confirm the repository-root `conftest.py` is gone and the moved plugin computes repository-relative constants from its new depth.
2. Prove automatic discovery across the real configured suite, not only a focused test. Run collection with `--trace-config` and require the moved module/path to appear as a registered plugin. Check `pyproject.toml` test paths so the moved conftest governs every real test subtree.
3. Preserve a process-level pre-body probe. Generate an external hostile test whose body writes a sentinel, invoke pytest from the repository root with `-p <moved.module>`, and require policy exit code 4, the bounded policy diagnostic, and an absent sentinel.
4. If importability requires adding `tests/__init__.py`, audit both release artifacts. An explicit wheel package list can exclude `tests` while the VCS-driven sdist still includes it. Build wheel and sdist at both base and candidate and compare relevant members; do not equate “not installed from the wheel” with “no packaging change.”

## Single OS matrix

1. Parse the workflow semantically. Require exactly one intended job, an exact OS list, and `runs-on` bound to the matrix expression rather than a literal runner.
2. Compare the ordered run-command vector with the accepted base. Recheck current-ref checkout, absent branch/ref conditions, absent workflow/job/step working-directory overrides, and prohibited mutation commands.
3. Mutation-test at least: second workflow, extra job, missing intended OS, literal runner, checkout ref, branch condition, each working-directory level, and prohibited command. Exact matrix equality should also reject an extra OS and either intended OS being removed.
4. Decide matrix cancellation semantics explicitly. GitHub Actions matrix `fail-fast` defaults to true and cancels queued/in-progress siblings after one matrix failure. If prior independent OS jobs supplied complete cross-platform diagnostic evidence, omission of `fail-fast: false` is a material evidence regression even though merge blocking remains fail-closed. Enforce the chosen value in the semantic contract.

## Reporting

Issue separate **SPEC COMPLIANCE** and **TASK QUALITY** verdicts. Distinguish product/runtime safety from release-artifact truth and diagnostic-evidence retention. Record focused tests, full suite, lint/compile/schema gates, artifact builds, artifact-member inspection, and diff hygiene.
