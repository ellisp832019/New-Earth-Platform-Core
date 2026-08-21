# MCP Runtime Contract Bundle Design

## Decision

**Mode:** `DESIGN_ONLY`

MCP-02B defines the delivery boundary for future runtime consumers. It does not
implement an exporter, verifier, installer, runtime client, runtime server,
transport, policy evaluator, approval workflow, audit store, or write capability.

The implementation decision is intentionally design-only because the current
canonical MCP declarations live under `examples/mcp/`, while validation relies
on fixed example paths and the registry does not enumerate every declaration
file. Moving or silently rewriting those paths in an exporter would create a
second contract system. MCP-02B therefore documents the safe export contract
and makes canonical-input registration a prerequisite for implementation.

## Authority and Baseline

Platform Core remains the authority for MCP identities, schemas, registry graph,
manifests, capability declarations, compatibility, and policy declarations.
The future bundle is a generated, read-only delivery artifact, not a new source
of truth.

Pinned baseline:

`NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21`

The exporter must record the exact Platform Core source commit SHA. It must
never use `latest`, `current`, `head`, or floating `main` as runtime identity.

Recommended bundle identity:

`new-earth-mcp-contract-bundle-v1`

Recommended format version:

`1.0.0`

The bundle format version may remain `1.x` while a future contract baseline
advances. A changed baseline must produce a new versioned bundle directory and
must not overwrite a frozen bundle.

## Current Surface Inventory

| Category | Current location | MCP-02B treatment |
|---|---|---|
| Root graph | `registry/mcp.yaml` | Runtime-required root index |
| MCP schemas | `schemas/mcp-*.schema.json`, `schemas/mcp/*.schema.json` | Runtime-required; 19 files currently |
| Runtime declarations | `examples/mcp/` | Explicitly allowlisted only; 16 current candidates |
| Reference identity | `examples/mcp/mcp-client-identity.yaml` | Development/reference only |
| Invocation examples | `examples/mcp/*invocation-record*.yaml` | Documentation/example only |
| Decision examples | `examples/mcp/*authorization-decision-record*.yaml` | Documentation/example only |
| Validation logic | `src/new_earth_platform/validation.py` | Development-only; reused before export, never bundled |
| Tests | `tests/` | Test-only; never bundled |
| MCP documentation | `docs/` | Documentation-only; never bundled |

The 16 runtime declaration candidates are the GAIA client identity, NEOS server
identity and manifest, discovery, consumption, capability, two tools, two
resources, two queries, three authorization policies, and one approval policy.
The exact list must become an explicit checked-in export graph before an
exporter is implemented. It must not be inferred from filenames or a broad
directory glob.

## Bundle Content Boundary

The smallest proposed runtime bundle contains:

1. `bundle-manifest.json`;
2. the validated registry snapshot;
3. the 19 required MCP JSON schemas;
4. the 16 explicitly registered runtime declaration files;
5. `hashes/SHA256SUMS.txt`; and
6. a separate manifest-hash record if required by the verifier.

It excludes source code, tests, docs, Git metadata, repository history, virtual
environments, temporary files, runtime logs, audit history, credentials, tokens,
machine-specific paths, and developer-specific usernames.

## Directory Format

The generated artifact should use a stable, portable layout:

```text
mcp-contract-bundle-v1/
  bundle-manifest.json
  registry/
    mcp.yaml
  contracts/
    identities/
    manifests/
    consumptions/
    discoveries/
    capabilities/
    tools/
    resources/
    queries/
    policies/
  schemas/
    mcp-*.schema.json
    mcp/*.schema.json
  hashes/
    SHA256SUMS.txt
    BUNDLE-MANIFEST.SHA256
```

The registry snapshot must be an explicit bundle root index. If source-relative
references must change from `examples/mcp/` to `contracts/`, that transformation
must be schema-validated, deterministic, documented, and tested. It must not
mutate the source registry or create an editable duplicate in Platform Core.

## Bundle Manifest

The canonical manifest should contain:

```json
{
  "bundle_id": "new-earth-mcp-contract-bundle-v1",
  "bundle_format_version": "1.0.0",
  "contract_baseline_id": "NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21",
  "platform_core_commit": "<40-character commit sha>",
  "registry_path": "registry/mcp.yaml",
  "schema_paths": ["...sorted bundle-relative paths..."],
  "contract_paths": ["...sorted bundle-relative paths..."],
  "hash_algorithm": "SHA-256",
  "bundle_hash": "<root hash of deterministic payload entries>",
  "hashes_path": "hashes/SHA256SUMS.txt",
  "read_only": true,
  "compatibility": {
    "minimum_consumer_bundle_format": "1.0.0",
    "contract_baseline": "NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21",
    "server_manifest_version": "1.0.0",
    "schema_set_version": "1.0.0"
  }
}
```

`created_at` is deliberately excluded from the deterministic manifest. If
release provenance later requires it, it must be isolated as non-content build
metadata and excluded from `bundle_hash` so repeated exports from the same
commit retain the same content identity.

## Export Authority and Allowlist

The exporter must read only from the canonical Platform Core registry, schemas,
and an explicit contract export graph. It must validate the repository first by
reusing `validate_repository` and the existing MCP validation functions. It must
not reconstruct declarations from docs or derive IDs from filenames.

The export graph should explicitly map each registry-visible identity and
contract ID to one approved source path. It should also explicitly list the
schemas required by those declarations and by the invocation/decision contract
types. Unreferenced examples are excluded, not silently copied.

Export must fail closed when:

- canonical validation fails;
- an allowlisted source is missing;
- a source path is absolute, traverses outside the repository, or resolves
  outside an approved root;
- a source is a symlink/reparse point or resolves through one unexpectedly;
- an unknown path is added to the export graph; or
- the output target is not a dedicated generated destination.

There are no network calls and no writes to NEOS, GAIA, or Command Centre.

## Reproducibility and Integrity

Two exports from the same canonical commit must have the same file set, file
bytes, per-file hashes, and `bundle_hash`.

The exporter must normalize:

- UTF-8 text encoding;
- LF line endings for generated text files;
- POSIX-style bundle-relative paths;
- sorted manifest arrays;
- sorted hash entries; and
- canonical JSON serialization where JSON is generated.

`SHA256SUMS.txt` contains one SHA-256 digest and one sorted bundle-relative path
per payload file. The deterministic root hash is calculated from the canonical
UTF-8 lines `path + two spaces + sha256 + LF` for all payload entries, excluding
the manifest and hash-control files to avoid circular hashing. The manifest is
checked separately using `BUNDLE-MANIFEST.SHA256`.

Hashes provide integrity evidence, not authenticity. No signing keys, secrets,
or signing implementation belong in MCP-02B. Future signing remains optional
hardening and requires an explicit trust/key policy.

## Verification

The future verifier must be independent of network state and must:

1. parse the manifest strictly;
2. verify the baseline ID and bundle format;
3. verify the recorded Platform Core commit format;
4. verify every expected payload exists;
5. verify every payload hash;
6. recompute and compare `bundle_hash`;
7. verify the manifest hash;
8. validate the registry and contracts using existing validation logic against
   the bundle layout;
9. reject unexpected files; and
10. reject missing or duplicated paths.

The final bundle layout must make existing validation reusable. If preserving
source-relative paths is necessary to achieve that, the export graph should
retain those paths inside the generated artifact rather than inventing a second
validator.

## Output, Atomicity, and Safety

Recommended repository-local generated output:

`dist/mcp-contract-bundle/<bundle-id>/<baseline-id>/`

This is generated output, not an editable source tree. The output path must be
explicit for the future CLI. A non-empty existing target must cause failure;
the exporter must not merge stale files or recursively delete an arbitrary
user-supplied directory.

The target export model is:

1. validate canonical inputs;
2. create a uniquely named temporary sibling directory under the approved
   output parent;
3. copy only allowlisted files without following symlinks/reparse points;
4. normalize generated metadata and calculate hashes;
5. verify the completed temporary bundle;
6. atomically rename it into a new versioned final directory; and
7. leave the source tree and external repositories untouched.

## Windows Installation and Resolution

The recommended shared user installation path is:

`%LOCALAPPDATA%\New Earth\Contracts\MCP\<baseline-id>\`

This avoids Administrator rights for the first local-first user-scoped model.
The directory should be installed as read-only to normal runtime consumers.
Installation is not part of MCP-02B and must not be implemented by the
exporter.

GAIA and NEOS must locate the bundle through explicit configuration containing
the bundle root, expected baseline ID, and optionally expected root hash. There
is no filesystem scanning, guessing, or `latest` lookup. Missing paths,
baseline mismatch, hash mismatch, incompatible manifest, and invalid contracts
all fail closed.

Multiple baselines coexist in separate directories. Consumers select one
explicitly. Rollback means changing the configured active path to a previously
verified bundle, never rewriting a bundle in place.

## Controlled Update Model

1. Approve a Platform Core contract change and create a new baseline or
   compatible release.
2. Export and verify a new bundle from the pinned commit.
3. Install it beside the old verified bundle.
4. Run consumer compatibility checks.
5. Switch the explicit active-bundle configuration.
6. Retain the previous bundle for rollback.

No updater, service restart, external repository mutation, or automatic active
baseline switch is allowed in this slice.

## Future CLI Boundary

The existing Typer CLI is the correct CLI authority. Do not create a second CLI.
After canonical input registration is resolved, the narrow future commands are:

```text
new-earth-platform mcp export-bundle --output <path>
new-earth-platform mcp verify-bundle --bundle <path>
```

The export command should accept the repository root only through the existing
CLI conventions, require an explicit output path, and report the pinned commit,
baseline, file count, and root hash. The verify command should return a non-zero
exit status for any mismatch. Neither command installs or activates a runtime.

## Implementation Gates and Test Strategy

MCP-02B should not become `SAFE_EXPORTER_IMPLEMENTATION` until:

- the 16 runtime declaration paths are explicit and registry-linked;
- the treatment of the two record examples and reference client is accepted;
- bundle-relative schema references are resolved without a second validator;
- the generated layout is compatible with existing MCP validation;
- no candidate input contains secrets or machine-specific paths; and
- path/reparse/output safety can be tested entirely within Platform Core.

The future exporter tests must cover valid export, manifest fields, baseline and
commit pinning, registry and schema inclusion, declaration allowlisting,
unrelated-example exclusion, missing/invalid input failure, deterministic
hashes, changed/missing/extra file verification failure, traversal and absolute
path rejection, output containment, stale-output rejection, atomic completion,
secret/path scanning, and preservation of all existing MCP and full-suite tests.

## Boundary Confirmation

This design adds no MCP runtime, network listener, client, server, tool/query
execution, authorization runtime, approval runtime, audit database, or write
capability. It does not modify NEOS, GAIA, or Command Centre. The next source
slice is the narrow canonical export-graph registration and bundle exporter
implementation only after the gates above are closed.
