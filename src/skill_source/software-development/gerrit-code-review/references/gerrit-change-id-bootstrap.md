# Gerrit Change-Id bootstrap and push verification

Use this when preparing a first Gerrit review commit or when `HEAD` lacks a `Change-Id` trailer.

## Preflight

```bash
git status --short --branch
git show -s --format='%B' HEAD
test -x "$(git rev-parse --git-dir)/hooks/commit-msg"
```

Require a trailer matching `^Change-Id: I[0-9a-f]{40}$` before pushing.

## Install the hook

Preferred order:

1. Copy a known-good hook from the main checkout when working in a linked worktree.
2. Download Gerrit's HTTPS hook endpoint:

```bash
hook=/tmp/gerrit-commit-msg
curl -fsSL "https://<host>/<context>/tools/hooks/commit-msg" -o "$hook"
test -s "$hook"
case "$(sed -n '1p' "$hook")" in '#!'*) ;; *) exit 1;; esac
install -m 0755 "$hook" "$(git rev-parse --git-dir)/hooks/commit-msg"
```

3. Use Gerrit's standard SCP hook endpoint when the server enables it:

```bash
scp -P 29418 <user>@<host>:hooks/commit-msg "$(git rev-parse --git-dir)/hooks/commit-msg"
chmod +x "$(git rev-parse --git-dir)/hooks/commit-msg"
```

Do not treat an SCP connection closure as a permanent tool limitation; try the HTTPS endpoint.

## Amend and verify

```bash
git commit --amend --no-edit
git show -s --format='%H%n%B' HEAD
git diff HEAD^..HEAD --check
test -z "$(git status --porcelain)"
```

The amend should change only commit metadata when the source tree was already clean.

## Push and read back

```bash
git push origin HEAD:refs/for/<target-branch>
```

Capture the returned change number, then query Gerrit and confirm:

- project and target branch;
- change status;
- current patch-set number;
- revision SHA equals local `HEAD`;
- current patch-set ref.

Report whether the push created a new change or updated an existing one. Do not infer success solely from the local push exit code or banner.
