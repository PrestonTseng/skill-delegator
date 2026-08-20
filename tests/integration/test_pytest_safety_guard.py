from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_mutation_safety_conftest_is_scoped_to_tests() -> None:
    assert not (REPOSITORY_ROOT / "conftest.py").exists()
    conftest = REPOSITORY_ROOT / "tests" / "conftest.py"
    tree = ast.parse(conftest.read_text(encoding="utf-8"))

    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "pytest_sessionstart" not in function_names
    assert "pytest_collection_modifyitems" in function_names
