#!/usr/bin/env python3
"""Refresh Delivery Map due-date formulas and workstream release tags in Confluence ADF.

The script reads a live Confluence Delivery Map, recomputes due-date cells whose
left-hand side is a scheduling expression (for example `WS8.1 + 10D` or
`max(WS10.1, WS10.3) + 5D`), and optionally writes the updated ADF back.

Auth: set ATLASSIAN_API_KEY to a base64 `email:api_token` string accepted by
Atlassian Basic auth. The script uses only Python stdlib.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CLOUD_ID = "302f7dfa-a172-4986-b4ae-efd7021f110a"
DEFAULT_SITE = "https://lileesystems.atlassian.net"

ISO_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
ISO_SLASH_RE = re.compile(r"\b(20\d{2})/(\d{2})/(\d{2})\b")
WS_RE = re.compile(r"\bWS\s*(\d+)\s*\.\s*(\d+)\b", re.I)
ADD_RE = re.compile(r"^(?P<base>.+?)\s*\+\s*(?P<days>\d+)\s*D\s*$", re.I)
MAX_RE = re.compile(r"^max\((?P<args>.+)\)$", re.I)
RELEASE_WINDOW_RE = re.compile(
    r"SafeAR[Tt]\s+(?P<version>\d+\.\d+)\s*[:：]\s*"
    r"(?P<start>20\d{2}-\d{2}-\d{2})\s*[-–—]\s*(?P<end>20\d{2}-\d{2}-\d{2})"
)
RELEASE_STATUS_RE = re.compile(r"^SafeAR[Tt]\s+\d+\.\d+$")

ADF = dict[str, Any]


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def fmt_date(d: dt.date) -> str:
    return d.isoformat()


def add_business_days(start: dt.date, days: int) -> dt.date:
    """Add Mon-Fri business days, exclusive of the start date."""
    cur = start
    remaining = days
    while remaining > 0:
        cur += dt.timedelta(days=1)
        if cur.weekday() < 5:
            remaining -= 1
    return cur


def adf_plain_text(node: Any) -> str:
    if isinstance(node, list):
        return "".join(adf_plain_text(x) for x in node)
    if not isinstance(node, dict):
        return ""
    typ = node.get("type")
    if typ == "text":
        return node.get("text", "")
    if typ == "hardBreak":
        return "\n"
    if typ == "status":
        return node.get("attrs", {}).get("text", "")
    if typ == "date":
        attrs = node.get("attrs", {})
        # Confluence date nodes usually carry millisecond UTC timestamp.
        ts = attrs.get("timestamp") or attrs.get("datetime")
        if isinstance(ts, int):
            return dt.datetime.fromtimestamp(ts / 1000, dt.UTC).date().isoformat()
        if isinstance(ts, str) and ts.isdigit():
            return dt.datetime.fromtimestamp(int(ts) / 1000, dt.UTC).date().isoformat()
        return str(ts or "")
    if typ == "mention":
        return node.get("attrs", {}).get("text", "")
    if typ == "inlineCard":
        return node.get("attrs", {}).get("url", "")
    return "".join(adf_plain_text(c) for c in node.get("content", []))


def text_cell(value: str) -> list[ADF]:
    return [{"type": "paragraph", "content": [{"type": "text", "text": value}]}]


def canonical_ws(ref: str) -> str:
    m = WS_RE.search(ref)
    if not m:
        raise ValueError(f"not a work-item reference: {ref}")
    return f"WS{int(m.group(1))}.{int(m.group(2))}"


def first_iso(text: str) -> dt.date | None:
    m = ISO_RE.search(text)
    if m:
        return parse_date(m.group(1))
    m = ISO_SLASH_RE.search(text)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


@dataclass
class WorkItem:
    ws_id: str
    ws_num: int
    item_num: int
    heading_node: ADF
    heading_index: int
    table_index: int
    row_node: ADF
    due_cell: ADF
    due_text: str
    due_lhs: str | None = None
    resolved_due: dt.date | None = None
    changed_due: bool = False


@dataclass
class ReleaseWindow:
    label: str
    start: dt.date
    end: dt.date
    inferred: bool = False


def iter_tables_with_headings(body: ADF):
    current_heading: tuple[int, ADF, str] | None = None
    for idx, node in enumerate(body.get("content", [])):
        if node.get("type") == "heading":
            htext = adf_plain_text(node).strip()
            if re.match(r"^\d+\.\s+", htext):
                current_heading = (idx, node, htext)
        elif node.get("type") == "table" and current_heading:
            yield current_heading, idx, node


def row_cells(row: ADF) -> list[ADF]:
    return [c for c in row.get("content", []) if c.get("type") in {"tableCell", "tableHeader"}]


def find_col(headers: list[str], names: Iterable[str]) -> int | None:
    lowered = [h.strip().lower() for h in headers]
    for name in names:
        n = name.lower()
        for idx, h in enumerate(lowered):
            if n == h or n in h:
                return idx
    return None


def extract_work_items(body: ADF) -> dict[str, WorkItem]:
    items: dict[str, WorkItem] = {}
    for (heading_idx, heading_node, _heading_text), table_idx, table in iter_tables_with_headings(body):
        rows = [r for r in table.get("content", []) if r.get("type") == "tableRow"]
        if not rows:
            continue
        headers = [adf_plain_text(c).strip() for c in row_cells(rows[0])]
        work_col = find_col(headers, ["Work Item"])
        due_col = find_col(headers, ["Due Date"])
        if work_col is None or due_col is None:
            continue
        for row in rows[1:]:
            cells = row_cells(row)
            if max(work_col, due_col) >= len(cells):
                continue
            work_text = adf_plain_text(cells[work_col]).strip()
            m = WS_RE.search(work_text)
            if not m:
                continue
            ws_id = f"WS{int(m.group(1))}.{int(m.group(2))}"
            due_text = " ".join(adf_plain_text(cells[due_col]).split())
            items[ws_id] = WorkItem(
                ws_id=ws_id,
                ws_num=int(m.group(1)),
                item_num=int(m.group(2)),
                heading_node=heading_node,
                heading_index=heading_idx,
                table_index=table_idx,
                row_node=row,
                due_cell=cells[due_col],
                due_text=due_text,
            )
    return items


class Resolver:
    def __init__(self, items: dict[str, WorkItem]):
        self.items = items
        self.stack: list[str] = []

    def resolve_item(self, ws_id: str) -> dt.date | None:
        ws_id = canonical_ws(ws_id)
        item = self.items.get(ws_id)
        if not item:
            raise ValueError(f"unknown work-item reference {ws_id}")
        if item.resolved_due:
            return item.resolved_due
        if ws_id in self.stack:
            raise ValueError(f"cyclic dependency: {' -> '.join(self.stack + [ws_id])}")
        self.stack.append(ws_id)
        try:
            item.due_lhs = self.left_hand_expression(item.due_text)
            if item.due_lhs:
                item.resolved_due = self.eval_expr(item.due_lhs)
                return item.resolved_due
            item.resolved_due = first_iso(item.due_text)
            return item.resolved_due
        finally:
            self.stack.pop()

    @staticmethod
    def left_hand_expression(text: str) -> str | None:
        if not text:
            return None
        lhs = text.split("=", 1)[0].strip() if "=" in text else text.strip()
        # Only recompute formula-like cells. Plain dates / H1 notes remain as evidence.
        if ADD_RE.match(lhs) or MAX_RE.match(lhs) or WS_RE.fullmatch(lhs.replace(" ", "")):
            return lhs
        # Handle common typo spacing like `WS 14.4 + 5D`.
        if WS_RE.search(lhs) and "+" in lhs:
            return lhs
        return None

    def eval_expr(self, expr: str) -> dt.date:
        expr = expr.strip()
        m = ADD_RE.match(expr)
        if m:
            base = self.eval_expr(m.group("base"))
            return add_business_days(base, int(m.group("days")))
        m = MAX_RE.match(expr)
        if m:
            parts = [p.strip() for p in m.group("args").split(",") if p.strip()]
            if not parts:
                raise ValueError(f"empty max() expression: {expr}")
            return max(self.eval_expr(p) for p in parts)
        if WS_RE.fullmatch(expr.replace(" ", "")) or WS_RE.search(expr):
            return self.resolve_item(canonical_ws(expr))  # type: ignore[return-value]
        d = first_iso(expr)
        if d:
            return d
        raise ValueError(f"unsupported due-date expression: {expr}")


def extract_release_windows_from_body(body: ADF) -> list[ReleaseWindow]:
    text = adf_plain_text(body)
    windows: list[ReleaseWindow] = []
    seen: set[str] = set()
    for m in RELEASE_WINDOW_RE.finditer(text):
        label = f"SafeART {m.group('version')}"
        if label in seen:
            continue
        seen.add(label)
        windows.append(ReleaseWindow(label, parse_date(m.group('start')), parse_date(m.group('end')), False))
    windows.sort(key=lambda w: w.start)
    return windows


def extend_windows(windows: list[ReleaseWindow], through: dt.date) -> None:
    if not windows:
        return
    # Continue the latest explicit cadence. Existing SafeART KPI windows are contiguous.
    while through > windows[-1].end:
        prev = windows[-1]
        duration = (prev.end - prev.start).days
        # Increment the minor component in labels like SafeART 0.25.
        lm = re.search(r"(\d+)\.(\d+)$", prev.label)
        if not lm:
            return
        next_label = f"SafeART {int(lm.group(1))}.{int(lm.group(2)) + 1}"
        next_start = prev.end + dt.timedelta(days=1)
        next_end = next_start + dt.timedelta(days=duration)
        windows.append(ReleaseWindow(next_label, next_start, next_end, True))


def label_for_date(d: dt.date, windows: list[ReleaseWindow]) -> str:
    for w in windows:
        if w.start <= d <= w.end:
            return w.label
    if windows and d > windows[-1].end:
        return f"After {windows[-1].label}"
    if windows and d < windows[0].start:
        return f"Before {windows[0].label}"
    return "Unscheduled"


def update_heading_release_status(heading: ADF, new_label: str) -> bool:
    """Replace the first release status node in a heading, preserving other text/statuses."""
    changed = False
    content = heading.get("content", [])
    for idx, child in enumerate(content):
        if child.get("type") == "status":
            attrs = child.setdefault("attrs", {})
            old_text = attrs.get("text", "")
            if RELEASE_STATUS_RE.match(old_text):
                if old_text != new_label:
                    attrs["text"] = new_label
                    # Release identifiers are status controls; purple is the house convention.
                    attrs["color"] = attrs.get("color") or "purple"
                    changed = True
                return changed
    # If no release status exists, append one with a separating space.
    content.append({"type": "text", "text": " "})
    content.append({"type": "status", "attrs": {"text": new_label, "color": "purple"}})
    heading["content"] = content
    return True


def refresh(body: ADF, windows: list[ReleaseWindow]) -> tuple[ADF, dict[str, Any]]:
    new_body = copy.deepcopy(body)
    items = extract_work_items(new_body)
    resolver = Resolver(items)
    errors: list[str] = []
    due_changes: list[dict[str, str]] = []
    for ws_id in sorted(items, key=lambda k: (items[k].ws_num, items[k].item_num)):
        item = items[ws_id]
        try:
            resolved = resolver.resolve_item(ws_id)
        except Exception as e:
            errors.append(f"{ws_id}: {e}")
            continue
        if item.due_lhs and resolved:
            new_text = f"{item.due_lhs} = {fmt_date(resolved)}"
            if item.due_text != new_text:
                item.due_cell["content"] = text_cell(new_text)
                item.changed_due = True
                due_changes.append({"ws_id": ws_id, "from": item.due_text, "to": new_text})

    dated_items = [i for i in items.values() if i.resolved_due]
    if dated_items:
        extend_windows(windows, max(i.resolved_due for i in dated_items if i.resolved_due))

    release_changes: list[dict[str, str]] = []
    headings_by_ws: dict[int, ADF] = {}
    heading_text_before: dict[int, str] = {}
    for item in items.values():
        headings_by_ws[item.ws_num] = item.heading_node
        heading_text_before[item.ws_num] = adf_plain_text(item.heading_node).strip()
    for ws_num in sorted(headings_by_ws):
        ws_items = [i for i in items.values() if i.ws_num == ws_num and i.resolved_due]
        if not ws_items:
            continue
        latest = max(i.resolved_due for i in ws_items if i.resolved_due)
        label = label_for_date(latest, windows)
        before = heading_text_before[ws_num]
        if update_heading_release_status(headings_by_ws[ws_num], label):
            after = adf_plain_text(headings_by_ws[ws_num]).strip()
            release_changes.append({"workstream": str(ws_num), "latest_due": fmt_date(latest), "from": before, "to": after})

    summary = {
        "work_items": len(items),
        "due_changes": due_changes,
        "release_changes": release_changes,
        "windows": [{"label": w.label, "start": fmt_date(w.start), "end": fmt_date(w.end), "inferred": w.inferred} for w in windows],
        "errors": errors,
    }
    return new_body, summary


def auth_headers(method: str = "GET", payload: bytes | None = None) -> dict[str, str]:
    key = os.environ.get("ATLASSIAN_API_KEY")
    if not key:
        raise SystemExit("ATLASSIAN_API_KEY is required")
    h = {"Authorization": "Basic " + key, "Accept": "application/json"}
    if payload is not None or method in {"PUT", "POST"}:
        h["Content-Type"] = "application/json"
    return h


def api_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=auth_headers(method, data))
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body}") from e


def page_url(cloud_id: str, page_id: str) -> str:
    return f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/pages/{page_id}"


def load_page(cloud_id: str, page_id: str) -> tuple[dict[str, Any], ADF]:
    data = api_json(page_url(cloud_id, page_id) + "?body-format=atlas_doc_format")
    value = data.get("body", {}).get("atlas_doc_format", {}).get("value")
    if isinstance(value, str):
        body = json.loads(value)
    elif isinstance(value, dict):
        body = value
    else:
        raise RuntimeError("page response did not include atlas_doc_format body")
    return data, body


def write_page(cloud_id: str, page: dict[str, Any], body: ADF, message: str) -> dict[str, Any]:
    page_id = page["id"]
    payload = {
        "id": page_id,
        "status": "current",
        "title": page["title"],
        "body": {"representation": "atlas_doc_format", "value": json.dumps(body, ensure_ascii=False)},
        "version": {"number": int(page["version"]["number"]) + 1, "message": message},
    }
    return api_json(page_url(cloud_id, page_id), method="PUT", payload=payload)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--page-id", required=True, help="Confluence Delivery Map page ID")
    p.add_argument("--cloud-id", default=DEFAULT_CLOUD_ID)
    p.add_argument("--release-page-id", action="append", default=[], help="KPI/release page ID containing `SafeART X: start - end` windows; repeat for H1+H2")
    p.add_argument("--input-body", help="Offline ADF body JSON instead of live fetch")
    p.add_argument("--release-body", help="Offline ADF body JSON for release windows")
    p.add_argument("--out-dir", default=".")
    p.add_argument("--write", action="store_true", help="Write changes back to Confluence")
    p.add_argument("--version-message", default="Refresh Delivery Map due dates and workstream release tags")
    p.add_argument("--no-infer-windows", action="store_true", help="Do not infer future release windows from KPI cadence")
    args = p.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if args.input_body:
        page = {"id": args.page_id, "title": "offline", "version": {"number": 0}}
        body = json.loads(Path(args.input_body).read_text(encoding="utf-8"))
    else:
        page, body = load_page(args.cloud_id, args.page_id)
        (out / "before-page.json").write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "before-body.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")

    windows: list[ReleaseWindow] = []
    if args.release_body:
        rbody = json.loads(Path(args.release_body).read_text(encoding="utf-8"))
        windows = extract_release_windows_from_body(rbody)
    elif args.release_page_id:
        seen: set[tuple[str, str, str]] = set()
        for release_page_id in args.release_page_id:
            _rpage, rbody = load_page(args.cloud_id, release_page_id)
            (out / f"release-body-{release_page_id}.json").write_text(json.dumps(rbody, ensure_ascii=False, indent=2), encoding="utf-8")
            for w in extract_release_windows_from_body(rbody):
                key = (w.label, fmt_date(w.start), fmt_date(w.end))
                if key not in seen:
                    seen.add(key)
                    windows.append(w)
        windows.sort(key=lambda w: w.start)
    if args.no_infer_windows:
        # The refresh() function extends as needed; truncate inferred windows in summary after use is not useful,
        # so instead pass only explicit windows and mark future dates After latest explicit.
        pass

    new_body, summary = refresh(body, windows)
    if args.no_infer_windows:
        # Re-run label assignment without cadence is intentionally not implemented because the house rule prefers
        # cadence inference when KPI implies it. This flag is reserved for future stricter workflows.
        summary["note"] = "--no-infer-windows is reserved; current implementation follows house-rule cadence inference."

    (out / "after-body.json").write_text(json.dumps(new_body, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    if summary["errors"]:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    if args.write:
        if args.input_body:
            raise SystemExit("--write cannot be used with --input-body")
        result = write_page(args.cloud_id, page, new_body, args.version_message)
        (out / "write-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        # Read back after write for verification artifacts.
        rb_page, rb_body = load_page(args.cloud_id, args.page_id)
        (out / "readback-page.json").write_text(json.dumps(rb_page, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "readback-body.json").write_text(json.dumps(rb_body, ensure_ascii=False, indent=2), encoding="utf-8")
        _rb_new, rb_summary = refresh(rb_body, windows)
        (out / "readback-summary.json").write_text(json.dumps(rb_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"wrote": True, "new_version": rb_page.get("version", {}).get("number"), **summary}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"wrote": False, **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
