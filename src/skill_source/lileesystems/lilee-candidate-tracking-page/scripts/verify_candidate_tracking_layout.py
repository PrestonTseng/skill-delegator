#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path


def text(node):
    if node.get('type') == 'text':
        return node.get('text', '')
    return ''.join(text(c) for c in node.get('content', []) or [])


def load_doc_from_page(page_id: str, cloud_id: str):
    token = os.environ.get('ATLASSIAN_API_KEY')
    if not token:
        raise SystemExit('ATLASSIAN_API_KEY is required for --page-id mode')
    url = f'https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2/pages/{page_id}?body-format=atlas_doc_format'
    req = urllib.request.Request(url, headers={'Authorization': 'Basic ' + token, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    return json.loads(payload['body']['atlas_doc_format']['value']), payload.get('title')


def load_doc_from_file(path: Path):
    raw = path.read_text(encoding='utf-8')
    data = json.loads(raw)
    if isinstance(data, dict) and data.get('type') == 'doc':
        return data, path.name
    if isinstance(data, dict) and 'body' in data and 'atlas_doc_format' in data['body']:
        return json.loads(data['body']['atlas_doc_format']['value']), path.name
    raise SystemExit(f'Unsupported JSON shape in {path}')


def extract_tables(doc):
    current_heading = None
    heading_order = []
    tables = []
    for node in doc.get('content', []):
        if node.get('type') == 'heading':
            ht = text(node).strip()
            if node.get('attrs', {}).get('level') == 1:
                heading_order.append(ht)
            current_heading = ht
        elif node.get('type') == 'table':
            rows = node.get('content', [])
            first_row = rows[0].get('content', []) if rows else []
            colwidths = []
            for cell in first_row:
                cw = cell.get('attrs', {}).get('colwidth')
                colwidths.append(cw[0] if isinstance(cw, list) and cw else None)
            row_labels = []
            for row in rows[1:]:
                cells = row.get('content', [])
                row_labels.append(text(cells[0]).strip() if cells else '')
            tables.append({
                'heading': current_heading,
                'width': node.get('attrs', {}).get('width'),
                'layout': node.get('attrs', {}).get('layout'),
                'columns': len(first_row),
                'rows': len(rows),
                'first_row_colwidths': colwidths,
                'row_labels': row_labels,
            })
    return heading_order, tables


def text_nodes(node):
    if isinstance(node, dict):
        if node.get('type') == 'text':
            yield node
        for child in node.get('content', []) or []:
            yield from text_nodes(child)
    elif isinstance(node, list):
        for child in node:
            yield from text_nodes(child)


def has_strong_mark(text_node):
    return any(mark.get('type') == 'strong' for mark in text_node.get('marks', []) or [])


def check_candidate_conventions(doc):
    problems = []

    def walk_status(node):
        if isinstance(node, dict):
            if node.get('type') == 'status':
                attrs = node.get('attrs', {})
                if attrs.get('text') == 'pending' and attrs.get('color') != 'neutral':
                    problems.append({
                        'type': 'pending_status_color',
                        'expected': 'neutral',
                        'actual': attrs.get('color'),
                        'text': attrs.get('text'),
                    })
            for child in node.get('content', []) or []:
                walk_status(child)
        elif isinstance(node, list):
            for child in node:
                walk_status(child)

    walk_status(doc)

    current_heading = None
    for node in doc.get('content', []):
        if node.get('type') == 'heading':
            current_heading = text(node).strip()
            continue
        if node.get('type') != 'table' or not (current_heading or '').startswith('Scoring —'):
            continue
        for row_index, row in enumerate(node.get('content', [])[1:], start=1):
            cells = row.get('content', [])
            row_label = text(cells[0]).strip() if cells else ''
            row_title = text(cells[1]).strip() if len(cells) > 1 else ''
            if row_title == 'Comments':
                problems.append({
                    'type': 'scoring_table_comments_row',
                    'heading': current_heading,
                    'row_index': row_index,
                })
            if len(row_label) == 1 and row_label.isalpha() and row_label.isupper():
                for cell_index, cell in enumerate(cells):
                    non_bold = [tn.get('text', '') for tn in text_nodes(cell) if tn.get('text') and not has_strong_mark(tn)]
                    if non_bold:
                        problems.append({
                            'type': 'aggregate_row_not_bold',
                            'heading': current_heading,
                            'row_label': row_label,
                            'cell_index': cell_index,
                            'text': ''.join(non_bold),
                        })
    return problems


def compare(spec, actual, doc):
    problems = []
    if spec['heading_order'] != actual['heading_order']:
        problems.append({
            'type': 'heading_order',
            'expected': spec['heading_order'],
            'actual': actual['heading_order'],
        })
    if len(spec['tables']) != len(actual['tables']):
        problems.append({
            'type': 'table_count',
            'expected': len(spec['tables']),
            'actual': len(actual['tables']),
        })
    for i, expected in enumerate(spec['tables']):
        if i >= len(actual['tables']):
            break
        observed = actual['tables'][i]
        for key in ['heading', 'width', 'layout', 'columns', 'rows', 'first_row_colwidths', 'row_labels']:
            if expected.get(key) != observed.get(key):
                problems.append({
                    'type': f'table[{i}].{key}',
                    'expected': expected.get(key),
                    'actual': observed.get(key),
                })
    problems.extend(check_candidate_conventions(doc))
    return problems


def main():
    ap = argparse.ArgumentParser(description='Verify a candidate tracking page layout against the canonical spec.')
    ap.add_argument('--spec', default=str(Path(__file__).resolve().parents[1] / 'references' / 'layout-spec.json'))
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--page-id')
    src.add_argument('--file')
    ap.add_argument('--cloud-id', default=None)
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding='utf-8'))
    if args.page_id:
        cloud_id = args.cloud_id or spec.get('cloud_id')
        doc, label = load_doc_from_page(args.page_id, cloud_id)
    else:
        doc, label = load_doc_from_file(Path(args.file))

    heading_order, tables = extract_tables(doc)
    problems = compare(spec, {'heading_order': heading_order, 'tables': tables}, doc)
    result = {
        'label': label,
        'ok': not problems,
        'problem_count': len(problems),
        'problems': problems,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not problems else 1)


if __name__ == '__main__':
    main()
