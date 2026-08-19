# TAPAS Mission cancellation — ownership-first worked example

This reference captures a reusable planning lesson from a Thalos/Unicorn Mission-cancellation review. Revalidate all exact code, timeouts, and FSM transitions before implementation; those details are volatile.

## Initial design mistake

The first proposal treated slow external synchronization as a reason to add:

- HTTP 202 and a `CANCELING` state;
- background reconciliation tasks;
- an in-process operation registry/history;
- new UI behavior.

That design was internally coherent but ignored the existing ownership contract: JPS already owned durable Mission state and called SS synchronously for `LOCKED`/`ACTIVE` cancellation. SS was expected to synchronize the result back to JPS before returning HTTP 200. Adding an asynchronous public state expanded scope without first proving the current contract was insufficient.

## Corrected ownership map

- **JPS/Unicorn:** durable Mission data owner and user-visible source.
- **SS/Thalos:** short-retention runtime executor and safety cleanup owner.
- **Scheduled Mission cancellation:** owned by JPS.
- **Locked/active Mission cancellation:** JPS calls SS; SS performs local cancellation and calls JPS's cancel endpoint; only JPS confirmation permits SS HTTP 200.
- **JPS cache update/removal event:** observation from JPS, not a new command that should callback JPS.

## Key semantic correction

Because SS keeps only a short Mission window, `executor not found` is a successful **local** outcome. It means SS should skip duplicate local cleanup. It does not prove JPS has persisted `CANCELED`.

Therefore:

```text
SS local not-found
  -> local goal satisfied
  -> still send mandatory JPS cancel command
  -> return 200 only after JPS reports canceled or absent
```

For a JPS-originated cache event:

```text
JPS event + SS local not-found
  -> informational no-op
  -> do not callback JPS
```

## Minimal cross-repository repair

### Runtime service

- Distinguish API source from owner-event source.
- Re-read executor ownership inside the vehicle lock.
- Perform local transition/cleanup once.
- Release the lock before external HTTP.
- Remove GET-before-cancel; use one owner POST.
- Treat owner 404 as goal satisfied where absence is accepted.
- Propagate owner timeout/5xx/conflict instead of logging and returning success.
- Keep auxiliary ADS notification best effort only if local safety and JPS truth define user-visible success.

### Durable owner

Add an explicit idempotent self-transition:

```text
CANCELED -> CANCEL -> CANCELED
```

Do not swallow unrelated state conflicts. This one transition supports duplicate request, response-loss retry, and racing callbacks without a sender-side tombstone cache.

## Timeout lesson

The reviewed path serialized multiple remote operations, each with its own timeout and retries, producing a much larger total than the caller deadline. The minimal remedy was to:

- remove redundant preflight network reads;
- make independent external steps concurrent;
- use one synchronous owner attempt;
- rely on safe end-to-end caller retry;
- compare the measured path against the real upstream timeout.

## Essential tests

- local present and owner newly canceled;
- local absent but owner still needs cancellation;
- local absent and owner already canceled;
- owner absent;
- owner failure prevents false 200;
- retry after local cleanup performs only owner synchronization;
- response committed at owner but response lost, then retry;
- API/event race performs one local transition;
- owner event never creates a callback loop;
- independent remote delays overlap rather than add serially;
- following runtime work is not held behind external HTTP;
- durable owner state is read back before claiming success.

## General lesson

Before adding distributed-operation infrastructure, ask whether idempotency can be composed from:

1. goal-oriented local absence;
2. ownership re-check under lock;
3. one idempotent durable-owner command;
4. strict success propagation;
5. end-to-end retry.

If those five properties satisfy the contract, they are usually more maintainable than a new asynchronous state machine.
