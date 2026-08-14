from __future__ import annotations

import subprocess
import tarfile
import zipfile
from pathlib import Path


def test_verification_receipt_schema_bytes_match_source_wheel_and_sdist(tmp_path: Path) -> None:
    project = Path(__file__).parents[2]
    dist = tmp_path / "dist"
    subprocess.run(
        ["uv", "build", "--out-dir", str(dist)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    source = (project / "schemas" / "verification-receipt.schema.json").read_bytes()
    wheel = next(dist.glob("*.whl"))
    sdist = next(dist.glob("*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        wheel_bytes = archive.read("skill_delegator/schemas/verification-receipt.schema.json")
    with tarfile.open(sdist, "r:gz") as archive:
        member = next(
            item
            for item in archive.getmembers()
            if item.name.endswith("/schemas/verification-receipt.schema.json")
        )
        stream = archive.extractfile(member)
        assert stream is not None
        sdist_bytes = stream.read()

    assert wheel_bytes == source
    assert sdist_bytes == source
