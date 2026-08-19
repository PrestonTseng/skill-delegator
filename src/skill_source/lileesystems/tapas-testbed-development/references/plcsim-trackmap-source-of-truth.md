# PLCsim integration from tapas-testbed

This reference no longer defines the `plcsim` source-of-truth authoring workflow.

For topology/wayside SSOT design, load `tapas-redesign-architecture` and read `references/canonical-yaml-migration-checkpoints.md`. That umbrella owns the four-patch sequence and the human-reviewed Item-1 YAML rules.

Use this testbed reference only after the applicable plcsim patch is approved and must be integrated into `tapas-testbed`.

## Integration rules

- Treat approved plcsim YAML/generated contracts as upstream versioned inputs; do not maintain a second handwritten route/asset table in testbed.
- Pin the exact Gerrit revision/tag or released artifact used by the testbed.
- Keep testbed-specific scenario fixtures separate from canonical TAPAS topology/wayside data.
- Do not patch missing engineering values in Compose fixtures. Send corrections back through the plcsim YAML Gerrit review.
- Match the active phase:
  - after Item 1, review/inventory only;
  - after Item 2, microservices may consume generated JSON;
  - after Item 3, Compose may exercise generated ST/OpenPLC artifacts;
  - after Item 4, E2E may drive the Dispatch Console.
- Require source revision, generated artifact hash, running image/container provenance, real API/Modbus behavior, and cleanup evidence before calling an integration pass.

Historical PLC decks and drawings remain test-scenario/reference material. They do not establish TAPAS switch IDs, detection boundaries, route overlap/flank protection, or release data.
