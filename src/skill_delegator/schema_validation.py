"""Shared loading and deterministic validation of bundled JSON schemas."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def schema_text(schema_name: str) -> str:
    """Read a schema from the source tree or the installed package."""

    repository_schema = Path(__file__).parents[2] / "schemas" / schema_name
    if repository_schema.is_file():
        return repository_schema.read_text(encoding="utf-8")
    packaged_schema = files("skill_delegator").joinpath("schemas", schema_name)
    return packaged_schema.read_text(encoding="utf-8")


def schema_errors(document: Any, schema_name: str) -> tuple[ValidationError, ...]:
    """Return schema errors in a stable order independent of traversal details."""

    schema = json.loads(schema_text(schema_name))
    return tuple(
        sorted(
            Draft202012Validator(schema).iter_errors(document),
            key=lambda error: (
                tuple(str(part) for part in error.absolute_path),
                tuple(str(part) for part in error.absolute_schema_path),
                str(error.validator),
            ),
        )
    )


def schema_error_location(error: ValidationError) -> str:
    """Render only the bounded structural location of a validation error."""

    return ".".join(str(part) for part in error.absolute_path) or "$"
