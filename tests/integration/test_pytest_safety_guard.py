from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]


def test_repository_conftest_has_no_branch_specific_startup_rejection() -> None:
    tree = ast.parse((REPOSITORY_ROOT / "conftest.py").read_text(encoding="utf-8"))

    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "pytest_sessionstart" not in function_names
