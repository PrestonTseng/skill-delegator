# TAPAS / SafeART KPI boundary checks

Use these checks after reading the live Delivery Map and spec. They are wording guardrails, not substitutes for current sources.

## TSR, Form A, and Form B

Keep these capabilities distinct instead of collapsing them into “TSR complete”:

- trackmap rendering and real-time state updates;
- per-block maximum-speed advisory validation;
- Line/Track semantic clarification for precise bulletin location;
- overspeed detection and operator alerting;
- Form A activation while a vehicle is already in-zone;
- Form B request creation, N+1 MA gate, dispatcher approval/reminders, audit, invalidation, and consumed-state visibility.

Use source-faithful terms such as DOM9/zero-extension MA only when the live plan includes them. Do not expand a KPI label into reject/retry or degraded-mode behavior unless those branches are in the linked scope.

## Seshat 2.0

Describe the user-visible analysis output and evidence traceability, not only “query/filter/display.” Useful distinctions:

- bounded historical query, topic selection, payload-field filtering, pagination, and raw payload inspection;
- selected ICD-aware display without promising semantic support for every field;
- multi-topic correlation with markers traceable to topic, timestamp, and payload;
- Mission/MA timeline using Type 17 schedule, Type 18 execution state, Type 3 virtual MA departure signal, and Type 2 ADS speed;
- replay that distinguishes known, unknown, stale, and missing data.

The Type 3 departure signal is virtual inside MA. Do not describe it as Type 7 physical WSS signal state.

## WSS/PLC redesign

Before preserving any KPI promise to replace Alpha PLC logic or solve all known issues, compare it with the live Delivery Map gates. If current planning sequences current-state study, issue-family RCA, cited rule constraints, safe shared-resource logic, spec publication, and scenario validation before implementation, the KPI should commit to the reviewable gate due in that period—not to an unsupported rollout.

## Next-generation TAPAS architecture

The redesign is ongoing. Prefer verifiable design outputs such as:

- current-state baseline;
- target service/daemon/module boundaries;
- major flows and schemas;
- visible ADRs/open questions;
- scenario validation;
- phased migration plan with dependencies, compatibility/cutover, validation gates, and rollback.

Use `reviewable`, `candidate`, `study`, or `target architecture` where appropriate. Do not convert Jia-Ru/Preston design inputs into approved platform truth.

## Route request ordering

Preserve the authority boundary:

- dispatcher provides business-facing inputs;
- SS derives EERT/IRT/LSRT;
- SS computes deterministic ordering using eligibility, intent, passenger impact, urgency, waiting, tie-breakers, and starvation protection;
- WSS/PLC remains responsible for route safety authorization.

If the KPI mentions dispatcher profiles, describe them as reviewed business-facing delay-tolerance or policy inputs. Do not imply the dispatcher directly sets final route order.
