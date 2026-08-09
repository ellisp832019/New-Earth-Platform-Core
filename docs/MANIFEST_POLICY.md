# Manifest And Generated Artifact Policy

`MANIFEST.sha256` is release evidence, not a file to regenerate after every edit. Regenerate it intentionally when preparing a packaged release or verification bundle.

Generated, reviewable outputs belong under `artifacts/generated/`. CI may generate artifacts for upload, but generated commands should not silently modify the repository during validation.

Transient caches, virtual environments, local machine data, and build output directories are not source artifacts and must not be committed.

Line-ending policy is defined in `.gitattributes`. The policy is introduced without forcing a repository-wide normalization rewrite in v0.1.
