#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def is_toc(node: Dict[str, Any]) -> bool:
    attrs = node.get("attrs", {})
    return (
        node.get("type") == "extension"
        and attrs.get("extensionType") == "com.atlassian.confluence.macro.core"
        and attrs.get("extensionKey") == "toc"
    )


def heading_text(node: Dict[str, Any]) -> str:
    if node.get("type") != "heading":
        return ""
    return "".join(
        child.get("text", "")
        for child in node.get("content", [])
        if child.get("type") == "text"
    )


def find_heading_index(content: List[Dict[str, Any]], text: str) -> int:
    matches = [i for i, node in enumerate(content) if node.get("type") == "heading" and heading_text(node) == text]
    if not matches:
        raise ValueError(f"Heading not found: {text!r}")
    if len(matches) > 1:
        raise ValueError(f"Heading is ambiguous ({len(matches)} matches): {text!r}")
    return matches[0]


def section_body_range(content: List[Dict[str, Any]], heading_idx: int) -> Tuple[int, int]:
    heading = content[heading_idx]
    level = heading.get("attrs", {}).get("level", 6)
    start = heading_idx + 1
    end = len(content)
    for i in range(start, len(content)):
        node = content[i]
        if node.get("type") == "heading" and node.get("attrs", {}).get("level", 6) <= level:
            end = i
            break
    return start, end


def normalize_replacement(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, dict) and obj.get("type") == "doc":
        return obj.get("content", [])
    if isinstance(obj, list):
        return obj
    raise ValueError("Replacement must be a node array or a full ADF doc")


def patch_section(base_doc: Dict[str, Any], heading: str, replacement_nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    content = base_doc.get("content", [])
    idx = find_heading_index(content, heading)
    start, end = section_body_range(content, idx)
    new_content = content[:start] + replacement_nodes + content[end:]
    out = dict(base_doc)
    out["content"] = new_content
    return out


def verify_section(before_doc: Dict[str, Any], after_doc: Dict[str, Any], heading: str) -> Dict[str, Any]:
    before = before_doc.get("content", [])
    after = after_doc.get("content", [])
    idx_before = find_heading_index(before, heading)
    idx_after = find_heading_index(after, heading)
    if before[idx_before] != after[idx_after]:
        raise ValueError("Target heading node changed; heading must remain unchanged for surgical patching")
    before_start, before_end = section_body_range(before, idx_before)
    after_start, after_end = section_body_range(after, idx_after)
    prefix_same = before[:before_start] == after[:after_start]
    suffix_same = before[before_end:] == after[after_end:]
    return {
        "heading": heading,
        "prefix_same": prefix_same,
        "suffix_same": suffix_same,
        "before_body_node_count": before_end - before_start,
        "after_body_node_count": after_end - after_start,
        "surgical_ok": prefix_same and suffix_same,
    }


def walk(node: Any, visit):
    if isinstance(node, dict):
        visit(node)
        for value in node.values():
            walk(value, visit)
    elif isinstance(node, list):
        for item in node:
            walk(item, visit)


def validate(doc: Dict[str, Any], require_toc_first: bool, forbid_plain_links: bool) -> Dict[str, Any]:
    if doc.get("type") != "doc":
        raise ValueError("ADF root must have type='doc'")
    content = doc.get("content", [])
    plain_link_count = 0
    inline_card_count = 0
    block_card_count = 0
    toc_first = bool(content and is_toc(content[0]))
    forbidden_center_nodes = []

    def visit(node: Dict[str, Any]):
        nonlocal plain_link_count, inline_card_count, block_card_count
        ntype = node.get("type")
        if ntype == "inlineCard":
            inline_card_count += 1
        if ntype == "blockCard":
            block_card_count += 1
        if ntype == "text":
            for mark in node.get("marks", []):
                if mark.get("type") == "link":
                    plain_link_count += 1
        attrs = node.get("attrs", {})
        if attrs.get("layout") == "center":
            extension_key = attrs.get("extensionKey")
            if extension_key != "native-embed:page":
                forbidden_center_nodes.append({
                    "type": ntype,
                    "attrs": attrs,
                })

    walk(doc, visit)

    errors = []
    warnings = []
    if require_toc_first and not toc_first:
        errors.append("TOC extension node is not the first top-level node")
    if forbid_plain_links and plain_link_count > 0:
        errors.append(f"Found {plain_link_count} plain text link node(s); default policy requires inline smart links")
    elif plain_link_count > 0:
        warnings.append(f"Found {plain_link_count} plain text link node(s); confirm these are intentional exceptions")
    if forbidden_center_nodes:
        errors.append(f"Found {len(forbidden_center_nodes)} centered node(s) outside native embed exceptions")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "toc_first": toc_first,
            "plain_link_count": plain_link_count,
            "inline_card_count": inline_card_count,
            "block_card_count": block_card_count,
            "forbidden_center_node_count": len(forbidden_center_nodes),
        },
    }


def cmd_validate(args: argparse.Namespace) -> int:
    doc = load_json(args.doc)
    result = validate(doc, require_toc_first=args.require_toc_first, forbid_plain_links=args.forbid_plain_links)
    print(dump_json(result))
    return 0 if result["ok"] else 1


def cmd_patch_section(args: argparse.Namespace) -> int:
    base_doc = load_json(args.base)
    replacement_nodes = normalize_replacement(load_json(args.replacement))
    out = patch_section(base_doc, args.heading, replacement_nodes)
    Path(args.out).write_text(dump_json(out) + "\n", encoding="utf-8")
    result = {
        "ok": True,
        "out": str(Path(args.out).resolve()),
        "heading": args.heading,
        "replacement_node_count": len(replacement_nodes),
    }
    print(dump_json(result))
    return 0


def cmd_verify_section(args: argparse.Namespace) -> int:
    before_doc = load_json(args.before)
    after_doc = load_json(args.after)
    result = verify_section(before_doc, after_doc, args.heading)
    if args.require_toc_first:
        validation = validate(after_doc, require_toc_first=True, forbid_plain_links=False)
        result["toc_first"] = validation["stats"]["toc_first"]
        result["toc_ok"] = validation["stats"]["toc_first"]
        result["surgical_ok"] = result["surgical_ok"] and validation["stats"]["toc_first"]
    print(dump_json(result))
    return 0 if result["surgical_ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guardrails for Lilee Confluence ADF authoring")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate an ADF document against house rules")
    p_validate.add_argument("doc")
    p_validate.add_argument("--require-toc-first", action="store_true")
    p_validate.add_argument("--forbid-plain-links", action="store_true")
    p_validate.set_defaults(func=cmd_validate)

    p_patch = sub.add_parser("patch-section", help="Replace only the body of a named heading section")
    p_patch.add_argument("--base", required=True)
    p_patch.add_argument("--heading", required=True)
    p_patch.add_argument("--replacement", required=True)
    p_patch.add_argument("--out", required=True)
    p_patch.set_defaults(func=cmd_patch_section)

    p_verify = sub.add_parser("verify-section", help="Verify only the named section body changed")
    p_verify.add_argument("--before", required=True)
    p_verify.add_argument("--after", required=True)
    p_verify.add_argument("--heading", required=True)
    p_verify.add_argument("--require-toc-first", action="store_true")
    p_verify.set_defaults(func=cmd_verify_section)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(dump_json({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
