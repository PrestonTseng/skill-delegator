# Descriptor-Relative Cache and Cross-Platform Closure Reviews

Use this checklist when closing prior findings around content-addressed filesystem caches, retained directory descriptors, atomic publication, or Linux/macOS support.

## Snapshot discipline

- Record the exact base and HEAD before reading or testing.
- Shared worktrees can advance during review. If HEAD changes, discard conclusions tied to the old commit and rerun focused probes and gates on the new HEAD.
- For read-only verification of a committed snapshot while the worktree is changing, materialize `git archive <sha>` into a temporary directory and run tests with that tree's `src` first on `PYTHONPATH`. Do not mix source from one commit with tests from another.
- In closure reports, reconstruct each original blocker, mark it closed/partial/open, and cite the exact new binding or regression. Do not report transient uncommitted failures as current facts.

## Retained-directory publication invariants

1. Create staging with an unguessable direct-child name under the retained cache descriptor (`mkdirat`/`dir_fd`).
2. Open staging relative to that descriptor and copy from source FD to staging FD.
3. Validate and hash through retained descriptors.
4. Publish with both `src_dir_fd` and `dst_dir_fd` bound to the same retained cache FD. This prevents lexical redirection and cross-filesystem `EXDEV`.
5. Clean staging with descriptor-relative, symlink-resistant removal. Suppress only an already-absent staging name; surface other cleanup failures.
6. Probe source and cache roots on genuinely different devices to prove staging/publication does not depend on the source or process-global temp filesystem.

## The validated-child binding gap

Opening and hashing a child FD is not enough if the API later returns or consumes the child's lexical name. An attacker can rename the validated child and install a different directory under the same cache key after hashing.

After every security-sensitive operation whose result will be associated with the public child name—especially whole-tree hashing and artifact discovery—rebind the name to the FD:

- `opened = fstat(child_fd)`
- `lexical = stat(name, dir_fd=parent_fd, follow_symlinks=False)`
- require both to be directories and `(st_dev, st_ino)` to match
- verify the retained parent chain before and after the comparison

Adversarial regression: begin with a valid existing cache entry; swap its public name immediately after hash completion; replace it with a valid-looking `CORRUPT` tree; require a fail-closed identity error rather than returned metadata or `accepted=True`.

A stable lexical path can still change after the final check. Distinguish this unavoidable future drift from acceptance of hostile bytes: metadata must come from the retained FD, downstream consumers must independently revalidate the lexical cache path, and the threat model must state the same-privilege mutation boundary.

## Cleanup review

For a prior residue finding, establish all three properties separately:

- cleanup targets the retained directory, not a swapped lexical path;
- path-swap probes leave external replacement directories untouched;
- cleanup failures are surfaced rather than hidden.

A test that merely asserts no `.snapshot-*` remains at the current lexical path is insufficient; also inspect the detached retained inode used during the operation.

## macOS API and CI review

Python 3.12 on macOS supports the POSIX primitives commonly needed here: `openat`-style `dir_fd` operations, `rename` with source/destination directory FDs, `listdir(fd)`, `fstat`, no-follow stats, and descriptor-relative `shutil.rmtree`. Still verify the exact APIs used rather than inferring support from Linux.

Workflow syntax validation (for example Actionlint) does not prove a macOS job can pass. If the job runs the full suite, search all selected tests for Linux-only assumptions such as `/proc/self/fd`, Linux-only filesystem injection helpers, and unguarded platform-specific syscalls or path conventions. Rewrite those tests with portable inode/FD comparisons or explicitly mark/select them as Linux-only.

A dedicated macOS workflow should run the production safe-example lifecycle in addition to portable unit tests, but hosted native execution remains unproven until that job actually runs.

## Closure report shape

1. Verdict.
2. Prior-blocker table with status, exact code citations, and focused probe evidence.
3. New blockers with exact file/line citations.
4. Non-blocking suggestions.
5. Fresh verification commands/counts, workflow-lint result, exact reviewed HEAD, and clean-tree status.
