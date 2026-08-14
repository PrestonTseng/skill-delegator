"""Explicit, non-applying source update checks and candidate-lock proposals."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from skill_delegator.errors import SourceError, UpdateError
from skill_delegator.inventory import hash_tree
from skill_delegator.lockfile import build_lock
from skill_delegator.models import (
    ArtifactUpdate,
    AuthorityConfig,
    LockedSource,
    LockUpdateProposal,
    SkillLock,
    SourceSpec,
    SourceUpdate,
)
from skill_delegator.resolver import ResolutionError, resolve_desired_state
from skill_delegator.source_store import (
    _ensure_real_cache_directory,
    _run_git,
    _tracked_commit_ref,
    resolve_sources,
)

_HEX = frozenset("0123456789abcdef")


def _revision(source: LockedSource) -> str:
    revision = source.resolved_commit if source.source_type == "git" else source.tree_hash
    expected = 40 if source.source_type == "git" else 64
    if (
        revision is None
        or len(revision) != expected
        or any(character not in _HEX for character in revision)
        or (source.source_type == "git" and source.tree_hash is not None)
        or (source.source_type == "filesystem" and source.resolved_commit is not None)
    ):
        raise SourceError(f"invalid locked identity for source {source.source_id}")
    for skill in source.skills:
        if len(skill.sha256) != 64 or any(character not in _HEX for character in skill.sha256):
            raise SourceError(f"invalid locked identity for artifact {skill.canonical_id}")
    return revision


def _validated_old(config: AuthorityConfig, lock: SkillLock) -> dict[str, LockedSource]:
    if lock.schema_version != 1:
        raise SourceError("invalid locked schema version")
    try:
        resolve_desired_state(config, lock)
    except ResolutionError as error:
        raise SourceError(f"invalid old lock: {error}") from error
    result: dict[str, LockedSource] = {}
    for source in lock.sources:
        _revision(source)
        result[source.source_id] = source
    _require_complete_pool(config, lock, label="old lock")
    return result


def _require_complete_pool(config: AuthorityConfig, lock: SkillLock, *, label: str) -> None:
    locked = {skill.canonical_id for source in lock.sources for skill in source.skills}
    missing = sorted(item.canonical_id for item in config.pool if item.canonical_id not in locked)
    if missing:
        raise SourceError(f"{label} missing locked skill reference: {', '.join(missing)}")


def _cache_root(config: AuthorityConfig) -> Path:
    if config.cache_root is not None:
        return config.cache_root
    return Path(tempfile.gettempdir()) / "skill-delegator-update-cache"


def _git_candidate(source: SourceSpec, old_revision: str, cache_root: Path) -> tuple[str, str]:
    if not isinstance(source.location, str) or not source.track:
        raise SourceError(f"git source {source.id} requires string location and tracked ref")
    with _ensure_real_cache_directory(
        cache_root, description="update check cache root"
    ) as check_root:
        check_root.verify(description="update-check-cache")
        temporary = Path(tempfile.mkdtemp(prefix=".update-check-", dir=check_root.descriptor_path))
        checkout = temporary / "repository"
        try:
            _run_git(["clone", "--quiet", "--no-checkout", "--", source.location, str(checkout)])
            candidate = _run_git(
                [
                    "rev-parse",
                    "--verify",
                    "--end-of-options",
                    f"{_tracked_commit_ref(source.track)}^{{commit}}",
                ],
                cwd=checkout,
            )
            if candidate == old_revision:
                relation = "no-change"
            elif source.track.startswith("refs/tags/"):
                relation = "tag-moved"
            else:
                try:
                    _run_git(["cat-file", "-e", f"{old_revision}^{{commit}}"], cwd=checkout)
                except SourceError:
                    relation = "force-moved"
                else:
                    try:
                        _run_git(
                            ["merge-base", "--is-ancestor", old_revision, candidate],
                            cwd=checkout,
                        )
                    except SourceError:
                        relation = "diverged"
                    else:
                        relation = "fast-forward"
            check_root.verify(description="update-check-cache")
            return candidate, relation
        finally:
            shutil.rmtree(temporary, ignore_errors=True)


def check_updates(config: AuthorityConfig, lock: SkillLock) -> tuple[SourceUpdate, ...]:
    """Compare each mutable selector to its exact lock without approving or applying it."""

    old_by_id = _validated_old(config, lock)
    updates: list[SourceUpdate] = []
    for source in sorted(config.sources, key=lambda item: item.id):
        old = _revision(old_by_id[source.id])
        try:
            if source.type == "filesystem":
                if not isinstance(source.location, Path):
                    raise SourceError(f"filesystem source {source.id} location must be a Path")
                candidate = hash_tree(source.location)
                relation = "no-change" if candidate == old else "filesystem-moved"
            elif source.type == "git":
                candidate, relation = _git_candidate(source, old, _cache_root(config))
            else:
                raise SourceError(f"unsupported source type: {source.type}")
        except SourceError:
            candidate = None
            relation = "unavailable"
        updates.append(SourceUpdate(source.id, source.type, old, candidate, relation))
    return tuple(updates)


def _selected_lock(source: SourceSpec, config: AuthorityConfig) -> LockedSource:
    selected_config = replace(config, sources=(source,), pool=(), targets=())
    resolved = resolve_sources(selected_config, _cache_root(config))
    return build_lock(selected_config, resolved).sources[0]


def _prepare_update(
    source_id: str, config: AuthorityConfig, old_lock: SkillLock
) -> LockUpdateProposal:
    """Resolve and fully validate one selected source as an immutable lock proposal."""

    specs = {source.id: source for source in config.sources}
    if source_id not in specs:
        raise SourceError(f"unknown source: {source_id}")
    old_by_id = _validated_old(config, old_lock)
    old_source = old_by_id[source_id]
    selected_config = replace(config, sources=(specs[source_id],), pool=(), targets=())
    check = check_updates(selected_config, SkillLock(1, (old_source,)))[0]
    if check.new_revision is None:
        raise SourceError(f"source {source_id} is unavailable")
    exact_spec = (
        replace(specs[source_id], track=check.new_revision)
        if specs[source_id].type == "git"
        else specs[source_id]
    )
    new_source = _selected_lock(exact_spec, config)
    new_revision = _revision(new_source)
    if new_revision != check.new_revision:
        raise SourceError(f"source {source_id} changed while candidate was prepared")
    candidate = SkillLock(
        1,
        tuple(
            new_source if source.source_id == source_id else source for source in old_lock.sources
        ),
    )
    _require_complete_pool(config, candidate, label="candidate lock")
    try:
        resolve_desired_state(config, candidate)
    except ResolutionError as error:
        raise SourceError(f"candidate lock blocked: {error}") from error

    source_update = check
    old_skills = {item.canonical_id: item for item in old_source.skills}
    new_skills = {item.canonical_id: item for item in new_source.skills}
    relevant = {
        item.canonical_id for item in config.pool if item.canonical_id.startswith(f"{source_id}/")
    }
    artifacts: list[ArtifactUpdate] = []
    for canonical_id in sorted(relevant):
        old = old_skills.get(canonical_id)
        new = new_skills.get(canonical_id)
        status = (
            "added"
            if old is None
            else "removed"
            if new is None
            else ("unchanged" if old.sha256 == new.sha256 else "changed")
        )
        artifacts.append(
            ArtifactUpdate(
                canonical_id,
                old.sha256 if old else None,
                new.sha256 if new else None,
                status,
            )
        )
    ungranted = (set(new_skills) - set(old_skills)) - relevant
    removed = (set(old_skills) - set(new_skills)) - relevant
    return LockUpdateProposal(
        source_update,
        candidate,
        tuple(artifacts),
        tuple(sorted(ungranted)),
        tuple(sorted(removed)),
    )


def prepare_update(
    source_id: str, config: AuthorityConfig, old_lock: SkillLock
) -> LockUpdateProposal:
    """Prepare one update while translating internals to a bounded public error."""

    configured_ids = {source.id for source in config.sources}
    if source_id not in configured_ids:
        raise UpdateError("unknown source")
    try:
        return _prepare_update(source_id, config, old_lock)
    except UpdateError:
        raise
    except (SourceError, ResolutionError, OSError, UnicodeError, ValueError) as error:
        raise UpdateError(f"source {source_id} candidate-invalid") from error


def proposal_document(proposal: LockUpdateProposal) -> dict[str, object]:
    """Return bounded deterministic review data, excluding skill and source bodies."""

    return {
        "source": {
            "id": proposal.source.source_id,
            "type": proposal.source.source_type,
            "old_revision": proposal.source.old_revision,
            "new_revision": proposal.source.new_revision,
            "relation": proposal.source.relation,
        },
        "artifacts": [
            {
                "canonical_id": item.canonical_id,
                "old_sha256": item.old_sha256,
                "new_sha256": item.new_sha256,
                "status": item.status,
            }
            for item in proposal.artifacts
        ],
        "new_ungranted": list(proposal.new_ungranted),
        "removed_ungranted": list(proposal.removed_ungranted),
    }


def proposal_json(proposal: LockUpdateProposal) -> str:
    return json.dumps(proposal_document(proposal), sort_keys=True, separators=(",", ":")) + "\n"


def proposal_text(proposal: LockUpdateProposal) -> str:
    source = proposal.source
    lines = [
        f"source {source.source_id}: {source.relation}",
        f"  old: {source.old_revision}",
        f"  new: {source.new_revision or '-'}",
    ]
    for item in proposal.artifacts:
        lines.append(
            f"  {item.status} {item.canonical_id}: {item.old_sha256 or '-'} -> {item.new_sha256 or '-'}"
        )
    for canonical_id in proposal.new_ungranted:
        lines.append(f"  new-ungranted {canonical_id}")
    for canonical_id in proposal.removed_ungranted:
        lines.append(f"  removed-ungranted {canonical_id}")
    return "\n".join(lines) + "\n"
