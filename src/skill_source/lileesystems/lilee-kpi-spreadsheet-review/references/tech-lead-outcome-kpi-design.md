# Tech Lead Outcome KPI Design

Use this reference when a manager wants KPI goals to measure work beyond routine feature delivery.

## 1. Eligibility gate: should this be a KPI?

Before making wording SMART, classify the item:

- **Routine / already committed delivery:** baseline job expectation. Do not award separate KPI weight merely for completing each feature.
- **Role leverage:** a suitable KPI when it transfers ownership, improves team capability, creates predictable delivery, or expands the Technical Lead's impact.
- **Strategic study/design:** suitable only when it has a defined final maturity and evidence-based outcome.
- **Operational improvement:** suitable when it changes a measurable system/process outcome rather than producing a document alone.

A committed feature may still be evidence for a leadership KPI. Example: several releases can demonstrate release governance or ownership transfer, but the individual features do not each become KPI items.

## 2. Recommended Technical Lead KPI classes

### Ownership transfer

Measure whether responsibility can actually be delegated, not whether training sessions occurred.

Useful evidence:

- representative changes led end-to-end by the developing owner;
- release verification owned by that person;
- independent RCA or controlled failure exercise;
- maintained architecture map, runbook, risk list, and release/debug checklist;
- final ownership review showing the Technical Lead is reviewer/escalation rather than daily executor.

Define the target level explicitly: development owner, co-owner, or primary stack owner.

### Release outcome

If leadership insists on an outcome-only target, define the commitment baseline first:

- scope becomes committed at a documented sign-off by the accountable parties;
- all baseline features must ship on their committed dates;
- no feature drop or carry-over;
- later scope changes count only through formal rebaseline.

Without a commitment cutoff, “no delay/no feature drop” is not objectively measurable and can be gamed in either direction.

### Strategic design/study

State the required maturity explicitly:

- **Design-complete:** approved spec, executable implementation plan, review closure, and handoff-ready ownership.
- **Design-complete plus migration plan:** current state, target state, phased cutover, compatibility, rollback, owners, and legacy retirement.
- **Implementation-verified:** implementation deployed to the named environment and all frozen baseline scenarios pass without specified regressions.

Do not use “complete a study” as the final target. Define the capability, decision package, or verified problem resolution produced by the study.

### Two-audience documentation

For strategic studies, use both:

- **Developer specification:** behavior, architecture/state/interfaces, scenarios, acceptance, dependencies, and implementation boundary.
- **External-facing explanation:** problem, user value, operational flow, capability boundary, limitations, and rollout state without unsuitable internal detail.

If documentation is embedded in every study, do not award a second standalone KPI merely for producing the same documents. Require review by each target audience and evidence that a downstream owner can proceed without oral gap-filling from the Technical Lead.

## 3. Evidence design

For every KPI specify:

1. frozen scope or commitment baseline;
2. final maturity level;
3. required artifacts/capabilities;
4. review or verification environment;
5. named evidence types;
6. rebaseline rule;
7. what does **not** count as completion.

For “resolve all known issues,” freeze the issue set at an agreed time or review gate. Trace every issue through symptom → root-cause family → design mechanism → verification scenario. New issues should not silently change the denominator.

## 4. Common anti-patterns

- Turning the Delivery Map into the employee KPI line by line.
- Making routine release features more verbose but leaving them as KPI goals.
- Measuring “document published” without adoption, review, or handoff evidence.
- Using absolute release outcomes without a signed-off baseline and rebaseline rule.
- Mixing design-complete and implementation-verified goals without stating which maturity applies.
- Creating many tiny study rows instead of a few strategic outcomes with supporting decisions.
- Requiring an incident to occur before an RCA KPI can pass; allow a controlled failure exercise when appropriate.
