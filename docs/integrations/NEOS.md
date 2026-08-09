# NEOS Integration Contract

NEOS should consume:

- `registry/projects.yaml`
- `registry/dependencies.yaml`
- `registry/interfaces.yaml`
- `compatibility/matrix.yaml`
- each repository's `NEW_EARTH_PROJECT.yaml`

NEOS should return derived intelligence such as:

- observed git branch/SHA;
- build health;
- test health;
- documentation health;
- contract drift;
- dependency drift;
- compatibility warnings;
- architecture impact;
- release readiness.

NEOS must not silently mutate Platform Core authoritative registries.
