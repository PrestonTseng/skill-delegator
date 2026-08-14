"""Command-line interface for skill-delegator."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

import yaml

from skill_delegator.config import load_config
from skill_delegator.errors import ConfigError, SourceError
from skill_delegator.lockfile import build_lock, write_lock_atomic
from skill_delegator.models import DesiredState, LockedSkill, LockedSource, SkillLock
from skill_delegator.resolver import ResolutionError, resolve_desired_state
from skill_delegator.source_store import resolve_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillctl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate configuration without applying it")
    validate.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    lock = subparsers.add_parser("lock", help="resolve sources and atomically write the exact lock")
    lock.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    resolve = subparsers.add_parser(
        "resolve", help="resolve desired target state without applying it"
    )
    resolve.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    resolve.add_argument("--json", action="store_true", required=True)
    return parser


def _load_validated_lock(config_dir: Path) -> SkillLock:
    document = yaml.safe_load((config_dir / "skill-lock.yaml").read_text(encoding="utf-8"))
    return SkillLock(
        schema_version=document["schema_version"],
        sources=tuple(
            LockedSource(
                source_id=source["source_id"],
                source_type=source["type"],
                resolved_commit=source.get("resolved_commit"),
                tree_hash=source.get("tree_hash"),
                skills=tuple(
                    LockedSkill(
                        canonical_id=skill["canonical_id"],
                        runtime_name=skill["runtime_name"],
                        path=PurePosixPath(skill["path"]),
                        sha256=skill["sha256"],
                    )
                    for skill in source["skills"]
                ),
            )
            for source in document["sources"]
        ),
    )


def _desired_state_document(state: DesiredState) -> dict[str, object]:
    targets = state.targets
    return {
        "targets": [
            {
                "id": target.id,
                "root": str(target.root),
                "links": [
                    {
                        "artifact_id": link.artifact_id,
                        "runtime_name": link.runtime_name,
                        "source_path": link.source_path.as_posix(),
                        "target_path": str(link.target_path),
                        "content_sha256": link.content_sha256,
                    }
                    for link in target.links
                ],
            }
            for target in targets
        ]
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        try:
            config = load_config(args.config)
        except ConfigError as error:
            print(f"Configuration error: {error}", file=sys.stderr)
            return 2
        print(
            "Valid configuration: "
            f"1 authority, {len(config.sources)} source, "
            f"{len(config.pool)} pool entry, {len(config.targets)} targets"
        )
        return 0
    if args.command == "lock":
        try:
            config_dir = args.config.resolve(strict=False)
            config = load_config(config_dir, require_lock=False)
            cache_root = config_dir.parent / "var" / "cache" / "sources"
            resolved = resolve_sources(config, cache_root)
            lock = build_lock(config, resolved)
            write_lock_atomic(config_dir / "skill-lock.yaml", lock)
        except (ConfigError, SourceError) as error:
            print(f"Lock error: {error}", file=sys.stderr)
            return 2
        skill_count = sum(len(source.skills) for source in lock.sources)
        skill_word = "skill" if skill_count == 1 else "skills"
        source_word = "source" if len(lock.sources) == 1 else "sources"
        print(f"Locked {skill_count} {skill_word} from {len(lock.sources)} {source_word}")
        return 0
    if args.command == "resolve":
        try:
            config_dir = args.config.resolve(strict=False)
            config = load_config(config_dir)
            lock = _load_validated_lock(config_dir)
            state = resolve_desired_state(config, lock)
        except (ConfigError, OSError, ResolutionError) as error:
            print(f"Resolve error: {error}", file=sys.stderr)
            return 2
        print(json.dumps(_desired_state_document(state), sort_keys=True, separators=(",", ":")))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
