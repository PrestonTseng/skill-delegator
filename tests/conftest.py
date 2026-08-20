"""Repository-wide pytest configuration and mutation-safety collection gate.

Checked-out configuration is validated by a read-only integration test. Mutation-capable tests
must instead use the confined helpers in :mod:`tests.fixture_safety`.
"""

from pathlib import Path

import pytest

from tests.fixture_safety import mutation_policy_violations

REPOSITORY_ROOT = Path(__file__).parent.parent
POLICY_TEST = REPOSITORY_ROOT / "tests" / "unit" / "test_fixture_safety.py"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Fail collection before a forbidden mutation-capable test body can execute."""
    violations: list[str] = []
    for path in sorted({Path(item.path) for item in items}):
        if path == POLICY_TEST:
            continue
        violations.extend(mutation_policy_violations(path, REPOSITORY_ROOT))
    if violations:
        pytest.exit("mutation-safety policy:\n" + "\n".join(violations), returncode=4)
