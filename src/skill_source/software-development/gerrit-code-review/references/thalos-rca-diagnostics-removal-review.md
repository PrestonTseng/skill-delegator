# Thalos RCA diagnostics removal review notes

Session-derived notes from reviewing `tcloud/safeart/thalos` Gerrit change 7948 (`SART-1857 Remove RCA diagnostics`). Use this when reviewing patches that remove temporary diagnostic instrumentation after an RCA / validation protocol has been narrowed.

## Source-of-truth check

For RCA diagnostic removal, do not treat "less observability" as inherently bad. First read the current issue / RCA page and determine whether the diagnostic path is still approved.

In the reviewed SART-1857 case, the Jira comments and canonical Confluence RCA page said:

- development root cause remained unknown;
- first-stage development evidence should be limited to hardened opt-in external profiling / slow-callback monitoring / thresholded timer evidence;
- in-process stack sampler, event-loop watchdog, broad phase timing, ACK timing, behavior-changing ablations, and mock fault controls should remain disabled for first observation.

Given that source-of-truth boundary, removing temporary in-process stack sampling and unconditional callback-runtime logs was aligned with the requirement rather than a regression.

## Review checklist for diagnostic-removal patches

1. Fetch exact Gerrit patch set and linked Jira/Confluence RCA source.
2. Confirm whether the diagnostic being removed is explicitly superseded, disabled, or out of scope in the current RCA protocol.
3. Inspect both sides of the change:
   - deleted implementation and interface files,
   - DI/service registry wiring,
   - settings model and env/example docs,
   - changed tests and test fixtures,
   - baseline log messages restored after removing diagnostic metadata.
4. Search the whole repo for stale symbols and diagnostic log strings, not just imports:
   - `stack_sampler`, `StackSampler`, `STACK_SAMPLER`,
   - diagnostic-specific log text such as `Timer callback runtime`, `asyncio_pending_tasks`, `callback=` when it was diagnostic-only.
5. Run the repository's CI-like path when feasible. For thalos, `./build.sh --run-tests` exercised Docker pyright, full pytest, and production image build.
6. Still run lightweight local checks when useful:
   - focused timer tests,
   - full unit tests,
   - pyright,
   - changed-file black/isort,
   - added-line static scan,
   - `git diff --check`.

## Finding calibration

- If source-of-truth says the diagnostic is no longer allowed or should be disabled, removal is expected behavior.
- Minor formatting churn such as missing EOF newline in `.env.example` is a nit unless repository checks enforce it.
- Do not ask for replacement observability unless the current RCA protocol requires it; otherwise it may reintroduce the diagnostic surface the patch is meant to remove.

## Useful commands

```bash
# Exact Gerrit checkout pattern
cd /tmp
git clone https://lilee-ci-tw.lileesystems.com/gerrit/tcloud/safeart/thalos thalos-CHANGE
cd thalos-CHANGE
git fetch origin refs/changes/NN/CHANGE/PS
git checkout FETCH_HEAD

# Stale diagnostic-symbol sweep
rg 'stack_sampler|StackSampler|STACK_SAMPLER|Timer callback runtime|asyncio_pending_tasks|callback=' .

# Verification layers
uv run pytest test/unit_test/timer_service -q
uv run pytest test/unit_test -q
uv run pyright
uv run black --check <changed-files>
uv run isort --check-only <changed-files>
git diff --check HEAD^..HEAD
./build.sh --run-tests
```
