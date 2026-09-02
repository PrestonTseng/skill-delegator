# Exceptional Resource-Ownership Probes

Use this pattern when reviewing or remediating code that acquires an OS resource and can fail before returning ownership: directory/file descriptors, sockets, locks, temporary files, handles, or transactions.

## Ownership contract

1. Before acquisition succeeds, the caller owns nothing.
2. After acquisition but before successful return, the callee owns the resource.
3. Every exceptional exit in that interval releases it.
4. Ownership transfers exactly once, only on successful return.
5. Cleanup failure does not replace the primary failure; preserve the original exception and attach cleanup diagnostics.
6. Outer orchestration releases already-owned parent resources when a later child acquisition or validation fails.

## Fault matrix

Enumerate every operation after acquisition and before transfer, then inject one failure at a time. A retained directory-descriptor verifier commonly needs:

| Phase | Injection | Required proof |
|---|---|---|
| Initial metadata read | first `fstat` | exact acquired FD closed; original exception identity preserved |
| Permission repair | `fchmod` | exact FD closed |
| Durability repair | `fsync` | exact FD closed |
| Revalidation | second `fstat` | exact FD closed, including a direct `BaseException` subclass |
| Cleanup | `close` | original failure re-raised with cleanup diagnostic |
| Child verification | failure after parent/root acquisition | child, root, and parent FDs all closed |

Test a direct `BaseException` subclass when production promises cleanup on every exceptional exit; `Exception`-only probes do not prove that contract.

## Exact leak proof

Use independent assertions:

- Capture the exact resource from the real acquisition primitive and prove invalidation after failure. For an FD, saved real `os.fstat(fd)` must raise `EBADF`.
- Compare process-level resource counts before and after. On Linux, `/proc/self/fd` is a useful secondary check.

Save real primitives before monkeypatching and scope wrappers to the target descriptor so fixture/test-runner I/O remains untouched. Always use a `finally` block with saved real cleanup so an intentional RED leak does not contaminate later tests.

## Valid RED and immutable history

A valid RED shows the injected primary error propagated while cleanup assertions failed. Setup/import errors, incorrect monkeypatch signatures, or failures before acquisition are not ownership evidence.

When producing immutable test-first history:

1. Run and preserve the narrow aggregate RED output.
2. Commit tests only.
3. Add the minimal production fix in a separate commit.
4. Prove staged path scope before both commits.

When independently reviewing an already-committed RED/GREEN sequence, do not checkout or mutate the reviewed worktree. Verify that the tests-only commit's parent is the accepted base, that its production delta is empty, and that the production commit's test delta is empty. Export the tests-only commit with `git archive` into a temporary directory and run the exact focused selection there; this proves the new tests fail against old production. Then run the identical selection at final HEAD. Preserve both exact counts.

## Minimal implementation pattern

Wrap only the owned interval:

```python
resource = acquire()
try:
    verify(resource)
except BaseException as primary:
    try:
        release(resource)
    except BaseException as cleanup:
        primary.add_note(f"cleanup failed: {cleanup!r}")
    raise
return resource
```

Once a common guard owns cleanup, remove branch-local releases to prevent double-close. Do not retry a failed POSIX `close`: descriptor state may be ambiguous and a retry can close a descriptor that has already been reused. Use a bare `raise` from the primary handler so exception identity and traceback are preserved. If cleanup diagnostics use `BaseException.add_note`, confirm the project's supported Python version provides it. Do not alter successful-path provider, validation, publication, or cache-identity semantics.

Add focused controls beyond failure cases:

- successful verification returns a still-open, usable resource to the caller;
- non-directory and bad-mode validation exits release exactly once;
- a cleanup primitive raising a direct `BaseException` cannot mask the primary error;
- the primary traceback still contains the injected failure site;
- already-owned parent/root resources unwind when child verification fails.

## Closure verification

Run the narrow fault matrix, focused subsystem suite, full suite, repository compile/type/lint gates, diff hygiene, authorized path inventory, terminal-newline check, and clean-worktree check. Append exact test names, RED/GREEN counts, commit hashes, finding disposition, and remaining concerns to the existing task report.
