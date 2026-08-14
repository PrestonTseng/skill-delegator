from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest

from skill_delegator import receipts
from skill_delegator.models import (
    ConfigFileHash,
    LockedSourceIdentity,
    OperationSummary,
    TargetFingerprint,
    VerificationResult,
)
from skill_delegator.receipts import ReceiptError, receipt_document, write_receipt
from skill_delegator.schema_validation import schema_text

_SHA_A = "a" * 64
_SHA_B = "b" * 64


def _result() -> VerificationResult:
    return VerificationResult(
        result="converged",
        reasons=(),
        target_fingerprints=(TargetFingerprint("worker", _SHA_A),),
        operation_summary=OperationSummary(1, 1, 1, 0, 0),
        authority_id="test-authority",
        repository_commit="1" * 40,
        repository_commit_available=True,
        config_hashes=(
            ConfigFileHash("authority.yaml", _SHA_A),
            ConfigFileHash("delegations.yaml", _SHA_A),
            ConfigFileHash("pool.yaml", _SHA_A),
            ConfigFileHash("skill-lock.yaml", _SHA_B),
            ConfigFileHash("sources.yaml", _SHA_A),
        ),
        locked_sources=(LockedSourceIdentity("source", "filesystem", "tree_hash", _SHA_B, _SHA_B),),
    )


def test_receipt_document_has_strict_stable_public_schema_without_skill_content() -> None:
    document = receipt_document(_result())

    jsonschema.Draft202012Validator(
        json.loads(schema_text("verification-receipt.schema.json"))
    ).validate(document)
    assert document["schema_version"] == 1
    assert document["authority_id"] == "test-authority"
    assert document["repository"] == {"available": True, "commit": "1" * 40}
    payload = json.dumps(document, sort_keys=True)
    assert "description" not in payload
    assert "SKILL.md" not in payload
    assert "timestamp" not in payload


def test_repeated_identical_receipt_has_stable_path_and_byte_identical_content(
    tmp_path: Path,
) -> None:
    root = tmp_path / "var" / "receipts"

    first = write_receipt(_result(), root)
    first_bytes = first.read_bytes()
    second = write_receipt(_result(), root)

    assert first == second
    assert first.read_bytes() == first_bytes
    assert list(root.glob("*.json")) == [first]
    assert first.name == f"{first.stem}.json"
    assert len(first.stem) == 64


def test_receipt_explicitly_records_unavailable_repository_commit(tmp_path: Path) -> None:
    result = replace(_result(), repository_commit=None, repository_commit_available=False)

    path = write_receipt(result, tmp_path / "var" / "receipts")
    document = json.loads(path.read_text())

    assert document["repository"] == {"available": False, "commit": None}


def test_git_revision_does_not_claim_an_unavailable_tree_identity() -> None:
    commit = "c" * 40
    result = replace(
        _result(),
        locked_sources=(LockedSourceIdentity("source", "git", "resolved_commit", commit, None),),
    )

    document = receipt_document(result)

    jsonschema.Draft202012Validator(
        json.loads(schema_text("verification-receipt.schema.json"))
    ).validate(document)
    assert document["locked_sources"] == [
        {
            "source_id": "source",
            "type": "git",
            "revision_kind": "resolved_commit",
            "revision": commit,
            "tree_identity": None,
        }
    ]


@pytest.mark.parametrize("attack", ("root-symlink", "ancestor-symlink", "root-file", "outside-var"))
def test_receipt_path_attacks_fail_closed(tmp_path: Path, attack: str) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "var" / "receipts"
    if attack == "root-symlink":
        root.parent.mkdir()
        root.symlink_to(outside, target_is_directory=True)
    elif attack == "ancestor-symlink":
        (tmp_path / "real-var").mkdir()
        (tmp_path / "var").symlink_to(tmp_path / "real-var", target_is_directory=True)
    elif attack == "root-file":
        root.parent.mkdir()
        root.write_text("not a directory", encoding="utf-8")
    else:
        root = tmp_path / "receipts"

    with pytest.raises(ReceiptError):
        write_receipt(_result(), root)

    assert not list(outside.iterdir())


def test_existing_content_address_is_never_overwritten(tmp_path: Path) -> None:
    root = tmp_path / "var" / "receipts"
    path = write_receipt(_result(), root)
    path.write_text("hostile", encoding="utf-8")

    with pytest.raises(ReceiptError, match="collision"):
        write_receipt(_result(), root)

    assert path.read_text() == "hostile"


def test_receipt_root_swap_race_is_detected_and_publication_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "var" / "receipts"
    outside = tmp_path / "outside"
    outside.mkdir()
    root.mkdir(parents=True)
    moved = tmp_path / "var" / "receipts-moved"
    real_link = receipts.os.link

    def swap_then_link(*args, **kwargs):
        root.rename(moved)
        root.symlink_to(outside, target_is_directory=True)
        return real_link(*args, **kwargs)

    monkeypatch.setattr(receipts.os, "link", swap_then_link)

    with pytest.raises(ReceiptError, match="identity changed"):
        write_receipt(_result(), root)

    assert not list(outside.iterdir())
    assert not list(moved.glob("*.json"))


def test_malformed_receipt_fails_public_schema() -> None:
    document = receipt_document(_result())
    document["unexpected"] = True

    errors = list(
        jsonschema.Draft202012Validator(
            json.loads(schema_text("verification-receipt.schema.json"))
        ).iter_errors(document)
    )
    assert errors
    assert errors[0].validator == "additionalProperties"
