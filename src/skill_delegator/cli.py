"""Command-line interface for skill-delegator."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path, PurePosixPath

import yaml

from skill_delegator.config import load_config
from skill_delegator.errors import ConfigError, SourceError, UpdateError
from skill_delegator.lockfile import build_lock, write_lock_atomic
from skill_delegator.managed_state import TargetStateError, scan_target
from skill_delegator.models import (
    CurrentState,
    DesiredSource,
    DesiredState,
    DesiredTarget,
    LockedSkill,
    LockedSource,
    ReconciliationPlan,
    SkillLock,
)
from skill_delegator.planner import build_plan, plan_json, plan_text
from skill_delegator.receipts import ReceiptError, receipt_document, write_receipt
from skill_delegator.reconciler import ApplyError, apply_plan
from skill_delegator.resolver import ResolutionError, resolve_desired_state
from skill_delegator.source_store import resolve_sources
from skill_delegator.updater import (
    check_updates,
    prepare_update,
    proposal_document,
    proposal_text,
)
from skill_delegator.verifier import bind_verification_evidence, verify_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillctl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate configuration without applying it")
    validate.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    lock = subparsers.add_parser("lock", help="resolve sources and atomically write the exact lock")
    lock.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    resolve = subparsers.add_parser(
        "resolve", help="resolve desired target state without applying it"
    )
    resolve.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    resolve.add_argument("--json", action="store_true", required=True)
    plan = subparsers.add_parser("plan", help="scan targets and plan without applying changes")
    plan.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    plan.add_argument("--json", action="store_true")
    apply = subparsers.add_parser("apply", help="transactionally apply the validated plan")
    apply.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    apply.add_argument("--yes", action="store_true", help="confirm plans containing REMOVE")
    apply.add_argument("--lock-timeout", type=float, default=5.0, metavar="SECONDS")
    verify = subparsers.add_parser("verify", help="freshly verify state and write an audit receipt")
    verify.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    status = subparsers.add_parser("status", help="freshly report state without writing a receipt")
    status.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    status.add_argument("--json", action="store_true")
    update = subparsers.add_parser("update", help="check or propose explicit source updates")
    update.add_argument("source", nargs="?", metavar="SOURCE")
    update.add_argument("--all", action="store_true", dest="all_sources")
    update.add_argument("--check", action="store_true")
    update.add_argument("--json", action="store_true")
    update.add_argument("--config", type=Path, default=Path("config"), metavar="PATH")
    return parser


def _load_validated_lock(config_dir: Path) -> SkillLock:
    document = yaml.safe_load((config_dir / "skill-lock.yaml").read_text(encoding="utf-8"))
    return SkillLock(
        schema_version=document["schema_version"],
        sources=tuple(
            LockedSource(
                source_id=source["source_id"],
                source_type=source["type"],
                resolved_commit=source.get("resolved_commit"),
                tree_hash=source.get("tree_hash"),
                skills=tuple(
                    LockedSkill(
                        canonical_id=skill["canonical_id"],
                        runtime_name=skill["runtime_name"],
                        path=PurePosixPath(skill["path"]),
                        sha256=skill["sha256"],
                    )
                    for skill in source["skills"]
                ),
            )
            for source in document["sources"]
        ),
    )


def _desired_state_document(state: DesiredState) -> dict[str, object]:
    targets = state.targets
    return {
        "targets": [
            {
                "id": target.id,
                "root": str(target.root),
                "links": [
                    {
                        "artifact_id": link.artifact_id,
                        "runtime_name": link.runtime_name,
                        "source_path": link.source_path.as_posix(),
                        "target_path": str(link.target_path),
                        "content_sha256": link.content_sha256,
                    }
                    for link in target.links
                ],
            }
            for target in targets
        ]
    }


def _bind_expected_sources(state: DesiredState, lock: SkillLock, cache_root: Path) -> DesiredState:
    revisions = {}
    desired_sources = []
    for source in lock.sources:
        revision = source.resolved_commit or source.tree_hash
        if revision is None or source.tree_hash is None:
            raise ResolutionError(
                f"locked source {source.source_id} has no coherent immutable identity"
            )
        revisions[source.source_id] = revision
        desired_sources.append(
            DesiredSource(
                source.source_id, cache_root / source.source_id / revision, source.tree_hash
            )
        )
    targets: list[DesiredTarget] = []
    for target in state.targets:
        links = []
        for link in target.links:
            source_id = link.artifact_id.split("/", 1)[0]
            revision = revisions[source_id]
            if revision is None:
                raise ResolutionError(f"locked source {source_id} has no immutable revision")
            expected = cache_root / source_id / revision / link.source_path
            links.append(replace(link, expected_source_path=expected))
        targets.append(replace(target, links=tuple(links)))
    return DesiredState(tuple(targets), tuple(desired_sources))


def _render_plan(plan: ReconciliationPlan, *, json_output: bool) -> None:
    sys.stdout.write(plan_json(plan) if json_output else plan_text(plan))


def _fresh_verification(config_dir: Path):
    config_dir = config_dir.resolve(strict=False)
    config = load_config(config_dir)
    lock = _load_validated_lock(config_dir)
    desired = resolve_desired_state(config, lock)
    cache_root = config_dir.parent / "var" / "cache" / "sources"
    desired = _bind_expected_sources(desired, lock, cache_root)
    result = verify_state(desired, CurrentState((), cache_root))
    return bind_verification_evidence(result, config_dir, config, lock)


def _render_verification(result, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(receipt_document(result), sort_keys=True, separators=(",", ":")))
        return
    summary = result.operation_summary
    target_word = "target" if summary.desired_targets == 1 else "targets"
    print(
        f"{result.result}: {summary.verified_links}/{summary.desired_links} links verified "
        f"across {summary.desired_targets} {target_word}"
    )
    for reason in result.reasons:
        location = "/".join(
            part for part in (reason.target_id, reason.artifact_id) if part is not None
        )
        suffix = f" {location}" if location else ""
        print(f"- {reason.code}{suffix}")


def _verification_exit_code(result) -> int:
    if result.result == "converged":
        return 0
    return 1 if result.result == "drift" else 3


def _update_check_document(updates) -> dict[str, object]:
    return {
        "sources": [
            {
                "id": item.source_id,
                "type": item.source_type,
                "old_revision": item.old_revision,
                "new_revision": item.new_revision,
                "relation": item.relation,
            }
            for item in updates
        ]
    }


def _render_update_checks(updates, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(_update_check_document(updates), sort_keys=True, separators=(",", ":")))
        return
    for item in updates:
        print(f"source {item.source_id}: {item.relation}")
        print(f"  old: {item.old_revision}")
        print(f"  new: {item.new_revision or '-'}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if os.name != "posix":
        print("skillctl error: V1 requires POSIX", file=sys.stderr)
        return 2
    if args.command == "validate":
        try:
            config = load_config(args.config)
        except ConfigError as error:
            print(f"Configuration error: {error}", file=sys.stderr)
            return 2
        print(
            "Valid configuration: "
            f"1 authority, {len(config.sources)} source, "
            f"{len(config.pool)} pool entry, {len(config.targets)} targets"
        )
        return 0
    if args.command == "lock":
        try:
            config_dir = args.config.resolve(strict=False)
            config = load_config(config_dir, require_lock=False)
            cache_root = config_dir.parent / "var" / "cache" / "sources"
            resolved = resolve_sources(config, cache_root)
            lock = build_lock(config, resolved)
            write_lock_atomic(config_dir / "skill-lock.yaml", lock)
        except (ConfigError, SourceError) as error:
            print(f"Lock error: {error}", file=sys.stderr)
            return 2
        skill_count = sum(len(source.skills) for source in lock.sources)
        skill_word = "skill" if skill_count == 1 else "skills"
        source_word = "source" if len(lock.sources) == 1 else "sources"
        print(f"Locked {skill_count} {skill_word} from {len(lock.sources)} {source_word}")
        return 0
    if args.command == "update":
        selectors = int(args.source is not None) + int(args.all_sources) + int(args.check)
        if selectors != 1:
            print(
                "Update option conflict: choose exactly one of --check, SOURCE, or --all",
                file=sys.stderr,
            )
            return 2
        try:
            config_dir = args.config.resolve(strict=False)
            config = load_config(config_dir)
            old_lock = _load_validated_lock(config_dir)
            if args.check:
                updates = check_updates(config, old_lock)
                _render_update_checks(updates, json_output=args.json)
                if any(item.relation == "unavailable" for item in updates):
                    return 3
                return 1 if any(item.relation != "no-change" for item in updates) else 0

            source_ids = (
                tuple(source.id for source in sorted(config.sources, key=lambda item: item.id))
                if args.all_sources
                else (args.source,)
            )
            candidate = old_lock
            proposals = []
            for source_id in source_ids:
                if source_id is None:
                    raise SourceError("missing source selector")
                proposal = prepare_update(source_id, config, candidate)
                candidate = proposal.candidate_lock
                proposals.append(proposal)
            write_lock_atomic(config_dir / "skill-lock.yaml", candidate)
        except UpdateError as error:
            print(f"Update blocked: {error}", file=sys.stderr)
            return 3
        except SourceError as error:
            code = (
                str(error)
                if str(error) in {"lock-publication-failed", "lock-rollback-unsafe"}
                else "source-invalid"
            )
            print(f"Update blocked: {code}", file=sys.stderr)
            return 3
        except (
            ConfigError,
            ResolutionError,
            OSError,
            UnicodeError,
            ValueError,
            KeyError,
            TypeError,
        ):
            print("Update blocked: configuration-invalid", file=sys.stderr)
            return 3
        except Exception:  # noqa: BLE001 - final CLI disclosure boundary
            print("Update blocked: internal-error", file=sys.stderr)
            return 3
        if args.json:
            document = {"proposals": [proposal_document(item) for item in proposals]}
            print(json.dumps(document, sort_keys=True, separators=(",", ":")))
        else:
            for proposal in proposals:
                sys.stdout.write(proposal_text(proposal))
        return 0
    if args.command == "resolve":
        try:
            config_dir = args.config.resolve(strict=False)
            config = load_config(config_dir)
            lock = _load_validated_lock(config_dir)
            state = resolve_desired_state(config, lock)
        except (ConfigError, OSError, ResolutionError) as error:
            print(f"Resolve error: {error}", file=sys.stderr)
            return 2
        print(json.dumps(_desired_state_document(state), sort_keys=True, separators=(",", ":")))
        return 0
    if args.command == "plan":
        try:
            config_dir = args.config.resolve(strict=False)
            config = load_config(config_dir)
            lock = _load_validated_lock(config_dir)
            desired = resolve_desired_state(config, lock)
            cache_root = config_dir.parent / "var" / "cache" / "sources"
            desired = _bind_expected_sources(desired, lock, cache_root)
            current = CurrentState(
                tuple(scan_target(target) for target in config.targets), cache_root
            )
            plan = build_plan(desired, current)
        except TargetStateError as error:
            plan = ReconciliationPlan((), (str(error),))
        except (ConfigError, OSError, ResolutionError) as error:
            print(f"Plan error: {error}", file=sys.stderr)
            return 3
        _render_plan(plan, json_output=args.json)
        if plan.blocked:
            return 3
        return 1 if plan.has_changes else 0
    if args.command == "apply":
        try:
            config_dir = args.config.resolve(strict=False)
            config = load_config(config_dir)
            lock = _load_validated_lock(config_dir)
            desired = resolve_desired_state(config, lock)
            cache_root = config_dir.parent / "var" / "cache" / "sources"
            desired = _bind_expected_sources(desired, lock, cache_root)
            current = CurrentState(
                tuple(scan_target(target) for target in config.targets), cache_root
            )
            plan = build_plan(desired, current)
        except TargetStateError as error:
            print(f"Apply blocked: {error}", file=sys.stderr)
            return 3
        except (ConfigError, OSError, ResolutionError) as error:
            print(f"Apply error: {error}", file=sys.stderr)
            return 2
        if plan.blocked:
            print(f"Apply blocked: {plan.blocked[0]}", file=sys.stderr)
            return 3
        if any(operation.action == "REMOVE" for operation in plan.operations) and not args.yes:
            print("Apply refused: plan contains REMOVE; pass --yes to confirm", file=sys.stderr)
            return 4
        try:
            result = apply_plan(plan, lock_timeout=args.lock_timeout)
        except ApplyError as error:
            print(f"Apply error: {error}", file=sys.stderr)
            return 5
        if result.changed == 0:
            print("Already converged")
        else:
            change_word = "change" if result.changed == 1 else "changes"
            target_word = "target" if result.targets == 1 else "targets"
            print(f"Applied {result.changed} {change_word} to {result.targets} {target_word}")
        return 0
    if args.command in {"verify", "status"}:
        label = "Verify" if args.command == "verify" else "Status"
        try:
            result = _fresh_verification(args.config)
        except (ConfigError, OSError, ResolutionError, ValueError) as error:
            print(f"{label} error: {error}", file=sys.stderr)
            return 2
        if args.command == "status":
            _render_verification(result, json_output=args.json)
            return _verification_exit_code(result)
        try:
            receipt = write_receipt(
                result, args.config.resolve(strict=False).parent / "var" / "receipts"
            )
        except ReceiptError as error:
            print(f"Verify blocked: {error}", file=sys.stderr)
            return 3
        _render_verification(result, json_output=False)
        print(f"receipt: {receipt}")
        return _verification_exit_code(result)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
