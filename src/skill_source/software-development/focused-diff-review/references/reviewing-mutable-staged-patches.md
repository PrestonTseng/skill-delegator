# Reviewing mutable staged patches

Use this when the requested review target is the Git index, especially if another actor may keep editing, staging, or committing while the review runs.

## Snapshot identities

Capture these before reading deeply:

```bash
base=$(git rev-parse HEAD)
index_tree=$(git write-tree)
git status --short
git diff --cached --stat
git diff --cached --check
```

Interpret status precisely:

- `M `: staged change only; ordinary checkout currently matches the index for that path.
- ` M`: unstaged change only; not part of the staged review.
- `MM`: staged and unstaged versions differ; ordinary checkout tests the wrong snapshot.

## Test the staged snapshot without touching the repository

Create a disposable directory from the recorded base, then apply the staged binary-safe patch:

```bash
tmp=$(mktemp -d /tmp/staged-review-XXXXXX)
git archive "$base" | tar -x -C "$tmp"
git diff --cached --binary | git -C "$tmp" apply
(
  cd "$tmp/path/to/component"
  <targeted test command>
  <lint/type/compile command>
)
rc=$?
rm -rf "$tmp"
exit "$rc"
```

Do not use `git apply --index` in an archive: the temporary directory is not a Git repository. Plain `git apply` is correct there.

If package tooling writes environments or caches, keep them inside the disposable tree or outside the reviewed checkout. Cleanup is part of the recipe, not a repository modification.

## Detect mid-review changes

A traceback whose source line and runtime object state appear impossible can mean the file changed while the process was importing or running. Before diagnosing application logic:

1. Re-run `git status --short`.
2. Re-read the exact cached hunk and live source.
3. Compare a fresh `git write-tree` with the recorded index tree.
4. If different, discard prior behavioral conclusions and re-run against the new snapshot.

## Patch committed during review

If the staged diff disappears and `HEAD` advances:

```bash
head_tree=$(git rev-parse HEAD^{tree})
git rev-parse HEAD
git status --short
```

- If `head_tree` equals the previously verified `index_tree`, the commit contains exactly the verified index snapshot.
- If it differs, inspect the final commit range and re-run verification on `HEAD`.
- Use the recorded base (`git diff "$base"..HEAD`) rather than assuming `HEAD^` is always the intended review base.

Final reporting must name the final verified tree/commit and must not cite test evidence from an obsolete snapshot.