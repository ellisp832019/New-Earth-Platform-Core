# New Earth Engineering Standard v0.1

Every active repository should have:

- `NEW_EARTH_PROJECT.yaml`
- semantic version metadata
- README with purpose and run/build instructions
- deterministic local validation commands
- tests appropriate to the project
- explicit dependency declarations
- no committed secrets
- architecture notes for material changes
- branch/PR workflow
- release notes for released versions
- rollback or recovery notes for operationally significant releases

Cross-repository changes must declare impact before merge.

Schema, interface, and compatibility changes require architecture review when they can affect another project. Pull requests should include validation evidence, expected impact, rollback notes where relevant, and links to coordinated repository work.
