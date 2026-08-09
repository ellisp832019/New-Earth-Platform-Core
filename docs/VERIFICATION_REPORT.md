# Verification Report

This file records expected v0.1 verification lanes. Final command results are reported in the pull request and release evidence.

## Required Local Lanes

- `new-earth-platform validate`
- `new-earth-platform doctor`
- `new-earth-platform projects`
- `new-earth-platform graph --format mermaid`
- `new-earth-platform impact <project-id>`
- `pytest`
- `ruff check src tests`
- `mypy src`
- `python -m build`

## Security Review Scope

The basic v0.1 review checks for committed secrets, private keys, credentials, machine-specific data, unsafe YAML loading, dangerous subprocess behavior, arbitrary code execution from registry data, and insecure path handling. It is not a professional penetration test.

## Generated Artifacts

Generated graph files belong under `artifacts/generated/`. CI may upload generated artifacts but should not silently commit them.
