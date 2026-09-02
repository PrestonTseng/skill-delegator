# Strict YAML Configuration Review

Use this checklist when a CLI promises fail-closed validation of YAML configuration.

## Review boundary

A successful schema pass is not enough. Exercise the complete path:

`bytes → UTF-8 decode → YAML construction → duplicate-key policy → schema validation → semantic/path normalization → model construction → CLI error boundary`

Every malformed input at this boundary should produce the documented configuration-error exit code, filename-bearing stderr, empty stdout when required, and no traceback.

## Adversarial matrix

Test each required configuration filename, not only the first document:

- invalid UTF-8;
- malformed YAML syntax;
- duplicate keys at the document root, nested mappings, and mappings inside sequences;
- unhashable mapping keys such as `? [a, b]\n: c`;
- hashable non-string keys (`1`, `true`, `null`, timestamps) to ensure schema diagnostics do not crash;
- wrong root/container/scalar types and malformed nested items;
- path strings containing NUL (`"\\0"`) in every path-like field;
- missing files, unreadable paths, and directories where files are expected.

Pair hostile cases with valid controls so a broken fixture or over-broad rejection cannot masquerade as fail-closed behavior.

## Duplicate and unhashable YAML keys

PyYAML's default mapping construction permits duplicate keys. A strict loader can subclass `yaml.SafeLoader`, flatten each mapping, construct keys, and reject duplicates before assigning values.

Before `if key in mapping`, explicitly call `hash(key)`. Convert only the resulting `TypeError` into `yaml.constructor.ConstructorError`, preserving the existing duplicate-key branch. The outer YAML error boundary can then attach the filename and convert it into the domain configuration error.

Review the fix as a narrow seam:

1. inspect the exact remediation diff;
2. prove the unhashable-key case now exits through the YAML/configuration boundary;
3. rerun root and nested duplicate-key controls;
4. repeat the hostile key against all required YAML files.

## Path-string trap

A JSON Schema rule such as `{ "type": "string", "minLength": 1 }` accepts strings that cannot name filesystem paths. In particular, YAML `"\\0"` becomes a Python string containing NUL.

Typical failure modes:

- `Path.resolve()` raises `ValueError: ... embedded null character`, escaping a CLI that catches only the domain error;
- a deferred path such as `skill_root` is accepted into an immutable model even though later filesystem use is impossible;
- fixture-specific containment rejects one target path, while the same malformed value crashes when the fixture policy is disabled.

Probe every path-like field under every relevant policy branch. The durable fix is explicit semantic validation of path strings before normalization, plus conversion of expected path-normalization exceptions into filename- and field-bearing configuration errors. Catching `ValueError` only at the CLI is insufficient if unusable paths can still be accepted.

## Approval rule

Do not approve merely because the originally reported malformed case is closed. After closure, broaden one layer to equivalent malformed scalar and path classes. Any reproducible exit-1 traceback or accepted unusable model is a spec blocker when the contract requires all malformed configuration to fail with a controlled exit code.
