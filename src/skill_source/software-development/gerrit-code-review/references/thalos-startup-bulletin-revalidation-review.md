# Thalos startup bulletin revalidation review

Use this note when reviewing changes that re-check persisted TSR bulletins against configured sub-block maximum speeds during Thalos startup.

## Requirement mapping

Ground the review in the live Jira/spec revision. The accepted contract for this class is:

- startup revalidates persisted operational and not-enforced bulletins after configured sub-block maximum speeds change;
- speed mismatches remain non-blocking because bulletin priority overrides block maximum speed;
- mismatches produce local system warning logs only;
- startup revalidation must not mutate bulletin state, create persisted bulletin-log entries, notify JPS/Unicorn/Crystal, or make an offline consumer a startup dependency;
- expired bulletins are outside the revalidation set.

Map product terms to the current Thalos state model explicitly:

- Not Enforced → `DISABLED`
- Enforced, scheduled → `SCHEDULED`
- Enforced, active → `EFFECTIVE`
- Excluded → `EXPIRED`

## Review procedure

1. Fetch the exact patch set and live Jira issue. If earlier patch-set descriptions mention dispatcher notification but Jira later removes it, use the revised Jira/spec as authoritative.
2. Compare the current patch set with both its parent and the preceding meaningful patch set; naming/refactor follow-ups can hide behavior added earlier.
3. Inspect startup ordering around persisted bulletin/log loading, revalidation, overdue timer reconciliation, and log-push startup.
4. Verify warning evaluation reuses the existing lane, normalized half-open milepost overlap, and per-sub-block `max_speed` logic.
5. Exercise `BulletinService.start()` and assert:
   - every eligible state emits the expected warning;
   - expired and non-exceeding bulletins do not;
   - bulletin models are unchanged;
   - persisted bulletin-log state is unchanged;
   - no consumer notification method is called.
6. Confirm create/enforce warning behavior remains unchanged when evaluation and recording helpers are separated.
7. Run layered verification:

```bash
uv sync --group dev
uv run pytest test/unit_test/bulletin_service/test_startup_max_speed_revalidation.py \
  test/unit_test/bulletin_service/test_evaluate_sub_block_speed_limit_warnings.py -q
uv run pytest test/unit_test/bulletin_service -q
uv run pyright thalos/core/bulletin_service.py \
  test/unit_test/bulletin_service/test_startup_max_speed_revalidation.py \
  test/unit_test/bulletin_service/test_evaluate_sub_block_speed_limit_warnings.py
./build.sh --run-tests
```

Also run `git diff --check`, an added-line security scan, and confirm the final worktree remains on the exact reviewed revision.

## Pitfalls

- Do not infer notification requirements from an obsolete commit message when Jira/spec removed dispatcher notification.
- Do not treat a warning as requiring a persisted bulletin audit log; that can reintroduce consumer coupling during startup.
- Do not claim “no mutation” from state assertions alone; inspect persisted log state and outbound service calls too.
- A pure helper test does not prove startup ordering or consumer independence; exercise the service lifecycle.
- Full CI passing does not replace explicit requirement/state mapping.
