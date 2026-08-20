from __future__ import annotations

import json
import subprocess
import tarfile
import zipfile
from pathlib import Path


def test_release_artifact_bytes_match_source_wheel_and_sdist(tmp_path: Path) -> None:
    project = Path(__file__).parents[2]
    dist = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--out-dir", str(dist)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(dist.glob("*.whl"))
    sdist = next(dist.glob("*.tar.gz"))
    schemas = sorted((project / "schemas").glob("*.schema.json"))
    assert project / "schemas" / "target-delegation.schema.json" in schemas
    config_files = sorted(path for path in (project / "config").rglob("*") if path.is_file())
    bundled = [
        *schemas,
        project / "docs" / "architecture.md",
        project / "docs" / "configuration.md",
        project / "docs" / "update-workflow.md",
        project / "docs" / "threat-model.md",
        *config_files,
        project / "tests" / "fixtures" / "example-source" / "hello" / "SKILL.md",
    ]

    with zipfile.ZipFile(wheel) as wheel_archive, tarfile.open(sdist, "r:gz") as sdist_archive:
        sdist_members = {member.name: member for member in sdist_archive.getmembers()}
        assert "skill_delegator/schemas/target-delegation.schema.json" in wheel_archive.namelist()
        assert any(
            name.endswith("/schemas/target-delegation.schema.json") for name in sdist_members
        )
        forbidden_parts = (
            "/.superpowers/",
            "/var/cache/",
            "/var/example-targets/",
            "/var/receipts/",
        )
        assert not [
            name
            for name in wheel_archive.namelist()
            if any(part in f"/{name}" for part in forbidden_parts)
        ]
        assert not [
            name for name in sdist_members if any(part in f"/{name}" for part in forbidden_parts)
        ]
        for source in bundled:
            relative = source.relative_to(project).as_posix()
            if relative.startswith(("schemas/", "docs/")):
                wheel_name = f"skill_delegator/{relative}"
            else:
                wheel_name = f"skill_delegator/example/{relative}"
            assert wheel_archive.read(wheel_name) == source.read_bytes()

            sdist_name = next(name for name in sdist_members if name.endswith(f"/{relative}"))
            stream = sdist_archive.extractfile(sdist_members[sdist_name])
            assert stream is not None
            assert stream.read() == source.read_bytes()


def test_singular_target_schema_reuses_the_legacy_target_definition() -> None:
    project = Path(__file__).parents[2]
    singular = json.loads((project / "schemas" / "target-delegation.schema.json").read_text())
    legacy = json.loads((project / "schemas" / "delegations.schema.json").read_text())

    assert singular == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "target-delegation.schema.json",
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "target"],
        "properties": {
            "schema_version": {"const": 1},
            "target": {"$ref": "delegations.schema.json#/$defs/target"},
        },
    }
    assert legacy["properties"]["targets"]["items"] == {"$ref": "#/$defs/target"}
    assert legacy["$defs"]["target"]
