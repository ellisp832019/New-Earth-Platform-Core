# Security Baseline v0.1

1. Local-first is the default architectural posture.
2. Secrets never belong in project contracts or registries.
3. Authentication, authorization and encryption choices must be documented.
4. External interfaces must be explicit and versioned.
5. Inputs crossing process/repository boundaries must be validated.
6. Security-sensitive dependency changes require review.
7. Release artifacts should have checksums.
8. Critical actions should be auditable.
9. YAML must be loaded with safe parsers.
10. Tooling must avoid arbitrary code execution from registry data.
11. Machine-specific paths, tokens, private keys, credentials and local environment files must not be committed.
