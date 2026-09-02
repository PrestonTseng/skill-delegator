# Manual Live-Proof Review Before Scheduling

Use this after code approval when one authorized live execution has occurred and an independent reviewer must decide whether scheduling may begin. Do not run another live tick: reconstruct and verify the existing proof read-only.

## Closure matrix

1. **Pin the gate and HEAD**
   - Record the exact HEAD and live run directory.
   - Confirm the diff since the approved implementation contains only the expected proof/report change.
   - Keep cron creation, cron triggering, chart setters, and additional live ticks out of scope.

2. **Verify publication deeply**
   - Require the exact artifact set and no staging/residue files.
   - Run both the immutable-history verifier and, when available, the producer's final-publication verifier. The latter should reconstruct source-list commitments from preserved raw inputs, not merely validate digest syntax.
   - Recompute output hashes, review hash, input/config/strategy hashes, manifest path/time/status/strategy identity, terminal review action, and latest-copy byte equality.

3. **Reconstruct the event proof instead of trusting prose**
   - Build state immediately before the new run and after it.
   - Apply the deployed alert-selection rule to identify transitions. An existing order with no outcome row is operationally OPEN when that is the authoritative tick contract; do not require a synthetic OPEN outcome artifact.
   - Regenerate the exact alert payload in memory. Compare event-block count and byte length with the recorded stdout. Hash the regenerated payload when useful.
   - Do not claim transactional external delivery from reconstructed stdout. Immediate delivery remains best-effort unless a durable acknowledgement boundary exists.

4. **Verify exact projected accounting**
   - Check each fixed-notional projection independently and the aggregate.
   - Use an explicit high-precision local Decimal context for probe arithmetic. Ambient/default precision can make a mathematically exact reconciliation comparison appear false after intermediate rounding.
   - Check `gross - fees - slippage + funding == net` per row and in aggregate.

5. **Re-run daily reconciliation read-only**
   - Recover the exact explicit UTC window from the recorded output hash when the original wrapper used a second-granularity default and the timestamp was not written down: enumerate only the narrow plausible end-time range, canonical-serialize each read-only aggregate exactly as the CLI does, and match the recorded SHA-256.
   - Then run the actual wrapper with that explicit window.
   - Verify exit/stderr/stdout hash; UTC half-open denominator; tick status/blocker ledger; unique/duplicate/side counts; signal-frequency denominator and rounding; intervals; complete material event ledger; fixed order notionals; outcomes and exact cash; final exposure; filter/quality/parity counts; and distinct supporting versus in-window verified-run counts.
   - Snapshot artifact bytes, sizes, and mtimes before/after the wrapper and require identity.

6. **Verify historical immutability**
   - Use the recorded before/after prior-tree digest as temporal evidence.
   - Independently verify every prior manifest/artifact/review now and reconstruct the pre-live state. State clearly that present checksum validity corroborates, but does not replace, the recorded temporal digest.
   - Account for regular lock files separately from immutable run artifacts so file-count statements are unambiguous.

7. **Verify external state and prohibited seams**
   - Read current TradingView/CDP state only; compare exact symbol, resolution, chart type, and study names/IDs with recorded before/after state.
   - Structurally search source for broker/order APIs, chart setters, services, databases, queues, dashboards, and direct message delivery. Distinguish approved read-only market adapters (`state`, `ohlcv`) from mutation APIs.

8. **Verify runtime margin**
   - Report observed shell duration and manifest start-to-completion duration separately.
   - Compute the wrapper's TERM plus kill-grace envelope and its margin under the scheduler hard ceiling.
   - Treat the first controlled scheduled trigger as deployment-level timeout/delivery verification even when cron creation is approved.

## Decision artifact

Write separate Spec, Quality, and Integrity verdicts; CRITICAL/HIGH/MEDIUM/LOW findings including `none`; an explicit cron-gate decision; accepted best-effort-delivery limits; exact commands/results; and whether the approval file is ignored or untracked. Approval should authorize only the next gate (cron creation plus controlled trigger checks), with pause/remove conditions for timeout, duplicate event, delivery anomaly, unexpected mutation, or integrity failure.
