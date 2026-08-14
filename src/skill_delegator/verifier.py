"""Independent, fresh verification of delegated target and source state."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import replace
from pathlib import Path, PurePosixPath

from skill_delegator.errors import SourceError
from skill_delegator.inventory import hash_tree, inspect_skill
from skill_delegator.managed_state import TargetStateError, scan_target, target_fingerprint
from skill_delegator.models import (
    AuthorityConfig,
    ConfigFileHash,
    CurrentState,
    DesiredLink,
    DesiredState,
    LockedSourceIdentity,
    OperationSummary,
    SkillLock,
    TargetFingerprint,
    TargetSpec,
    VerificationReason,
    VerificationResult,
)

_DRIFT_SCAN_ERRORS = (
    ("managed link is missing:", "managed-link-missing"),
    ("broken managed link:", "managed-link-broken"),
    ("managed link does not match manager metadata:", "managed-link-wrong"),
    ("managed entry is not a symlink:", "managed-link-wrong"),
)


def _reason(
    code: str,
    category: str,
    target_id: str | None,
    artifact_id: str | None,
    detail: str,
) -> VerificationReason:
    return VerificationReason(code, category, target_id, artifact_id, detail[:300])


def _failure_fingerprint(target_id: str, root: Path) -> str:
    """Fingerprint lexical target state even when strict managed scanning rejects it."""

    digest = hashlib.sha256()
    digest.update(target_id.encode("utf-8", "backslashreplace"))
    digest.update(os.fsencode(root))
    try:
        root_metadata = root.lstat()
    except FileNotFoundError:
        digest.update(b"absent")
        return digest.hexdigest()
    except OSError:
        digest.update(b"unreadable")
        return digest.hexdigest()
    digest.update(str(stat.S_IFMT(root_metadata.st_mode)).encode())
    if stat.S_ISLNK(root_metadata.st_mode):
        try:
            digest.update(os.fsencode(os.readlink(root)))
        except OSError:
            digest.update(b"unreadable-link")
        return digest.hexdigest()
    if not stat.S_ISDIR(root_metadata.st_mode):
        return digest.hexdigest()
    try:
        for directory, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames.sort(key=os.fsencode)
            filenames.sort(key=os.fsencode)
            for name in (*dirnames, *filenames):
                path = Path(directory) / name
                relative = path.relative_to(root)
                digest.update(os.fsencode(relative))
                metadata = path.lstat()
                digest.update(str(stat.S_IFMT(metadata.st_mode)).encode())
                if stat.S_ISLNK(metadata.st_mode):
                    digest.update(os.fsencode(os.readlink(path)))
                elif stat.S_ISREG(metadata.st_mode):
                    file_digest = hashlib.sha256()
                    with path.open("rb") as stream:
                        while chunk := stream.read(1024 * 1024):
                            file_digest.update(chunk)
                    digest.update(file_digest.digest())
    except OSError:
        digest.update(b"scan-error")
    return digest.hexdigest()


def _lexical_real_directory(path: Path, cache_root: Path) -> bool:
    if not path.is_absolute() or path == cache_root or not path.is_relative_to(cache_root):
        return False
    current = Path(path.anchor)
    try:
        for part in path.parts[1:]:
            current /= part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                return False
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def _expected_relative(target_root: Path, link: DesiredLink) -> PurePosixPath | None:
    try:
        relative = link.target_path.relative_to(target_root)
    except ValueError:
        return None
    candidate = PurePosixPath(relative.as_posix())
    artifact = PurePosixPath(link.artifact_id)
    if (
        candidate != artifact
        or candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        return None
    return candidate


def _scan_error_reason(target_id: str, error: TargetStateError) -> VerificationReason:
    text = str(error)
    for prefix, code in _DRIFT_SCAN_ERRORS:
        if text.startswith(prefix):
            return _reason(code, "drift", target_id, None, code.replace("-", " "))
    return _reason(
        "target-state-invalid",
        "invalid",
        target_id,
        None,
        "target state is malformed, ambiguous, or unsafe",
    )


def verify_state(desired: DesiredState, current: CurrentState) -> VerificationResult:
    """Freshly verify exact desired links and source evidence.

    ``current.targets`` is deliberately ignored: it may be a stale planning object. Only
    its exact cache authority is used; every target is scanned again from the desired roots.
    """

    reasons: list[VerificationReason] = []
    fingerprints: list[TargetFingerprint] = []
    desired_links = sum(len(target.links) for target in desired.targets)
    verified_links = 0
    cache_root = current.expected_cache_root
    if cache_root is None or not cache_root.is_absolute():
        reasons.append(
            _reason(
                "cache-authority-invalid",
                "invalid",
                None,
                None,
                "exact absolute cache authority is required",
            )
        )

    seen_target_ids: set[str] = set()
    for target in sorted(desired.targets, key=lambda item: item.id):
        if target.id in seen_target_ids:
            reasons.append(
                _reason(
                    "duplicate-target-id",
                    "invalid",
                    target.id,
                    None,
                    "desired target identifiers must be unique",
                )
            )
            continue
        seen_target_ids.add(target.id)

        expected: dict[str, DesiredLink] = {}
        source_artifacts = {}
        source_clean: dict[str, bool] = {}
        runtime_names: dict[str, str] = {}
        for link in sorted(target.links, key=lambda item: item.artifact_id):
            if link.artifact_id in expected:
                reasons.append(
                    _reason(
                        "duplicate-desired-artifact",
                        "invalid",
                        target.id,
                        link.artifact_id,
                        "desired artifact identifiers must be unique",
                    )
                )
            expected[link.artifact_id] = link
            source = link.expected_source_path
            before_source = len(reasons)
            if (
                cache_root is None
                or source is None
                or not _lexical_real_directory(source, cache_root)
            ):
                reasons.append(
                    _reason(
                        "source-state-invalid",
                        "invalid",
                        target.id,
                        link.artifact_id,
                        "expected source is absent, symlinked, or outside the exact cache",
                    )
                )
                source_clean[link.artifact_id] = False
                continue
            try:
                actual_hash = hash_tree(source)
                artifact = inspect_skill(source)
            except (OSError, SourceError):
                reasons.append(
                    _reason(
                        "source-state-invalid",
                        "invalid",
                        target.id,
                        link.artifact_id,
                        "source tree or skill metadata is invalid",
                    )
                )
                source_clean[link.artifact_id] = False
                continue
            source_artifacts[link.artifact_id] = artifact
            if actual_hash != link.content_sha256:
                reasons.append(
                    _reason(
                        "source-content-hash-mismatch",
                        "drift",
                        target.id,
                        link.artifact_id,
                        "fresh source tree hash differs from exact lock",
                    )
                )
            if artifact.runtime_name != link.runtime_name:
                reasons.append(
                    _reason(
                        "runtime-name-mismatch",
                        "drift",
                        target.id,
                        link.artifact_id,
                        "fresh source runtime name differs from exact lock",
                    )
                )
            previous = runtime_names.get(artifact.runtime_name)
            if previous is not None and previous != link.artifact_id:
                reasons.append(
                    _reason(
                        "runtime-name-collision",
                        "drift",
                        target.id,
                        link.artifact_id,
                        "fresh source metadata has a duplicate runtime name",
                    )
                )
                source_clean[previous] = False
            runtime_names[artifact.runtime_name] = link.artifact_id
            source_clean[link.artifact_id] = len(reasons) == before_source

        try:
            fresh = scan_target(TargetSpec(target.id, target.root, ()))
        except TargetStateError as error:
            reasons.append(_scan_error_reason(target.id, error))
            fingerprints.append(
                TargetFingerprint(target.id, _failure_fingerprint(target.id, target.root))
            )
            continue

        fingerprints.append(TargetFingerprint(target.id, target_fingerprint(fresh)))
        if cache_root is None:
            continue
        target_issue = False
        if fresh.cache_root is not None and fresh.cache_root != cache_root:
            reasons.append(
                _reason(
                    "cache-root-mismatch",
                    "invalid",
                    target.id,
                    None,
                    "managed metadata names a different cache authority",
                )
            )
            target_issue = True

        actual = {entry.artifact_id: entry for entry in fresh.managed}
        for artifact_id in sorted(set(expected) - set(actual)):
            reasons.append(
                _reason(
                    "missing-managed-entry",
                    "drift",
                    target.id,
                    artifact_id,
                    "expected manager-owned entry is absent",
                )
            )
        for artifact_id in sorted(set(actual) - set(expected)):
            reasons.append(
                _reason(
                    "unexpected-managed-entry",
                    "drift",
                    target.id,
                    artifact_id,
                    "manager-owned entry is not desired",
                )
            )

        for artifact_id in sorted(set(expected) & set(actual)):
            link = expected[artifact_id]
            entry = actual[artifact_id]
            before = len(reasons)
            relative = _expected_relative(target.root, link)
            if relative is None or entry.relative_path != relative:
                reasons.append(
                    _reason(
                        "target-path-invalid",
                        "invalid",
                        target.id,
                        artifact_id,
                        "desired target path is not lexically confined",
                    )
                )
            source = link.expected_source_path
            if source is None or artifact_id not in source_artifacts:
                continue
            raw_target = entry.raw_link_target
            if raw_target is None:
                reasons.append(
                    _reason(
                        "managed-link-wrong",
                        "drift",
                        target.id,
                        artifact_id,
                        "managed link has no lexical destination",
                    )
                )
            else:
                raw = Path(raw_target)
                resolved_raw = raw if raw.is_absolute() else link.target_path.parent / raw
                resolved_raw = Path(os.path.abspath(resolved_raw))
                if (
                    resolved_raw != source
                    or resolved_raw == cache_root
                    or not resolved_raw.is_relative_to(cache_root)
                ):
                    reasons.append(
                        _reason(
                            "managed-link-wrong",
                            "drift",
                            target.id,
                            artifact_id,
                            "managed link destination differs from exact confined source",
                        )
                    )
            if entry.source_path != source or entry.content_sha256 != link.content_sha256:
                reasons.append(
                    _reason(
                        "managed-metadata-mismatch",
                        "drift",
                        target.id,
                        artifact_id,
                        "manager metadata differs from desired lock evidence",
                    )
                )
            if not target_issue and source_clean.get(artifact_id, False) and len(reasons) == before:
                verified_links += 1

    reasons_tuple = tuple(
        sorted(
            set(reasons),
            key=lambda item: (
                item.target_id or "",
                item.artifact_id or "",
                item.category,
                item.code,
                item.detail,
            ),
        )
    )
    invalid_count = sum(reason.category == "invalid" for reason in reasons_tuple)
    drift_count = sum(reason.category == "drift" for reason in reasons_tuple)
    outcome = "invalid" if invalid_count else "drift" if drift_count else "converged"
    return VerificationResult(
        outcome,
        reasons_tuple,
        tuple(sorted(fingerprints, key=lambda item: item.target_id)),
        OperationSummary(
            len(desired.targets), desired_links, verified_links, drift_count, invalid_count
        ),
    )


_CONFIG_INPUTS = (
    "authority.yaml",
    "delegations.yaml",
    "pool.yaml",
    "skill-lock.yaml",
    "sources.yaml",
)
_MAX_CONFIG_BYTES = 16 * 1024 * 1024


def _read_config_input(config_dir: Path, name: str) -> bytes:
    """Read one lexical regular input through a bounded no-follow descriptor."""

    path = Path(os.path.abspath(config_dir / name))
    current = Path(path.anchor)
    try:
        for part in path.parts[1:-1]:
            current /= part
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(f"config input is not beneath lexical directories: {name}")
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"config input must be a lexical regular file: {name}")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ):
                raise ValueError(f"config input identity changed during read: {name}")
            chunks: list[bytes] = []
            remaining = _MAX_CONFIG_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            payload = b"".join(chunks)
            if len(payload) > _MAX_CONFIG_BYTES:
                raise ValueError(f"config input exceeds safe read limit: {name}")
            after = os.fstat(descriptor)
            if (after.st_dev, after.st_ino, after.st_size) != (
                opened.st_dev,
                opened.st_ino,
                len(payload),
            ):
                raise ValueError(f"config input changed during read: {name}")
            return payload
        finally:
            os.close(descriptor)
    except ValueError:
        raise
    except OSError as error:
        raise ValueError(f"cannot safely read config input: {name}") from error


def _repository_commit(
    config_dir: Path, current_inputs: dict[str, bytes]
) -> tuple[str | None, bool]:
    """Return HEAD only when its ordinary blobs equal every current input byte-for-byte."""

    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        root_result = subprocess.run(
            ["git", "-C", str(config_dir), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError):
        return None, False
    if root_result.returncode != 0:
        return None, False
    repository_root = Path(root_result.stdout.strip())
    try:
        config_relative = config_dir.relative_to(repository_root)
    except ValueError:
        return None, False
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", "--verify", "HEAD^{commit}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError):
        return None, False
    commit = completed.stdout.strip()
    if completed.returncode != 0 or len(commit) not in range(40, 65):
        return None, False
    if any(character not in "0123456789abcdef" for character in commit):
        return None, False
    for name in _CONFIG_INPUTS:
        relative = (config_relative / name).as_posix()
        try:
            entry = subprocess.run(
                ["git", "-C", str(repository_root), "ls-tree", "-z", commit, "--", relative],
                check=False,
                capture_output=True,
                timeout=2,
                env=environment,
            )
            blob = subprocess.run(
                ["git", "-C", str(repository_root), "cat-file", "blob", f"{commit}:{relative}"],
                check=False,
                capture_output=True,
                timeout=2,
                env=environment,
            )
        except (OSError, subprocess.SubprocessError):
            return None, False
        records = entry.stdout.rstrip(b"\0").split(b"\0") if entry.stdout else []
        if entry.returncode != 0 or len(records) != 1:
            return None, False
        header, separator, recorded_path = records[0].partition(b"\t")
        fields = header.split()
        if (
            not separator
            or len(fields) != 3
            or fields[0] not in {b"100644", b"100755"}
            or fields[1] != b"blob"
            or os.fsdecode(recorded_path) != relative
            or blob.returncode != 0
            or blob.stdout != current_inputs[name]
        ):
            return None, False
    return commit, True


def bind_verification_evidence(
    result: VerificationResult,
    config_dir: Path,
    config: AuthorityConfig,
    lock: SkillLock,
) -> VerificationResult:
    """Bind byte, repository, authority, and exact-lock identities to a result."""

    config_dir = Path(os.path.abspath(config_dir))
    current_inputs = {name: _read_config_input(config_dir, name) for name in _CONFIG_INPUTS}
    hashes = tuple(
        ConfigFileHash(name, hashlib.sha256(current_inputs[name]).hexdigest())
        for name in _CONFIG_INPUTS
    )
    locked_sources: list[LockedSourceIdentity] = []
    for source in sorted(lock.sources, key=lambda item: item.source_id):
        if source.resolved_commit is not None:
            kind = "resolved_commit"
            revision = source.resolved_commit
            tree_identity = None
        elif source.tree_hash is not None:
            kind = "tree_hash"
            revision = source.tree_hash
            tree_identity = source.tree_hash
        else:
            raise ValueError(f"locked source has no immutable identity: {source.source_id}")
        locked_sources.append(
            LockedSourceIdentity(
                source.source_id,
                source.source_type,
                kind,
                revision,
                tree_identity,
            )
        )
    commit, available = _repository_commit(config_dir, current_inputs)
    return replace(
        result,
        authority_id=config.authority_id,
        repository_commit=commit,
        repository_commit_available=available,
        config_hashes=hashes,
        locked_sources=tuple(locked_sources),
    )
