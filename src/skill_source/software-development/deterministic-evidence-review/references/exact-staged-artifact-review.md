# Exact staged-artifact review

Use this for pre-commit evidence reviews when staged and unstaged content overlap, ignored fixtures are required, Docker/build tooling reads the working tree, or another process may update the index.

## 1. Give the index an immutable identity

```bash
review_tree="$(git write-tree)"
git diff --cached --check
```

A later `git diff --cached` may describe a different artifact if another agent, hook, or user restages files. Record the tree hash with the review evidence.

## 2. Do not execute the working tree by mistake

Repository commands normally read working-tree files, not index blobs. If `git status --short` shows overlapping staged/unstaged states such as `MM` or `AM`, a passing run in the repository does not verify the staged artifact.

Materialize the index into an isolated temporary directory:

```bash
review_root="$(mktemp -d /path/visible/to/runtime/staged-review.XXXXXX)"
trap 'rm -rf "$review_root"' EXIT
git checkout-index --all --prefix="$review_root/"
```

Choose a root visible to Docker or any sibling runtime. Copy only the approved ignored fixtures needed for reproduction. Run the full build/test/evidence command from `review_root`, verify runtime cleanup, then remove the temporary tree.

## 3. Detect concurrent mutation

After execution:

```bash
after_tree="$(git write-tree)"
test "$after_tree" = "$review_tree"
```

If the tree changed, discard stale conclusions, inspect the new diff, and rerun. Never combine source review from one tree with test evidence from another.

If the index becomes empty because the change was committed during review, compare:

```bash
git rev-parse 'HEAD^{tree}'
```

When it equals `review_tree`, the execution still grounds that exact commit. Report the concurrent commit and identify both commit and tree.

## 4. Probe validator failure semantics

Evidence-producing validators need malformed-metadata probes, not only a valid fixture. JavaScript numeric comparisons commonly false-pass on `NaN`:

- require `Number.isFinite()` before ordering or tolerance comparisons;
- require positive source and output durations before arithmetic;
- reject missing packet timestamps before monotonicity checks;
- distinguish “the command requested CFR” from “output cadence proves CFR.”

A happy-path media output can be valid while its acceptance validator remains fail-open.