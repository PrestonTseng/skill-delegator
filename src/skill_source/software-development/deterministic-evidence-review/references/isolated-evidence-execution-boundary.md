# Isolated Execution Boundaries for Deterministic Publication

Use this reference when a deterministic evidence CLI must bind published artifacts to committed code, but reviewers start treating arbitrary same-process monkeypatching as an in-process security boundary.

## Threat-model rule

Pure Python cannot authenticate itself after an attacker already has arbitrary code execution inside the same interpreter. Such an attacker can replace the loader, authenticator, `run_cli`, `hashlib`, `os`, import hooks, or publication calls. Function metadata (`__module__`, `__name__`, `co_filename`) is not implementation authentication and creates false assurance.

Do not enter a metadata-check arms race. Either establish a fresh isolated production process loading clean committed code, or explicitly narrow the claim and state that hostile same-process code execution is out of scope. The narrowed claim is honest only when the production process boundary is actually enforced.

## Recommended production boundary

For a src-layout Python project managed by uv:

```bash
uv run --isolated --with-editable . \
  python -I -X pycache_prefix=/dev/null \
  -m package.evidence_cli ...
```

Verify this command in the target repository. `python -I` alone may not find a src-layout package because it ignores `PYTHONPATH`; the isolated editable installation makes the project importable through the ephemeral environment. `-I` also does **not** prove that committed `.py` bytes were compiled: Python may execute a timestamp-valid ignored `__pycache__/*.pyc` while Git remains clean. Routing `pycache_prefix` to `/dev/null` prevents worktree bytecode lookup and retained bytecode writes without introducing a host-random path into deterministic manifests.

Enforce all of the following:

- public production entry refuses unless `sys.flags.isolated == 1`;
- public production entry requires normalized `sys.pycache_prefix == "/dev/null"`; reject missing or alternate prefixes;
- every loaded provenance-critical module with non-null `__cached__` routes beneath `/dev/null`;
- production dispatch cannot route through dependency-injected test helpers;
- full pre-run Git porcelain status is empty, not only selected source directories;
- repeat the clean-state check immediately before immutable publication;
- executing provenance-critical source resolves to the intended repository/install artifact and matches committed Git bytes;
- manifest records the execution boundary, isolated-interpreter status, bytecode-cache mode, code commit/source hashes, and explicit same-process-injection exclusion;
- cache and output confinement remain descriptor-based and no-follow; process isolation does not replace filesystem hardening.

### Poisoned-bytecode regression

A meaningful regression must prove both sides rather than merely assert configuration:

1. In a disposable clean clone, create poisoned bytecode for a production module.
2. Restore the committed `.py` bytes and make the `.pyc` timestamp/size metadata valid for that source.
3. Prove full Git porcelain remains empty.
4. Prove an otherwise equivalent unprotected control actually executes the poison.
5. Run the canonical `/dev/null` command and prove committed source behavior executes instead.
6. Snapshot worktree bytecode before/after and prove the protected command neither reads the poison nor creates retained `.pyc` files.

This control/protected pair prevents a tautological test that would pass even if the poison fixture were invalid.

A private dependency-injected helper may remain for tests, but label it non-production and prove `main()` and public `run_cli()` never dispatch through it.

## Review checklist

1. Run the real isolated command in a subprocess; do not infer production importability from pytest.
2. Confirm non-isolated public invocation fails before replay/publication.
3. Confirm `-I` ignores user site and `PYTHONPATH` while the intended project still imports.
4. Verify full-worktree cleanliness and exact committed-source binding before and after expensive computation.
5. Require deterministic manifest bytes for the same NOW, commit, cache, and status.
6. Keep the threat claim scoped: fresh-process integrity is reviewed; arbitrary code already executing inside that process is not.
7. Do not accept metadata-compatible monkeypatch probes as evidence that the declared isolated-process boundary failed unless the probe also demonstrates an injection path into the canonical fresh command.

## Expensive replay discipline

Before a multi-hour replay, close the design-to-manifest matrix and security review. If a post-replay aggregate validator fails:

- persist stdout, stderr, and exit code;
- rerun once through a diagnostic-only harness that saves the validated replay object and pre-validation result under `/tmp`;
- use the saved replay to reproduce and fix aggregation/rendering defects quickly;
- do not treat the saved object as final publication authority;
- after code review, run the canonical production CLI again so the final manifest binds the actual commit and isolated execution boundary.

If an immutable package is later found provenance-incomplete, preserve it as blocked evidence and publish a versioned replacement. Never overwrite it, and stop obsolete reruns before spending hours proving determinism for a schema that cannot be approved.
