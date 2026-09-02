# Policy provenance binding probes

Use these probes when an immutable artifact contains a decision, classification, cohort, or annotation governed by versioned policy bytes.

## Threat model

Output checksum verification proves only that the stored output matches its manifest. A free-form `policy_id` proves only that a string was stored. Neither proves that the decision was produced under the reviewed policy bytes.

A common integrity gap is:

1. publication writes an input hash for the policy and verifies it once;
2. the historical verifier later checks only that input hashes are well shaped;
3. the report consumer validates the annotation and `policy_id` but cannot see or does not check the policy hash;
4. a checksum-valid synthetic run with an absent or substituted policy commitment enters retention, cohort, or reconciliation results.

## Review procedure

1. Trace the policy bytes from config loading through manifest creation, publication verification, immutable-history loading, and every downstream interpreter.
2. Confirm the immutable run object preserves validated input-hash pairs rather than discarding them after schema validation.
3. For every governed output, require a binding such as `(policy_id, expected_sha256)` from an authoritative version registry or constant. A matching ID alone is insufficient.
4. Define legacy behavior narrowly: absence of the governed output may map to a legacy/unavailable state; presence of the output with a missing, duplicate, unknown, or mismatched policy hash must fail closed.
5. Verify downstream reports enforce the binding before using a decision in coverage, retention, cohorts, cash, or event rows.

## Minimum adversarial matrix

Create temporary runs with valid artifact/output checksums and vary only policy provenance:

| Governed output | Manifest policy hash | Expected result |
|---|---|---|
| absent | absent | documented legacy classification |
| present | exact reviewed hash | accepted |
| present | absent | reject |
| present | wrong valid SHA-256 | reject |
| present | hash under wrong input name | reject |
| present | unknown policy ID with known hash | reject |
| present | known policy ID with another version's hash | reject |

Also include a valid control proving that the hardened verifier still reads ordinary historical evidence.

## Reproduction shape

Print the manifest input hashes and the downstream interpreted result. A decisive vulnerable result looks like:

```text
input_hashes=[]
accepted_decision=PASS
retention=1.0
```

This is stronger than observing that publication-time verification exists: the relevant question is whether historical interpretation independently proves the policy binding.