#!/usr/bin/env python3
import argparse
import copy
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


PLACEHOLDER_KEYS = [
    "candidate_name",
    "applied_position",
    "resume_received",
    "candidate_source",
    "stage0_reviewer",
    "stage0_review_date",
    "stage0_review_summary_p1",
    "stage0_review_summary_p2",
    "hr_screen_focus_1",
    "hr_screen_focus_2",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def text(node):
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        return "".join(text(c) for c in node.get("content", []) or [])
    if isinstance(node, list):
        return "".join(text(item) for item in node)
    return ""


def paragraph_with_text(value: str):
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": value}] if value else [],
    }


def paragraph_with_link(label: str, url: str):
    return {
        "type": "paragraph",
        "content": [
            {
                "type": "text",
                "text": label,
                "marks": [{"type": "link", "attrs": {"href": url}}],
            }
        ],
    }


def replace_placeholders(node, replacements):
    if isinstance(node, dict):
        if node.get("type") == "text":
            raw = node.get("text", "")
            if raw in replacements:
                node["text"] = replacements[raw]
        for value in node.values():
            replace_placeholders(value, replacements)
    elif isinstance(node, list):
        for item in node:
            replace_placeholders(item, replacements)


def to_timestamp_ms(date_str: str):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str or ""):
        return None
    d = dt.date.fromisoformat(date_str)
    return str(int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000))


def set_stage0_date(doc, date_str: str):
    ts = to_timestamp_ms(date_str)
    if not ts:
        return
    current_h1 = None
    for node in doc.get("content", []):
        if node.get("type") == "heading" and node.get("attrs", {}).get("level") == 1:
            current_h1 = text(node).strip()
        elif node.get("type") == "table" and current_h1 == "Stage 0 — Resume Review":
            for row in node.get("content", [])[1:]:
                cells = row.get("content", [])
                if len(cells) < 2:
                    continue
                label = text(cells[0]).strip()
                if label == "Date":
                    cells[1]["content"] = [{
                        "type": "paragraph",
                        "content": [{"type": "date", "attrs": {"timestamp": ts}}],
                    }]
                    return


def set_resume_link(doc, resume_link):
    current_h1 = None
    for node in doc.get("content", []):
        if node.get("type") == "heading" and node.get("attrs", {}).get("level") == 1:
            current_h1 = text(node).strip()
        elif node.get("type") == "table" and current_h1 == "Candidate Info":
            for row in node.get("content", [])[1:]:
                cells = row.get("content", [])
                if len(cells) < 2:
                    continue
                label = text(cells[0]).strip()
                if label != "Resume Link":
                    continue
                if isinstance(resume_link, dict):
                    url = resume_link.get("url")
                    label_text = resume_link.get("label") or "Resume"
                    note = resume_link.get("note") or "—"
                    new_para = paragraph_with_link(label_text, url) if url else paragraph_with_text(note)
                elif isinstance(resume_link, str) and resume_link.strip():
                    new_para = paragraph_with_text(resume_link.strip())
                else:
                    new_para = paragraph_with_text("—")
                cells[1]["content"] = [new_para]
                return


def set_stage0_focus_list(doc, items):
    if not items:
        items = ["(Add HR screening focus here.)"]
    current_h1 = None
    pending_focus_list = False
    for node in doc.get("content", []):
        if node.get("type") == "heading" and node.get("attrs", {}).get("level") == 1:
            current_h1 = text(node).strip()
        elif current_h1 == "Stage 0 — Resume Review" and node.get("type") == "paragraph":
            if text(node).strip() == "Suggested focus for HR screening call:":
                pending_focus_list = True
        elif current_h1 == "Stage 0 — Resume Review" and pending_focus_list and node.get("type") == "bulletList":
            node["content"] = [
                {
                    "type": "listItem",
                    "content": [paragraph_with_text(item)],
                }
                for item in items
            ]
            return


def compute_title(profile):
    if profile.get("page_title_suggestion"):
        return profile["page_title_suggestion"]
    year = (profile.get("resume_received") or dt.date.today().isoformat())[:4]
    honorific = profile.get("honorific", "").strip()
    name = profile.get("candidate_name", "").strip()
    role = profile.get("applied_position", "").strip()
    prefix = f"{honorific} {name}".strip()
    return f"{year} - {prefix} - {role} - Stage 1".replace("  ", " ").strip()


def validate_profile(profile):
    required = [
        "candidate_name",
        "applied_position",
        "resume_received",
        "candidate_source",
        "stage0_reviewer",
        "stage0_review_date",
    ]
    missing = [key for key in required if not str(profile.get(key, "")).strip()]
    if missing:
        raise SystemExit(f"Missing required profile fields: {', '.join(missing)}")
    summaries = profile.get("stage0_review_summary") or []
    if not isinstance(summaries, list) or not summaries:
        raise SystemExit("stage0_review_summary must be a non-empty list")
    focuses = profile.get("hr_screen_focus") or []
    if not isinstance(focuses, list) or not focuses:
        raise SystemExit("hr_screen_focus must be a non-empty list")


def main():
    ap = argparse.ArgumentParser(description="Fill the canonical candidate tracking page template from a structured candidate profile JSON.")
    ap.add_argument("--profile", required=True, help="Path to candidate-profile.json")
    ap.add_argument("--template", default=str(Path(__file__).resolve().parents[1] / "templates" / "candidate-tracking-page-template.adf.json"))
    ap.add_argument("--output", required=True, help="Path to write the filled ADF JSON")
    ap.add_argument("--meta-output", help="Optional JSON file for title suggestion and provenance")
    ap.add_argument("--verify", action="store_true", help="Run the canonical layout verifier after writing output")
    args = ap.parse_args()

    profile = load_json(Path(args.profile))
    validate_profile(profile)
    template = load_json(Path(args.template))
    doc = copy.deepcopy(template)

    summaries = profile.get("stage0_review_summary") or []
    focuses = profile.get("hr_screen_focus") or []
    replacements = {
        "{{candidate_name}}": profile.get("candidate_name", ""),
        "{{applied_position}}": profile.get("applied_position", ""),
        "{{resume_received}}": profile.get("resume_received", ""),
        "{{candidate_source}}": profile.get("candidate_source", ""),
        "{{resume_link_or_dash}}": (profile.get("resume_link") or {}).get("note", "—") if isinstance(profile.get("resume_link"), dict) else (profile.get("resume_link") or "—"),
        "{{stage0_reviewer}}": profile.get("stage0_reviewer", ""),
        "{{stage0_review_date}}": profile.get("stage0_review_date", ""),
        "{{stage0_review_summary_p1}}": summaries[0],
        "{{stage0_review_summary_p2}}": summaries[1] if len(summaries) > 1 else "",
        "{{hr_screen_focus_1}}": focuses[0],
        "{{hr_screen_focus_2}}": focuses[1] if len(focuses) > 1 else focuses[0],
    }
    replace_placeholders(doc, replacements)
    set_stage0_date(doc, profile.get("stage0_review_date", ""))
    set_resume_link(doc, profile.get("resume_link"))
    set_stage0_focus_list(doc, focuses)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.meta_output:
        meta = {
            "page_title_suggestion": compute_title(profile),
            "profile_path": str(Path(args.profile).resolve()),
            "template_path": str(Path(args.template).resolve()),
            "output_path": str(output_path.resolve()),
            "resume_filename": profile.get("resume_filename"),
        }
        meta_path = Path(args.meta_output)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.verify:
        verifier = Path(__file__).resolve().parent / "verify_candidate_tracking_layout.py"
        result = subprocess.run([sys.executable, str(verifier), "--file", str(output_path)], check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)

    print(json.dumps({
        "ok": True,
        "output": str(output_path.resolve()),
        "page_title_suggestion": compute_title(profile),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
