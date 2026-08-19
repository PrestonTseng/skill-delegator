# Diagnostic instrumentation review notes

Use this reference when reviewing patches that add diagnostics, stack sampling, tracing, profiling, verbose logging, or incident-capture hooks.

## Review focus

Diagnostic code is not automatically low-risk just because it is gated by config or intended for RCA. Check whether it can perturb the same runtime condition it is meant to observe.

Key questions:

- Is the diagnostic path called once per incident, or once per repeated warning/event?
- Is there a cooldown, rate limit, dedupe, or one-capture-per-burst guard?
- Are queues bounded or otherwise backpressured?
- Is expensive formatting deferred off the event loop / hot path?
- Even if formatting is deferred, can deferred work accumulate unboundedly during a burst?
- Does the test suite cover burst behavior, not only single-event behavior?
- Does the default config produce a reasonable output size in a realistic or minimally measured process?

## Stack-sampler / full-dump specific heuristic

If a patch preserves full thread stacks or sample rings on warnings:

1. Measure approximate dump size under the default sampling window.
2. Multiply mentally by the number of concurrent warning sources expected in a real incident burst.
3. Check whether repeated captures duplicate almost-identical large dumps.
4. Require a suppression counter or summary log for skipped duplicate captures so operators still know a burst happened.

Example lightweight measurement pattern:

```bash
uv run python - <<'PY'
import asyncio
from types import SimpleNamespace
from thalos.core.stack_sampler_service import StackSamplerService

async def main():
    settings = SimpleNamespace(
        stack_sampler_enabled=True,
        stack_sampler_interval_ms=50,
        stack_sampler_ring_seconds=10,
    )
    sampler = StackSamplerService(settings)
    await sampler.start()
    await asyncio.sleep(10.2)
    with sampler._lock:
        samples = list(sampler._samples)
    formatted = sampler._format_samples(samples)
    print('samples', len(samples))
    print('threads_per_last', len(samples[-1]['threads']) if samples else 0)
    print('formatted_bytes', len(formatted.encode()))
    await sampler.stop()

asyncio.run(main())
PY
```

Treat this as a sizing probe, not a production benchmark.

## Gerrit-ready finding pattern

```text
[Medium] Add burst control for diagnostic dumps

The patch captures/logs a full diagnostic snapshot for every warning above threshold. With the default sampling window, one dump is already sizable; in the real incident pattern, multiple related warnings can arrive in the same burst. This can duplicate large dumps, grow any unbounded queue, and add CPU/logging pressure during the same contention window being diagnosed.

Please add a cooldown / rate limit / one-capture-per-burst guard, preferably with a counter for suppressed duplicate snapshots. The normal concise warning can still log every event.
```
