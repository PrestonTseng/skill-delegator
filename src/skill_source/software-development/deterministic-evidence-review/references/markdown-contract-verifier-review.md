# Adversarial review of Markdown contract verifiers

Use this when a repository gate treats Markdown documents as executable evidence or state (briefs, decisions, completion reports, checklists, approval records).

## Governing rule

Validate rendered Markdown semantics, not a convenient subset of source syntax. A hand-written regex masker can reject known examples while still accepting render-equivalent contradictions.

## Reproduction matrix

Start from one valid completed document and mutate one property at a time in a temporary repository. Pair every hostile case with a valid control.

### Heading identity

Require semantic uniqueness after parsing through the repository's actual Markdown dialect. Probe:

- ATX headings with closing hashes and case variants.
- Inline emphasis: `## **Decision**`.
- Links: `## [Decision](https://example.test)`.
- HTML comments splitting text.
- Setext level-two headings.
- Headings inside fenced code and HTML comments as negative controls.

Compare normalized rendered inline text, not raw heading source. Confirm suspicious variants with a maintained CommonMark parser rather than asserting equivalence from memory.

### Structured field identity

Collect list items from the Markdown AST and normalize rendered labels before duplicate detection. Probe equivalent list markers and inline forms:

- `- Exit status: 0`
- `* Exit status: 1`
- `- **Exit status:** 1`
- `- Exit <!-- split -->status: 1`

Reject contradictory duplicate semantic labels regardless of marker or decoration.

### Exact command sections

Inspect every rendered code block and visible command-like entry in the governed section. Probe:

- backtick and tilde fences;
- language tags such as `sh`, `bash`, and `shell`;
- multiple blocks;
- additional visible commands outside the approved block;
- commented/fenced examples that should not execute.

An extractor that recognizes only one fence syntax cannot prove an exact command list.

### Evidence locators

For repository-confined evidence:

1. Canonicalize the repository root.
2. `lstat` each allowed top-level evidence root and reject symlinks before resolving it.
3. Prove every allowed root remains strictly within the repository root.
4. Reject child symlink escapes.
5. Distinguish a run directory from an artifact file.
6. Require contract-valid, non-empty evidence rather than bare `.exists()`.

Always test a symlinked allowed root separately from a symlinked child; guarding only the child misses root rebasing.

### Lifecycle and CI enforcement

Run both validation modes directly. Then mutate completion-only fields to invalid values and prove the CI-selected mode rejects them. If CI always invokes a setup phase, completion constraints are advisory even when the complete validator itself is correct. Use an explicit lifecycle marker or deterministic auto-detection so the integration gate selects the binding phase.

## Reporting

Record:

- exact HEAD/base and clean status;
- committed test counts;
- expected rejection of previously reported attacks;
- actual acceptance/rejection of fresh semantic variants;
- parser-render evidence for equivalence;
- separate Spec and Quality verdicts;
- an explicit integrate/do-not-integrate decision.

Keep probes outside the repository, remove temporary scripts afterward, and re-fingerprint HEAD/status before the verdict.
