# Schema-centric Gerrit change review

Use this checklist when a Gerrit patch introduces or redesigns a multi-document engineering schema with examples.

## Review the composed model, not only each JSON Schema

JSON Schema validates document shape but generally cannot prove cross-document engineering semantics. Add a repository gate that loads the complete example/data set and checks:

- per-collection and global ID uniqueness (`uniqueItems` does not enforce unique object IDs);
- all references resolve to the correct entity class;
- authored facts have one owner; derive route/overlap block coverage from topology rather than duplicating it;
- point locations fall inside the referenced segment;
- block/TVD boundaries belong to member segments and physical boundaries carry an explicit element identity;
- route entry/exit assets coincide with the first/last path boundary;
- adjacent route segments are physically traversable, not merely incident on the same graph vertex;
- turnout traversal permits tip↔left and tip↔right but rejects left↔right;
- every acquired route/overlap resource is released exactly once, with no omission, duplication, or release of an unacquired resource;
- release groups have unambiguous applicability/ownership;
- catalog references are valid (for example, signal aspects), and referenced values are within each asset's declared capability;
- derived safety rules have one source of truth: direction-lock requirements should drive opposite-direction exclusion rather than duplicated handwritten conflict pairs.

## Connected examples

Provide one fictitious, globally connected example set using unmistakable non-production IDs. Include examples that exercise route boundary alignment, a real turnout in both valid positions, same-direction lock sharing and opposite-direction exclusion, overlap ownership and release, an independent non-derived conflict, and site-specific catalogs.

## Mandatory negative probes

Before push, mutate the examples and prove the gate rejects at least:

1. entry signal offset from route path boundary;
2. turnout branch-to-branch traversal;
3. release of an unrelated block/resource;
4. duplicate ID with otherwise different object content;
5. boundary outside the owning TVD/block;
6. unsupported signal aspect reference;
7. unknown cross-document reference.

A green metaschema/example-shape run is insufficient unless these semantic probes also fail for the intended reason.

## Late async review after push

If the task remains in scope and late review reports reproducible safety-model gaps:

1. reproduce each finding against the current patch set;
2. reject obsolete findings already fixed in the meantime;
3. add failing negative tests before changing the model;
4. amend while preserving `Change-Id`;
5. rerun metaschema, positive examples, semantic gate, negative probes, and `git diff --check`;
6. push a new patch set and read back the Gerrit revision SHA before reporting completion.
