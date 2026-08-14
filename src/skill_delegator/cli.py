"""Command-line interface for skill-delegator."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from skill_delegator.config import load_config
from skill_delegator.errors import ConfigError, SourceError
from skill_delegator.lockfile import build_lock, write_lock_atomic
from skill_delegator.source_store import resolve_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillctl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate configuration without applying it")
    validate.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    lock = subparsers.add_parser("lock", help="resolve sources and atomically write the exact lock")
    lock.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    return parser


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
            config = load_config(config_dir)
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
