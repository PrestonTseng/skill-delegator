"""Command-line interface for skill-delegator."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from skill_delegator.config import load_config
from skill_delegator.errors import ConfigError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillctl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate configuration without applying it")
    validate.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
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
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
