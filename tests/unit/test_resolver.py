from __future__ import annotations

from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

from skill_delegator.models import (
    AuthorityConfig,
    LockedSkill,
    LockedSource,
    PoolSpec,
    SkillLock,
    SourceSpec,
    TargetSpec,
)
from skill_delegator.resolver import ResolutionError, resolve_desired_state

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def skill(artifact_id: str, runtime_name: str, path: str, sha: str = _SHA_A) -> LockedSkill:
    return LockedSkill(artifact_id, runtime_name, PurePosixPath(path), sha)


def source(source_id: str, *skills: LockedSkill) -> LockedSource:
    return LockedSource(source_id, "filesystem", None, "f" * 64, skills)


def config(
    tmp_path: Path,
    *,
    pool: tuple[str, ...],
    targets: tuple[TargetSpec, ...],
) -> AuthorityConfig:
    source_ids = sorted({item.split("/", 1)[0] for item in pool})
    return AuthorityConfig(
        "authority",
        True,
        "none",
        tuple(
            SourceSpec(item, "filesystem", tmp_path / item, PurePosixPath("."))
            for item in source_ids
        ),
        tuple(PoolSpec(item) for item in pool),
        targets,
    )


def test_resolves_valid_subset_with_exact_desired_link_fields(tmp_path: Path) -> None:
    target = TargetSpec("worker", tmp_path / "target", ("alpha/nested/tool",))
    authority = config(
        tmp_path,
        pool=("alpha/nested/tool", "alpha/unused"),
        targets=(target,),
    )
    lock = SkillLock(
        1,
        (source("alpha", skill("alpha/nested/tool", "tool", "nested/tool")),),
    )

    state = resolve_desired_state(authority, lock)

    assert state.targets[0].id == "worker"
    assert state.targets[0].root == target.root
    assert state.targets[0].links[0].artifact_id == "alpha/nested/tool"
    assert state.targets[0].links[0].runtime_name == "tool"
    assert state.targets[0].links[0].source_path == PurePosixPath("nested/tool")
    assert state.targets[0].links[0].target_path == target.root / "alpha/nested/tool"
    assert state.targets[0].links[0].content_sha256 == _SHA_A


def test_empty_targets_and_empty_target_grants_are_valid(tmp_path: Path) -> None:
    empty_authority = config(tmp_path, pool=(), targets=())
    assert resolve_desired_state(empty_authority, SkillLock(1, ())).targets == ()

    target = TargetSpec("empty", tmp_path / "empty", ())
    state = resolve_desired_state(config(tmp_path, pool=(), targets=(target,)), SkillLock(1, ()))
    assert state.targets[0].links == ()


def test_output_order_is_independent_of_input_order(tmp_path: Path) -> None:
    z = TargetSpec("z-target", tmp_path / "z", ("beta/z", "alpha/a"))
    a = TargetSpec("a-target", tmp_path / "a", ("beta/z",))
    authority = config(tmp_path, pool=("beta/z", "alpha/a"), targets=(z, a))
    lock = SkillLock(
        1,
        (
            source("beta", skill("beta/z", "z", "z", _SHA_B)),
            source("alpha", skill("alpha/a", "a", "a", _SHA_A)),
        ),
    )

    first = resolve_desired_state(authority, lock)
    second = resolve_desired_state(
        replace(
            authority,
            pool=tuple(reversed(authority.pool)),
            targets=tuple(reversed(authority.targets)),
        ),
        replace(lock, sources=tuple(reversed(lock.sources))),
    )

    assert first == second
    assert tuple(target.id for target in first.targets) == ("a-target", "z-target")
    assert tuple(link.artifact_id for link in first.targets[1].links) == ("alpha/a", "beta/z")


def test_rejects_configured_and_locked_source_set_mismatch_deterministically(
    tmp_path: Path,
) -> None:
    authority = AuthorityConfig(
        "authority",
        True,
        "none",
        (
            SourceSpec("alpha", "filesystem", tmp_path / "alpha", PurePosixPath(".")),
            SourceSpec("beta", "filesystem", tmp_path / "beta", PurePosixPath(".")),
        ),
        (),
        (),
    )
    lock = SkillLock(1, (source("gamma"), source("alpha")))

    with pytest.raises(
        ResolutionError,
        match=r"locked source set differs from configuration: missing=\['beta'\], extra=\['gamma'\]",
    ):
        resolve_desired_state(authority, lock)


def test_rejects_locked_source_type_mismatch(tmp_path: Path) -> None:
    authority = config(tmp_path, pool=("alpha/tool",), targets=())
    lock = SkillLock(
        1,
        (
            LockedSource(
                "alpha",
                "git",
                "f" * 40,
                None,
                (skill("alpha/tool", "tool", "tool"),),
            ),
        ),
    )

    with pytest.raises(
        ResolutionError,
        match="locked source alpha type 'git' does not match configured type 'filesystem'",
    ):
        resolve_desired_state(authority, lock)


@pytest.mark.parametrize(
    ("artifact_id", "path", "message"),
    (
        ("evil/tool", "tool", "artifact evil/tool is enclosed by source alpha"),
        ("alpha/", "tool", "artifact alpha/ has invalid canonical source prefix or suffix"),
        ("alpha/tool", "../tool", "locked path ../tool is outside configured skill root skills"),
        (
            "alpha/tool",
            "skills/different",
            "locked path skills/different does not match canonical suffix tool",
        ),
    ),
)
def test_rejects_artifact_authority_and_path_binding_mismatches(
    tmp_path: Path, artifact_id: str, path: str, message: str
) -> None:
    authority = AuthorityConfig(
        "authority",
        True,
        "none",
        (SourceSpec("alpha", "filesystem", tmp_path / "alpha", PurePosixPath("skills")),),
        (),
        (),
    )
    lock = SkillLock(1, (source("alpha", skill(artifact_id, "tool", path)),))

    with pytest.raises(ResolutionError, match=message):
        resolve_desired_state(authority, lock)
