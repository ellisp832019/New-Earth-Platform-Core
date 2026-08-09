# Release Standard v0.1

A release should be blocked if:

- project contract validation fails;
- required CI fails;
- compatibility rules fail;
- required documentation is stale;
- security review is required but missing;
- upstream/downstream impact has not been reviewed.

Release lifecycle:

development → alpha → beta → release-candidate → stable → deprecated

Release evidence should include validation results, tests, lint, typing, package build status, declared impact, known limitations, rollback or recovery notes, and any required migration notes for breaking changes.
