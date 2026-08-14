"""Shared canonical identifier grammar for source-qualified skill paths."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

SOURCE_ID_PATTERN_TEXT = r"^[a-z][a-z0-9-]*$"
CANONICAL_SEGMENT_PATTERN_TEXT = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
CANONICAL_ID_PATTERN_TEXT = (
    r"^[a-z][a-z0-9-]*/[A-Za-z0-9][A-Za-z0-9._-]*"
    r"(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$"
)

_SOURCE_ID_PATTERN = re.compile(SOURCE_ID_PATTERN_TEXT)
_SEGMENT_PATTERN = re.compile(CANONICAL_SEGMENT_PATTERN_TEXT)
_CANONICAL_ID_PATTERN = re.compile(CANONICAL_ID_PATTERN_TEXT)


def is_source_id(value: str) -> bool:
    return _SOURCE_ID_PATTERN.fullmatch(value) is not None


def is_canonical_segment(value: str) -> bool:
    return _SEGMENT_PATTERN.fullmatch(value) is not None


def is_canonical_id(value: str) -> bool:
    return _CANONICAL_ID_PATTERN.fullmatch(value) is not None


def canonical_relative_path(value: PurePosixPath) -> bool:
    """Return whether a discovered/locked relative path uses canonical segments."""

    return (
        not value.is_absolute()
        and value != PurePosixPath(".")
        and bool(value.parts)
        and all(is_canonical_segment(part) for part in value.parts)
    )
