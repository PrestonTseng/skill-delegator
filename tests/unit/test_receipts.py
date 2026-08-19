from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import jsonschema
import pytest

from skill_delegator import receipts
from skill_delegator.models import (
    ConfigFileHash,
    LockedSourceIdentity,
    OperationSummary,
    SourceTreeEvidence,
    TargetFingerprint,
    VerificationReason,
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
        source_tree_evidence=(SourceTreeEvidence("source", _SHA_B),),
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


def test_git_revision_requires_and_records_direct_snapshot_tree_identity() -> None:
    commit = "c" * 40
    result = replace(
        _result(),
        locked_sources=(LockedSourceIdentity("source", "git", "resolved_commit", commit, _SHA_B),),
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
            "tree_identity": _SHA_B,
        }
    ]


@pytest.mark.parametrize("result_name", ("drift", "invalid"))
def test_write_receipt_rejects_non_converged_results_without_creating_root(
    tmp_path: Path, result_name: str
) -> None:
    result = replace(
        _result(),
        result=result_name,
        reasons=(VerificationReason("not-converged", result_name, None, None, "blocked"),),
        operation_summary=OperationSummary(
            1, 1, 0, int(result_name == "drift"), int(result_name == "invalid")
        ),
    )
    root = tmp_path / "var" / "receipts"

    with pytest.raises(ReceiptError, match="converged"):
        write_receipt(result, root)

    assert not root.exists()


@pytest.mark.parametrize(
    "evidence",
    ((), (SourceTreeEvidence("source", _SHA_A),), (SourceTreeEvidence("other", _SHA_B),)),
)
def test_write_receipt_rejects_missing_or_incoherent_source_tree_evidence(
    tmp_path: Path, evidence: tuple[SourceTreeEvidence, ...]
) -> None:
    with pytest.raises(ReceiptError, match="source-tree evidence"):
        write_receipt(
            replace(_result(), source_tree_evidence=evidence),
            tmp_path / "var" / "receipts",
        )


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


@pytest.mark.parametrize(
    "config_hashes",
    (
        (
            ConfigFileHash("authority.yaml", _SHA_A),
            ConfigFileHash("authority.yaml", _SHA_B),
            ConfigFileHash("pool.yaml", _SHA_A),
            ConfigFileHash("skill-lock.yaml", _SHA_B),
            ConfigFileHash("sources.yaml", _SHA_A),
        ),
        _result().config_hashes[:-1],
    ),
)
def test_write_receipt_rejects_duplicate_or_missing_config_names(
    tmp_path: Path, config_hashes: tuple[ConfigFileHash, ...]
) -> None:
    with pytest.raises(ReceiptError, match="config_hashes"):
        write_receipt(
            replace(_result(), config_hashes=config_hashes), tmp_path / "var" / "receipts"
        )


@pytest.mark.parametrize(
    "identity",
    (
        LockedSourceIdentity("source", "git", "tree_hash", _SHA_A, _SHA_A),
        LockedSourceIdentity("source", "git", "resolved_commit", _SHA_A, None),
        LockedSourceIdentity("source", "filesystem", "resolved_commit", _SHA_A, None),
        LockedSourceIdentity("source", "filesystem", "tree_hash", _SHA_A, _SHA_B),
    ),
)
def test_write_receipt_rejects_incoherent_source_identities(
    tmp_path: Path, identity: LockedSourceIdentity
) -> None:
    with pytest.raises(ReceiptError, match="locked_sources"):
        write_receipt(replace(_result(), locked_sources=(identity,)), tmp_path / "var" / "receipts")


def test_write_receipt_rejects_duplicate_locked_source_ids(tmp_path: Path) -> None:
    duplicate = LockedSourceIdentity("source", "git", "resolved_commit", "c" * 40, _SHA_A)
    with pytest.raises(ReceiptError, match="locked_sources"):
        write_receipt(
            replace(_result(), locked_sources=(_result().locked_sources[0], duplicate)),
            tmp_path / "var" / "receipts",
        )


def test_schema_rejects_duplicate_config_names_and_incoherent_git_identity() -> None:
    validator = jsonschema.Draft202012Validator(
        json.loads(schema_text("verification-receipt.schema.json"))
    )
    duplicate_names = receipt_document(_result())
    duplicate_names["config_hashes"][1]["name"] = "authority.yaml"
    incoherent_git = receipt_document(_result())
    incoherent_git["locked_sources"] = [
        {
            "source_id": "source",
            "type": "git",
            "revision_kind": "tree_hash",
            "revision": _SHA_A,
            "tree_identity": _SHA_A,
        }
    ]

    assert list(validator.iter_errors(duplicate_names))
    assert list(validator.iter_errors(incoherent_git))


def test_write_receipt_rejects_semantically_impossible_operation_evidence(tmp_path: Path) -> None:
    impossible = replace(_result(), operation_summary=OperationSummary(1, 1, 2, 0, 0))

    with pytest.raises(ReceiptError, match="operation evidence"):
        write_receipt(impossible, tmp_path / "var" / "receipts")


def test_write_receipt_rolls_back_new_publication_when_primary_cleanup_close_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "var" / "receipts"
    root.mkdir(parents=True)
    real_close = receipts.os.close
    real_link = receipts.os.link
    root_metadata = root.stat(follow_symlinks=False)
    root_identity = (root_metadata.st_dev, root_metadata.st_ino)
    linked = False
    fired = False

    def tracking_link(*args, **kwargs):
        nonlocal linked
        result = real_link(*args, **kwargs)
        linked = True
        return result

    def fail_primary_close(descriptor: int) -> None:
        nonlocal fired
        try:
            metadata = os.fstat(descriptor)
            is_root = (metadata.st_dev, metadata.st_ino) == root_identity
        except OSError:
            is_root = False
        if linked and not fired and is_root:
            fired = True
            real_close(descriptor)
            raise OSError("injected post-publication directory close failure")
        real_close(descriptor)

    monkeypatch.setattr(receipts.os, "link", tracking_link)
    monkeypatch.setattr(receipts.os, "close", fail_primary_close)

    with pytest.raises(ReceiptError, match="clean up"):
        write_receipt(_result(), root)

    assert fired
    assert not list(root.glob("*.json"))

    monkeypatch.setattr(receipts.os, "close", real_close)
    existing = write_receipt(_result(), root)
    fired = False
    monkeypatch.setattr(receipts.os, "close", fail_primary_close)
    with pytest.raises(ReceiptError, match="clean up"):
        write_receipt(_result(), root)
    assert fired
    assert existing.exists()

    root_close_count = 0

    def fail_only_final_cleanup_close(descriptor: int) -> None:
        nonlocal root_close_count
        try:
            metadata = os.fstat(descriptor)
            is_root = (metadata.st_dev, metadata.st_ino) == root_identity
        except OSError:
            is_root = False
        if is_root:
            root_close_count += 1
            if root_close_count == 2:
                real_close(descriptor)
                raise OSError("injected final cleanup descriptor close failure")
        real_close(descriptor)

    monkeypatch.setattr(receipts.os, "link", real_link)
    monkeypatch.setattr(receipts.os, "close", fail_only_final_cleanup_close)
    assert write_receipt(_result(), root) == existing
    assert root_close_count == 2
    assert existing.exists()


def test_write_receipt_requires_coherent_converged_fingerprints_and_counts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "var" / "receipts"
    second = TargetFingerprint("z-worker", _SHA_B)
    impossible = (
        replace(_result(), operation_summary=OperationSummary(1, 2, 1, 0, 0)),
        replace(_result(), operation_summary=OperationSummary(2, 1, 1, 0, 0)),
        replace(
            _result(),
            target_fingerprints=(
                _result().target_fingerprints[0],
                _result().target_fingerprints[0],
            ),
            operation_summary=OperationSummary(2, 1, 1, 0, 0),
        ),
        replace(
            _result(),
            target_fingerprints=(second, _result().target_fingerprints[0]),
            operation_summary=OperationSummary(2, 1, 1, 0, 0),
        ),
    )

    for result in impossible:
        with pytest.raises(ReceiptError, match="operation evidence"):
            write_receipt(result, root)

    legitimate_drift_evidence = replace(
        _result(),
        result="drift",
        reasons=(VerificationReason("missing", "drift", "worker", "source/one", "missing"),),
        operation_summary=OperationSummary(1, 2, 1, 1, 0),
    )
    with pytest.raises(ReceiptError, match="converged"):
        write_receipt(legitimate_drift_evidence, root)
