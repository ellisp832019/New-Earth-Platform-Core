# Testing Standard v0.1

Minimum layers:

- schema/contract tests;
- unit tests;
- integration tests where repositories interact;
- smoke tests for packaged applications;
- compatibility checks for shared interfaces;
- release validation.

Platform-wide orchestration should eventually run only tests affected by a dependency change, plus mandatory safety-critical lanes.

Platform Core tests must remain deterministic and offline. Critical coverage includes project contracts, duplicate IDs, unknown references, self-dependencies, graph generation, cycle detection, compatibility requirement parsing, impact analysis, CLI validation, doctor output, and version drift.
