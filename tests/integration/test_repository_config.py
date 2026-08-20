from pathlib import Path

from skill_delegator.config import load_config

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_checked_out_repository_config_validates() -> None:
    load_config(REPOSITORY_ROOT / "config")
