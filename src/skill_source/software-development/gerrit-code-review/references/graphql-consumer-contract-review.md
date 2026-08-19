# GraphQL producer–consumer contract review

Use this reference when a Gerrit patch renames or removes GraphQL fields, arguments, enum values, input fields, or operations consumed by another repository.

## Why producer-only CI is insufficient

A producer schema can pass every local test while deployed consumers still submit operations that no longer validate. Treat live consumer source as authoritative contract evidence; a deleted or skipped producer-side contract test is not proof that the consumer migrated.

## Review procedure

1. **Pin both sides.** Record the exact producer patch-set revision and current consumer branch revision. Keep both checkouts clean.
2. **Inventory schema removals.** Compare the producer patch for removed or renamed fields, arguments, enum values, and inputs. Compatibility aliases count as preserved only when present in the production schema.
3. **Inspect direct consumer source.** Search the current consumer branch for old names in GraphQL documents and client types. Query Gerrit for related open or merged consumer changes; a design-only or Done Jira ticket is not implementation evidence.
4. **Validate real operations.** Extract actual consumer GraphQL documents and run the GraphQL validator against the producer's production schema object. Record each failing operation and exact error.
5. **Separate patch-specific failures.** If the producer parent already breaks other operations, distinguish inherited baseline failures from operations newly broken by the reviewed patch.
6. **Compare patch sets.** When the latest patch removes a cross-repository contract test, inspect the deleted test. If it validated real consumer operations, its removal is evidence of coverage regression—not restored compatibility.
7. **Calibrate rollout risk.** A breaking rename is acceptable only with an explicit paired consumer change and verified release ordering or atomic deployment. Otherwise retain a deprecated compatibility alias until consumers migrate.

## Deterministic Python probe

Run inside the producer environment and adapt extraction syntax to the consumer's GraphQL wrapper:

```python
import re
from pathlib import Path
from graphql import parse, validate
from producer.schema_registry import graphql_schema

consumer_root = Path("/tmp/consumer")
operations = [("path/to/queries.ts", "GET_ITEMS")]

failed = False
for relative_path, constant in operations:
    source = (consumer_root / relative_path).read_text(encoding="utf-8")
    match = re.search(
        rf"export const {constant} = gql<[^`]+>`(.*?)`;",
        source,
        re.DOTALL,
    )
    assert match is not None, f"Unable to extract {constant}"
    errors = validate(graphql_schema._schema, parse(match.group(1)))
    if errors:
        failed = True
        print(f"{constant}: INVALID")
        for error in errors:
            print(f"  - {error.message}")
    else:
        print(f"{constant}: valid")

raise SystemExit(1 if failed else 0)
```

## Finding shape

```text
[High] The schema change breaks current <consumer> operations

<producer file/line> removes or renames <field>. Current <consumer revision> still requests it in <operation/file/line>. Validating the real operation against this production schema returns <error>. <Prior patch-set contract test> was removed in the current patch set.

Please retain the old field as a deprecated compatibility alias, or provide the paired consumer change and verified atomic release ordering. Restore a cross-repository contract gate.
```

## Pitfalls

- Do not infer consumer migration from Jira status, a design page, or a planned frontend ticket; inspect source and Gerrit directly.
- Do not validate hand-written substitute queries when real consumer documents are available.
- Do not attribute all validation failures to the current patch when some originate in its parent.
- Do not accept a green producer suite as cross-repository evidence after the real contract test was deleted.
