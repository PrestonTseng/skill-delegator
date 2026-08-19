---
name: safeart-deployment-changelog
description: Create dependency-facing SafeART/TAPAS deployment changelogs from git commits across service repos such as Crystal, Unicorn, and Thalos.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# SafeART Deployment Changelog

Use this skill when the user asks to prepare a changelog from git commits for a SafeART / TAPAS deployment, especially for other teams that depend on one or more services.

This skill is for **dependency-facing deployment changelogs**, not formal SafeART release notes. The changelog should explain what other teams need to know: API contracts, subscriptions, config, behavior, build/runtime changes, and operational integration impact.

## Trigger examples

- "我要部署 crystal, unicorn, thalos 的 0.21b3 到 alpha，可以幫我從 git commit 整理 changelog 嗎"
- "Summarize changes between SafeART tags for dependency teams"
- "Prepare an integration-impact changelog for Alpha deployment"
- "What should ACES / frontend / monitoring teams know from these commits?"

## Non-goals

Do not turn this into a formal release note unless the user asks for release-note authoring. For formal Confluence release notes, use `safeart-release-note-authoring` and its ADF/source-of-truth workflow.

Do not invent:

- QA pass/fail status,
- release approval,
- deployment readiness,
- known issue cohort,
- customer-facing release claims,
- Jira status beyond what was actually fetched or provided.

A git changelog can say what changed in code. It cannot prove release quality by itself.

## Workflow

### 1. Establish the source range

Default beta-to-beta deployment comparison:

```bash
git log safeart-<previous>..safeart-<target>
```

Examples:

- `safeart-0.21b2..safeart-0.21b3`
- `safeart-0.20b3..safeart-0.21b1`

Verify the tags exist in every target repo before summarizing. If a repo is missing the tag, say so directly and ask whether to use a branch/ref instead.

### 2. Fetch tags and refs

When normal Gerrit fetch uses the wrong SSH identity, use the shared Gerrit key pattern from `references/release-git-changelog.md`.

Do not encode transient SSH failure as a durable limitation. The reusable lesson is the fetch pattern.

### 3. Extract commit and file evidence

For each repo, collect:

```bash
git rev-parse --short safeart-<previous>
git rev-parse --short safeart-<target>
git log --reverse --date=short --pretty=format:'%h%x09%ad%x09%an%x09%s%d%n%b%n---ENDCOMMIT---' safeart-<previous>..safeart-<target>
git diff --stat safeart-<previous>..safeart-<target>
git diff --name-status safeart-<previous>..safeart-<target>
```

Then inspect actual diffs for files that imply dependency impact.

### 4. Filter for dependency impact

Prioritize:

- GraphQL / REST schema changes,
- subscription names, event shapes, replay/coalescing semantics,
- HTTP status/error contract changes,
- config flags and default changes,
- Docker/build/runtime toolchain changes,
- MQTT/ICD-facing behavior,
- route/mission/MA/TSR behavior changes,
- WSS/ADS-facing behavior,
- logs/metrics/events useful for another team's debugging.

De-emphasize:

- test-only changes,
- formatting,
- internal refactors with no integration effect,
- broad implementation detail that a dependency team cannot act on.

### 5. Group by service

Recommended grouping:

- **Crystal** — frontend behavior and backend API assumptions it now relies on.
- **Unicorn** — GraphQL/REST/subscription/config/build/runtime behavior consumed by Crystal or other services.
- **Thalos / Safety Server** — REST contract changes, route/mission/MA/TSR behavior, WSS/ADS-facing effects.

For each material item, include:

- ticket ID / commit ID,
- short description,
- concrete behavior or contract change,
- `Dependency impact:` line.

### 6. Format for Discord

Discord does not render markdown tables reliably. Use:

- short source/range section,
- bold service headers,
- bullets with ticket IDs,
- `Dependency impact:` lines,
- optional raw commit list at the end.

Avoid markdown table syntax.

## Verification checklist

Before final response:

- Tags/ranges verified in every repo.
- Commit counts match `git rev-list --count`.
- Each dependency claim is backed by commit message or inspected diff.
- Output distinguishes code-derived facts from inferred impact.
- Discord formatting avoids markdown tables.
- Task artifacts, if created, are saved under `/opt/data/plans/YYYY-MM-DD-<task-slug>/`.

## References

- `references/release-git-changelog.md` — detailed command pattern and impact-classification notes from a Crystal/Unicorn/Thalos 0.21b3 Alpha changelog session.
