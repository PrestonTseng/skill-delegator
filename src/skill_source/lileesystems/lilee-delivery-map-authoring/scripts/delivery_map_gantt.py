#!/usr/bin/env python3
"""Generate a Mermaid Gantt chart from a Lilee Delivery Map Confluence ADF page.

Default output is a `.mmd` Mermaid file plus a `.txt` copy for Discord upload.

Auth for live Confluence fetch: set ATLASSIAN_API_KEY to a base64 `email:api_token`
string accepted by Atlassian Basic auth. The script uses only Python stdlib.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CLOUD_ID = "302f7dfa-a172-4986-b4ae-efd7021f110a"
ISO_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
WS_RE = re.compile(r"\bWS\s*(\d+)\s*\.\s*(\d+)\b", re.I)
ADD_RE = re.compile(r"^(?P<base>.+?)\s*\+\s*(?P<days>\d+)\s*D\s*$", re.I)
MAX_RE = re.compile(r"^max\((?P<args>.+)\)$", re.I)
RELEASE_WINDOW_RE = re.compile(
    r"SafeAR[Tt]\s+(?P<version>\d+\.\d+)\s*[:：]\s*"
    r"(?P<start>20\d{2}-\d{2}-\d{2})\s*[-–—]\s*(?P<end>20\d{2}-\d{2}-\d{2})"
)

ADF = dict[str, Any]
FUNCTION_MARKER = {
    "PD": "active",
    "BE": "crit",
    "FE": "done",
}


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def fmt_date(d: dt.date) -> str:
    return d.isoformat()


def add_business_days(start: dt.date, days: int) -> dt.date:
    """Add Mon-Fri business days, exclusive of the start date."""
    cur = start
    for _ in range(days):
        cur += dt.timedelta(days=1)
        while cur.weekday() >= 5:
            cur += dt.timedelta(days=1)
    return cur


def previous_business_days_inclusive(end: dt.date, duration: int) -> dt.date:
    """Return start for a duration-business-day window ending on `end`, inclusive."""
    cur = end
    for _ in range(max(duration - 1, 0)):
        cur -= dt.timedelta(days=1)
        while cur.weekday() >= 5:
            cur -= dt.timedelta(days=1)
    return cur


def next_business_day(day: dt.date) -> dt.date:
    cur = day + dt.timedelta(days=1)
    while cur.weekday() >= 5:
        cur += dt.timedelta(days=1)
    return cur


def sanitize_mermaid_text(text: str) -> str:
    return (
        " ".join(text.split())
        .replace(":", " -")
        .replace("#", "No.")
        .replace(";", ",")
        .replace("|", "/")
    )


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


def canonical_ws(ref: str) -> str:
    m = WS_RE.search(ref)
    if not m:
        raise ValueError(f"not a work-item reference: {ref}")
    return f"WS{int(m.group(1))}.{int(m.group(2))}"


def first_iso(text: str) -> dt.date | None:
    m = ISO_RE.search(text)
    return parse_date(m.group(1)) if m else None


def extract_duration_days(expr: str | None, default_duration: int) -> int:
    if not expr:
        return default_duration
    m = ADD_RE.match(expr.strip())
    if m:
        return int(m.group("days"))
    return default_duration


@dataclass
class WorkItem:
    ws_id: str
    ws_num: int
    item_num: int
    workstream_title: str
    function: str
    title: str
    due_text: str
    due_lhs: str | None = None
    resolved_due: dt.date | None = None
    dependencies: list[str] = field(default_factory=list)
    duration_days: int = 5

    @property
    def sort_key(self) -> tuple[int, int]:
        return (self.ws_num, self.item_num)


@dataclass
class ReleaseWindow:
    label: str
    start: dt.date
    end: dt.date


def iter_tables_with_headings(body: ADF):
    current_heading: tuple[int, ADF, str] | None = None
    for idx, node in enumerate(body.get("content", [])):
        if node.get("type") == "heading":
            htext = adf_plain_text(node).strip()
            m = re.match(r"^(?P<num>\d+)\.\s+(?P<title>.+)$", htext)
            if m:
                # Strip trailing release status from text when it was concatenated during ADF text extraction.
                title = re.sub(r"\s+SafeAR[Tt]\s+\d+\.\d+\s*$", "", m.group("title")).strip()
                title = re.sub(r"\s+product refinement\s*$", "", title, flags=re.I).strip()
                current_heading = (idx, node, title)
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


def left_hand_expression(text: str) -> str | None:
    if not text:
        return None
    lhs = text.split("=", 1)[0].strip() if "=" in text else text.strip()
    if ADD_RE.match(lhs) or MAX_RE.match(lhs) or WS_RE.fullmatch(lhs.replace(" ", "")):
        return lhs
    if WS_RE.search(lhs) and "+" in lhs:
        return lhs
    return None


def deps_from_expr(expr: str | None) -> list[str]:
    if not expr:
        return []
    deps: list[str] = []
    for m in WS_RE.finditer(expr):
        ws = f"WS{int(m.group(1))}.{int(m.group(2))}"
        if ws not in deps:
            deps.append(ws)
    return deps


def extract_work_items(body: ADF, from_ws: int = 1) -> dict[str, WorkItem]:
    items: dict[str, WorkItem] = {}
    for (_heading_idx, _heading_node, heading_title), _table_idx, table in iter_tables_with_headings(body):
        rows = [r for r in table.get("content", []) if r.get("type") == "tableRow"]
        if not rows:
            continue
        headers = [adf_plain_text(c).strip() for c in row_cells(rows[0])]
        work_col = find_col(headers, ["Work Item"])
        function_col = find_col(headers, ["Function"])
        due_col = find_col(headers, ["Due Date"])
        if work_col is None or function_col is None or due_col is None:
            continue
        for row in rows[1:]:
            cells = row_cells(row)
            if max(work_col, function_col, due_col) >= len(cells):
                continue
            work_text = adf_plain_text(cells[work_col]).strip()
            m = WS_RE.search(work_text)
            if not m:
                continue
            ws_num = int(m.group(1))
            item_num = int(m.group(2))
            if ws_num < from_ws:
                continue
            ws_id = f"WS{ws_num}.{item_num}"
            title = re.sub(r".*?WS\s*\d+\s*\.\s*\d+\s*\]?", "", work_text, count=1, flags=re.I).strip(" -–—\n[]")
            if not title:
                title = work_text
            fn_text = adf_plain_text(cells[function_col]).strip().upper()
            fn = "PD" if "PD" in fn_text else "BE" if "BE" in fn_text else "FE" if "FE" in fn_text else fn_text or "UNK"
            due_text = " ".join(adf_plain_text(cells[due_col]).split())
            lhs = left_hand_expression(due_text)
            duration = extract_duration_days(lhs, default_duration=5)
            items[ws_id] = WorkItem(
                ws_id=ws_id,
                ws_num=ws_num,
                item_num=item_num,
                workstream_title=heading_title,
                function=fn,
                title=title,
                due_text=due_text,
                due_lhs=lhs,
                dependencies=deps_from_expr(lhs),
                duration_days=duration,
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
            if item.due_lhs:
                item.resolved_due = self.eval_expr(item.due_lhs)
                return item.resolved_due
            item.resolved_due = first_iso(item.due_text)
            return item.resolved_due
        finally:
            self.stack.pop()

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
        if WS_RE.search(expr):
            d = self.resolve_item(canonical_ws(expr))
            if d is None:
                raise ValueError(f"dependency has no resolved date: {expr}")
            return d
        d = first_iso(expr)
        if d:
            return d
        raise ValueError(f"unsupported due-date expression: {expr}")


def version_tuple(label_or_version: str) -> tuple[int, int] | None:
    m = re.search(r"(\d+)\.(\d+)", label_or_version)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def extract_release_windows_from_body(body: ADF) -> list[ReleaseWindow]:
    text = adf_plain_text(body)
    windows: list[ReleaseWindow] = []
    seen: set[str] = set()
    for m in RELEASE_WINDOW_RE.finditer(text):
        label = f"SafeART {m.group('version')}"
        if label in seen:
            continue
        seen.add(label)
        windows.append(ReleaseWindow(label, parse_date(m.group("start")), parse_date(m.group("end"))))
    windows.sort(key=lambda w: w.end)
    return windows


def filter_release_windows(
    windows: list[ReleaseWindow],
    min_version: str | None = None,
    max_version: str | None = None,
) -> list[ReleaseWindow]:
    lo = version_tuple(min_version) if min_version else None
    hi = version_tuple(max_version) if max_version else None
    result: list[ReleaseWindow] = []
    for w in windows:
        v = version_tuple(w.label)
        if v is None:
            continue
        if lo and v < lo:
            continue
        if hi and v > hi:
            continue
        result.append(w)
    return result


def auth_headers(method: str = "GET", payload: bytes | None = None) -> dict[str, str]:
    key = os.environ.get("ATLASSIAN_API_KEY")
    if not key:
        raise SystemExit("ATLASSIAN_API_KEY is required for live Confluence fetch")
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


def load_page_body(cloud_id: str, page_id: str) -> ADF:
    data = api_json(page_url(cloud_id, page_id) + "?body-format=atlas_doc_format")
    value = data.get("body", {}).get("atlas_doc_format", {}).get("value")
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, dict):
        return value
    raise RuntimeError(f"page {page_id} response did not include atlas_doc_format body")


def load_body(path_or_page_id: str, cloud_id: str) -> ADF:
    p = Path(path_or_page_id)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        # Accept either raw ADF body or a saved API page response.
        if data.get("type") == "doc":
            return data
        value = data.get("body", {}).get("atlas_doc_format", {}).get("value")
        if isinstance(value, str):
            return json.loads(value)
        if isinstance(value, dict):
            return value
        raise RuntimeError(f"{p} is not a raw ADF body or Confluence page JSON")
    return load_page_body(cloud_id, path_or_page_id)


def resolve_all(items: dict[str, WorkItem]) -> tuple[list[WorkItem], list[str]]:
    resolver = Resolver(items)
    errors: list[str] = []
    for item in sorted(items.values(), key=lambda i: i.sort_key):
        try:
            resolver.resolve_item(item.ws_id)
        except Exception as e:
            errors.append(f"{item.ws_id}: {e}")
    return [i for i in sorted(items.values(), key=lambda i: i.sort_key) if i.resolved_due], errors


def task_start(item: WorkItem, items: dict[str, WorkItem]) -> dt.date:
    deps = [items[d].resolved_due for d in item.dependencies if d in items and items[d].resolved_due]
    if deps:
        return next_business_day(max(d for d in deps if d))
    assert item.resolved_due is not None
    return previous_business_days_inclusive(item.resolved_due, item.duration_days)


def checkpoint_id(label: str, due: dt.date, used: set[str]) -> str:
    base = f"cp_{due.strftime('%m%d')}"
    if base not in used:
        used.add(base)
        return base
    version = re.sub(r"\D+", "", label)
    candidate = f"{base}_{version or len(used)}"
    used.add(candidate)
    return candidate


def render_gantt(items: list[WorkItem], item_map: dict[str, WorkItem], windows: list[ReleaseWindow], title: str) -> str:
    lines = [
        "gantt",
        f"    title {sanitize_mermaid_text(title)}",
        "    dateFormat  YYYY-MM-DD",
        "    axisFormat  %Y/%m/%d",
        "    todayMarker true",
        "    excludes weekends",
        "    tickInterval 2week",
        "",
    ]

    if windows:
        lines.append("    section Checkpoints")
        used_ids: set[str] = set()
        for w in windows:
            cp_id = checkpoint_id(w.label, w.end, used_ids)
            lines.append(f"    {w.label} Release :milestone, {cp_id}, {fmt_date(w.end)}, 0d")
        lines.append("")

    current_ws: int | None = None
    for item in items:
        if item.ws_num != current_ws:
            current_ws = item.ws_num
            lines.append(f"    section WS{item.ws_num} - {sanitize_mermaid_text(item.workstream_title)}")
        marker = FUNCTION_MARKER.get(item.function, "")
        marker_part = f":{marker}, " if marker else ":"
        start = task_start(item, item_map)
        end = item.resolved_due
        assert end is not None
        label = sanitize_mermaid_text(f"{item.ws_id} [{item.function}] {item.title} - due {fmt_date(end)}")
        # Use `1d` for same-day tasks to avoid renderer-specific zero-length task behavior.
        if start == end:
            lines.append(f"    {label} {marker_part}{fmt_date(start)}, 1d")
        else:
            lines.append(f"    {label} {marker_part}{fmt_date(start)}, {fmt_date(end)}")
        # blank line between sections for readability, inserted on next section boundary by leaving compact here
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--page-id", required=True, help="Delivery Map page ID or path to saved ADF/page JSON")
    ap.add_argument("--cloud-id", default=DEFAULT_CLOUD_ID)
    ap.add_argument("--release-page-id", action="append", default=[], help="KPI page ID or saved ADF/page JSON; repeat for H1/H2")
    ap.add_argument("--checkpoint-min-version", help="Optional minimum SafeART release version to include, e.g. 0.20")
    ap.add_argument("--checkpoint-max-version", help="Optional maximum SafeART release version to include, e.g. 0.24")
    ap.add_argument("--from-ws", type=int, default=6, help="First workstream number to include. Default: 6")
    ap.add_argument("--title", default="Delivery Map Gantt")
    ap.add_argument("--out", default="delivery-map-gantt.mmd", help="Output .mmd path. A .txt copy is always created beside it unless --txt-out is set.")
    ap.add_argument("--txt-out", help="Output .txt copy path for Discord upload")
    ap.add_argument("--summary-out", help="Optional JSON summary path")
    args = ap.parse_args(argv)

    body = load_body(args.page_id, args.cloud_id)
    item_map = extract_work_items(body, from_ws=args.from_ws)
    items, errors = resolve_all(item_map)
    if errors:
        print("Failed to resolve one or more due dates:", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 2

    windows: list[ReleaseWindow] = []
    seen_windows: set[tuple[str, str]] = set()
    for release_source in args.release_page_id:
        rbody = load_body(release_source, args.cloud_id)
        for w in extract_release_windows_from_body(rbody):
            key = (w.label, fmt_date(w.end))
            if key not in seen_windows:
                seen_windows.add(key)
                windows.append(w)
    windows.sort(key=lambda w: w.end)
    windows = filter_release_windows(windows, args.checkpoint_min_version, args.checkpoint_max_version)

    mmd = render_gantt(items, item_map, windows, args.title)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(mmd, encoding="utf-8")
    txt_out = Path(args.txt_out) if args.txt_out else out.with_suffix(".txt")
    txt_out.parent.mkdir(parents=True, exist_ok=True)
    txt_out.write_text(mmd, encoding="utf-8")

    summary = {
        "items": len(items),
        "from_ws": args.from_ws,
        "missing_due_dates": 0,
        "checkpoints": [{"label": w.label, "release_due": fmt_date(w.end)} for w in windows],
        "mmd": str(out),
        "txt": str(txt_out),
    }
    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
