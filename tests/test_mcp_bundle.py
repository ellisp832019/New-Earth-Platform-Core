from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import new_earth_platform.mcp_bundle as bundle_module
from new_earth_platform.mcp_bundle import BundleError, export_bundle, verify_bundle

ROOT = Path(__file__).parents[1]


@pytest.fixture
def exported_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(bundle_module, "_source_commit", lambda _root: "a" * 40)
    return export_bundle(ROOT, tmp_path / "output")


def _payload_files(bundle: Path) -> set[str]:
    return {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and path.name not in {"bundle-manifest.json", "SHA256SUMS.txt"}
    }


def test_valid_export_has_expected_payload_and_manifest(exported_bundle: Path) -> None:
    manifest = json.loads((exported_bundle / "bundle-manifest.json").read_text(encoding="utf-8"))
    assert len(_payload_files(exported_bundle)) == 36
    assert manifest["bundle_id"] == "new-earth-mcp-contract-bundle-v1"
    assert manifest["bundle_format_version"] == "1.0.0"
    assert manifest["contract_baseline_id"] == "NE-MCP-READONLY-V1-DECLARATIVE-2026-08-21"
    assert manifest["platform_core_commit"] == "a" * 40
    assert manifest["read_only"] is True
    assert len(manifest["schema_paths"]) == 19
    assert len(manifest["contract_paths"]) == 16
    assert (exported_bundle / "registry/mcp.yaml").is_file()
    assert len((exported_bundle / "hashes/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()) == 36
    assert "mcp-client-identity.yaml" not in "\n".join(_payload_files(exported_bundle))


def test_repeated_export_has_deterministic_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bundle_module, "_source_commit", lambda _root: "b" * 40)
    first = export_bundle(ROOT, tmp_path / "first")
    second = export_bundle(ROOT, tmp_path / "second")
    first_manifest = json.loads((first / "bundle-manifest.json").read_text(encoding="utf-8"))
    second_manifest = json.loads((second / "bundle-manifest.json").read_text(encoding="utf-8"))
    assert first_manifest == second_manifest
    assert (first / "hashes/SHA256SUMS.txt").read_bytes() == (second / "hashes/SHA256SUMS.txt").read_bytes()


def test_offline_verification_works_outside_repository(exported_bundle: Path, tmp_path: Path) -> None:
    copied = tmp_path / "copied-bundle"
    shutil.copytree(exported_bundle, copied)
    manifest = verify_bundle(copied)
    assert manifest["bundle_id"] == "new-earth-mcp-contract-bundle-v1"


def test_dirty_source_export_is_rejected(tmp_path: Path) -> None:
    tracked_file = ROOT / "README.md"
    original_bytes = tracked_file.read_bytes()
    before = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    try:
        tracked_file.write_bytes(original_bytes + b"\n# temporary dirty-source test marker\n")
        with pytest.raises(BundleError, match="DIRTY_SOURCE_TREE"):
            export_bundle(ROOT, tmp_path / "output")
    finally:
        tracked_file.write_bytes(original_bytes)
    after = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert after == before


def test_existing_final_bundle_is_rejected(exported_bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bundle_module, "_source_commit", lambda _root: "a" * 40)
    with pytest.raises(BundleError, match="BUNDLE_ALREADY_EXISTS"):
        export_bundle(ROOT, exported_bundle.parent.parent)


@pytest.mark.parametrize("mutation", ["changed", "missing", "unexpected"])
def test_payload_tampering_is_rejected(exported_bundle: Path, mutation: str) -> None:
    target = exported_bundle / "registry/mcp.yaml"
    if mutation == "changed":
        target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    elif mutation == "missing":
        target.unlink()
    else:
        (exported_bundle / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(BundleError) as caught:
        verify_bundle(exported_bundle)
    assert caught.value.code in {"HASH_MISMATCH", "MISSING_BUNDLE_FILE", "UNEXPECTED_BUNDLE_FILE"}


def test_manifest_baseline_tampering_is_rejected(exported_bundle: Path) -> None:
    path = exported_bundle / "bundle-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["contract_baseline_id"] = "latest"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleError, match="BASELINE_MISMATCH"):
        verify_bundle(exported_bundle)


def test_root_hash_tampering_is_rejected(exported_bundle: Path) -> None:
    path = exported_bundle / "bundle-manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["content_root_hash"] = "0" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleError, match="ROOT_HASH_MISMATCH"):
        verify_bundle(exported_bundle)


def test_hash_listing_tampering_is_rejected(exported_bundle: Path) -> None:
    path = exported_bundle / "hashes/SHA256SUMS.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("0" * 64 + lines[0][64:] + "\n" + "\n".join(lines[1:]) + "\n", encoding="utf-8")
    with pytest.raises(BundleError, match="HASH_MISMATCH"):
        verify_bundle(exported_bundle)


def test_failed_export_does_not_leave_final_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bundle_module, "_source_commit", lambda _root: "c" * 40)
    monkeypatch.setattr(bundle_module, "validate_repository", lambda _root: ["invalid"])
    parent = tmp_path / "output"
    with pytest.raises(BundleError, match="CONTRACT_VALIDATION_FAILED"):
        export_bundle(ROOT, parent)
    assert not (parent / "new-earth-mcp-contract-bundle-v1").exists()


def test_bundle_contains_no_machine_paths_or_secrets(exported_bundle: Path) -> None:
    text = "".join(
        path.read_text(encoding="utf-8")
        for path in exported_bundle.rglob("*")
        if path.is_file() and path.suffix in {".yaml", ".json"}
    )
    assert "D:\\Dev\\" not in text
    assert "PRIVATE KEY" not in text
    assert "token:" not in text.lower()
