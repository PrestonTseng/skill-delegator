# Passenger train doors vs platform screen doors (PSD/platform gates)

## Regulatory boundary: movement authority vs door responsibility

### Interlocking / traffic control system
- **49 CFR § 236.402**: "At a controlled point in a traffic control system, means may be provided to permit the control operator to actuate the control circuits."
- **49 CFR § 236.403**: conflicting routes cannot be established simultaneously.
- **49 CFR § 236.407**: "Approach or time locking shall be provided for all controlled signals where route or direction of traffic can be changed."
- **49 CFR § 236.408**: "Route locking shall be provided where switches are power-operated."
- **49 CFR § 236.750** defines automatic interlocking as train movements "governed by signal indication."

**Implication:** these rules govern route protection, signal logic, and movement safety. They do not assign normal passenger-door command authority to interlocking.

## Regulatory boundary: passenger doors
- **49 CFR § 238.131(a)(1)**: locomotives in passenger service "shall be connected or interlocked with the door summary circuit to prohibit the train from developing tractive power if an exterior side door ... is not closed, unless the door is under the direct physical control of a crewmember."
- **49 CFR § 238.131(a)(7)**: "A train's throttle position shall neither open nor close the exterior side doors on the train."
- **49 CFR § 238.131(b)(3)**: door summary status indicator must be "readily viewable to the engineer from his or her normal position in the operating cab."
- **49 CFR § 238.135(a)**: each crewmember must participate in a safety briefing identifying responsibilities for safe door operation, including responsibilities "when arriving at or departing a station."
- **49 CFR § 238.135(d)**: each railroad must provide written override rules to "crewmembers and control center personnel" for overriding the door summary circuit or no-motion system after en-route failures.
- **49 CFR § 238.135(f)**: railroads must require crewmembers to determine exterior side door status so the train "may safely depart a station."
- **49 CFR § 238.135(g)**: railroads must periodically test crewmembers and control center personnel "as appropriate to their roles" on door safety procedures.

**Implication:** normal passenger-door responsibility sits on the operating side (crew / engineer / train-side system), while control-center personnel appear mainly in supervision and override procedures.

## Public industry evidence
- **Wabtec Door Control Units**: "Door Control Units manage primary operational functions, safety functions ... and data recording." This supports train-side ownership of door control logic.
- **Wabtec Marseille NEOMMA**: platform gates "form part of a complete passenger transfer system," while Wabtec also supplied Alstom with "the onboard doors for new metro cars." This shows PSD/platform gates and onboard doors are separate but integrated subsystems.
- **Wabtec Panama Metrolink / Hitachi Rail quote**: "the doors, platforms and stations have to work together with the rest of the systems to operate efficiently." This supports the model of coordinated but distinct subsystems.
- **Hitachi Rail Honolulu platform experience**: the engineer role specialized in "Platform Screen Gates and Train Control and Communication Systems" and the team handled maintenance of platform screen gates across stations, indicating PSDs are treated as a distinct subsystem/domain.
- **Hitachi Rail driverless metro article**: CBTC flexibility includes "blocking doors ... which can be done remotely." This supports the pattern that OCC/control-center systems may supervise or inhibit doors in automated metros without being the primary normal-cycle owner.

## Design implications for planner/scheduler products
When translating this into scheduling or mission-definition software:
- Model **service intent**, not low-level door motor actions.
- Represent whether a stop requires boarding/alighting service, dwell duration, door side, and whether PSD compatibility is required.
- Treat train-door and PSD execution as downstream subsystem behavior.
- Keep abnormal override/control-center participation in exception handling, not in the normal stop primitive.

## Useful phrasing
- "Interlocking governs movement authority; door systems govern passenger exchange."
- "Train doors and platform screen doors are usually separate but coordinated subsystems."
- "A scheduler should describe passenger-service dwell intent, not assume it is the physical door controller."
