# Gerrit REST-only review fallback

Use this when an exact local checkout is blocked, slow, or unavailable but Gerrit REST is reachable. This is a fallback, not a replacement for local checkout/tests when those are feasible.

## Fetch review inputs without git

```bash
TASK=/opt/data/plans/YYYY-MM-DD-review-<repo>-<change>
PROJECT='tcloud/safeart/thalos'
CHANGE='7926'
PS='3'
ENC_PROJECT=$(python3 - <<'PY'
from urllib.parse import quote
print(quote('tcloud/safeart/thalos', safe=''))
PY
)

# Change detail / CI / current revision
curl -sS -L "https://<host>/gerrit/changes/${ENC_PROJECT}~${CHANGE}/detail?o=CURRENT_REVISION&o=CURRENT_COMMIT&o=CURRENT_FILES&o=DETAILED_LABELS&o=MESSAGES&o=ALL_REVISIONS" \
  > "$TASK/change-detail.raw"
python3 - <<'PY'
import json, pathlib
p=pathlib.Path('$TASK/change-detail.raw')
s=p.read_text()
if s.startswith(")]}'"):
    s=s.split('\n',1)[1]
p.with_suffix('.json').write_text(json.dumps(json.loads(s), indent=2))
PY

# Patch file
curl -sS -L "https://<host>/gerrit/changes/${ENC_PROJECT}~${CHANGE}/revisions/${PS}/patch?download" \
  | base64 -d > "$TASK/change-${CHANGE}-ps${PS}.patch"

# Existing review comments
curl -sS -L "https://<host>/gerrit/changes/${ENC_PROJECT}~${CHANGE}/comments" > "$TASK/comments.raw"
```

## Fetch exact file content from a patch set

Gerrit's `.../files/<path>/content` endpoint returns base64-encoded file content. Save to a file and decode with `base64 -d`; this avoids line-wrapping/padding surprises that can happen if a script captures very long base64 output through command-result text.

```bash
file='thalos/core/mission_executor.py'
enc_file=$(python3 - <<PY
from urllib.parse import quote
print(quote('$file', safe=''))
PY
)
curl -sS -L "https://<host>/gerrit/changes/${ENC_PROJECT}~${CHANGE}/revisions/${PS}/files/${enc_file}/content" \
  -o "$TASK/${file//\//__}.b64"
base64 -d "$TASK/${file//\//__}.b64" > "$TASK/${file//\//__}"
```

## How to use this fallback in a review

- Label the coverage limit clearly: REST-only inspection can support code review findings, syntax checks, and source-grounded reasoning, but it does not replace running the repo's test suite.
- Still fetch surrounding contract files via `files/<path>/content`, not only the changed diff. For example, a mission logging patch may require reading the MA manager interface/implementation and the affected model classes.
- Run `python3 -m py_compile` on fetched Python files when dependencies are not needed for parsing.
- For added-line static scans, prefer a small Python regex over shell `grep` if credential redaction or shell quoting obscures output.
- Write the limitation into `/opt/data/plans/.../status.md` before finalizing.
