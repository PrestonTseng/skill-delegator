#!/usr/bin/env python3
"""Validate an XLSX package for ZIP/XML integrity and worksheet namespace safety.

Usage:
    python validate_ooxml_namespaces.py workbook.xlsx [workbook2.xlsx ...]

This catches the corruption pattern where a generic XML serializer removes
namespace declarations but leaves their prefixes in mc:Ignorable.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                errors.append(f"ZIP CRC failure: {bad_member}")

            for name in archive.namelist():
                if not name.endswith((".xml", ".rels")):
                    continue
                raw = archive.read(name)
                try:
                    ET.fromstring(raw)
                except ET.ParseError as exc:
                    errors.append(f"XML parse failure in {name}: {exc}")
                    continue

                if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                    continue
                text = raw.decode("utf-8", "replace")
                root_match = re.search(r"<worksheet\b[^>]*>", text, re.S)
                if not root_match:
                    errors.append(f"Missing worksheet root start tag in {name}")
                    continue
                root = root_match.group(0)
                declared = set(
                    re.findall(r"xmlns:([A-Za-z_][A-Za-z0-9_.-]*)\s*=", root)
                )
                ignorable = re.search(
                    r'\b(?:[A-Za-z_][A-Za-z0-9_.-]*:)?Ignorable="([^"]*)"',
                    root,
                )
                if ignorable:
                    missing = [
                        prefix
                        for prefix in ignorable.group(1).split()
                        if prefix not in declared
                    ]
                    if missing:
                        errors.append(
                            f"{name}: mc:Ignorable references undeclared prefixes: "
                            + ", ".join(missing)
                        )
    except (BadZipFile, OSError) as exc:
        errors.append(f"Cannot open XLSX package: {exc}")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate_ooxml_namespaces.py workbook.xlsx [workbook2.xlsx ...]", file=sys.stderr)
        return 2

    failed = False
    for arg in sys.argv[1:]:
        path = Path(arg)
        errors = validate(path)
        if errors:
            failed = True
            print(f"FAIL {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
