import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

ENROLLMENT = ROOT / "schemas" / "enrollment.schema.json"
ASSESSMENT = ROOT / "schemas" / "enrollment-assessment.schema.json"
EVIDENCE_RUN = ROOT / "schemas" / "enrollment-evidence-run.schema.json"


def _validator(path: Path) -> Draft202012Validator:
    with path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _valid_enrollment() -> dict:
    return {
        "schema": "new-earth.enrollment.v1",
        "enrollment_id": "example-enrollment",
        "enrollment_type": "EXISTING_REPOSITORY",
        "subject": {
            "requested_name": "Example",
            "canonical_id": None,
            "purpose": "Schema validation fixture",
            "owner_ref": "peter",
        },
        "provenance": {
            "created_by": "human",
            "source": "test",
            "created_at": "2026-09-16T06:00:00Z",
            "source_reference": None,
        },
        "repositories": [
            {
                "role": "PRIMARY",
                "candidate_path": r"D:\\Dev\\Projects\\Example",
                "repository_ref": None,
            }
        ],
        "programme": {
            "status": "EXTERNAL_PENDING",
            "programme_ref": None,
            "lane_ref": None,
            "bundle_ref": None,
        },
        "requested_authority": {
            "initial": "OBSERVE",
            "human_approval_required": True,
        },
        "routing": {
            "repository_admission_required": True,
            "programme_definition_required": False,
            "contract_review_required": None,
            "consumer_verification_required": None,
        },
        "evidence_refs": [],
        "notes": None,
    }


def _valid_assessment() -> dict:
    digest = "a" * 64
    return {
        "schema": "new-earth.enrollment-assessment.v1",
        "enrollment_id": "example-enrollment",
        "assessment_provenance": {
            "validator_version": "ea-enrollment-validator/0.1.0",
            "evaluated_at": "2026-09-16T06:00:00Z",
            "enrollment_sha256": digest,
            "evidence_sha256": digest,
        },
        "baseline_assurance": {
            "historical_acceptance": "NOT_ACCEPTED",
            "current_comparison": "NOT_EVALUATED",
            "accepted_head": None,
            "observed_head": None,
        },
        "overall_result": "UNKNOWN",
        "admission": {
            "last_proven_stage": "IDENTIFIED",
            "candidate_stage": "OBSERVED",
            "quarantined": True,
        },
        "gates": [
            {
                "gate": "OBSERVED",
                "applicability": "REQUIRED",
                "result": "UNKNOWN",
                "evidence_refs": [],
                "findings": ["No attributable NEOS observation is available."],
            }
        ],
        "findings": [
            {
                "finding_id": "EA-OBSERVED-001",
                "classification": "UNKNOWN",
                "gate": "OBSERVED",
                "message": "No attributable NEOS observation is available.",
                "resolution_owner": "NEOS",
            }
        ],
        "final_authority": "peter",
        "next_action": {
            "id": "ESTABLISH_NEOS_OBSERVATION",
            "description": "Obtain a fresh attributable NEOS observation.",
            "resolution_owner": "NEOS",
        },
        "evidence_refs": [],
    }


def _valid_evidence_run() -> dict:
    digest = "b" * 64
    return {
        "schema": "new-earth.enrollment-evidence-run.v1",
        "run_id": "run-001",
        "created_at": "2026-09-16T06:00:00Z",
        "runner_version": "ea-enrollment-evidence-runner/0.1.0",
        "validator_version": "ea-enrollment-validator/0.1.0",
        "source_paths": {
            "enrollment": r"D:\\evidence\\enrollment.json",
            "evidence": r"D:\\evidence\\evidence.json",
        },
        "source_sha256": {
            "enrollment": digest,
            "evidence": digest,
        },
        "assessment_input_sha256": {
            "enrollment": digest,
            "evidence": digest,
        },
        "assessment_summary": {
            "overall_result": "UNKNOWN",
            "last_proven_stage": "IDENTIFIED",
            "quarantined": True,
        },
        "artifact_sha256": {
            "assessment.json": digest,
        },
    }


def test_enrollment_schema_is_valid_draft_2020_12():
    _validator(ENROLLMENT)


def test_enrollment_assessment_schema_is_valid_draft_2020_12():
    _validator(ASSESSMENT)


def test_enrollment_evidence_run_schema_is_valid_draft_2020_12():
    _validator(EVIDENCE_RUN)


def test_valid_enrollment_fixture_passes():
    assert list(_validator(ENROLLMENT).iter_errors(_valid_enrollment())) == []


def test_enrollment_rejects_execute_authority():
    value = _valid_enrollment()
    value["requested_authority"]["initial"] = "EXECUTE"
    errors = list(_validator(ENROLLMENT).iter_errors(value))
    assert errors
    assert any("EXECUTE" in error.message for error in errors)


def test_enrollment_requires_human_approval():
    value = _valid_enrollment()
    value["requested_authority"]["human_approval_required"] = False
    errors = list(_validator(ENROLLMENT).iter_errors(value))
    assert errors


def test_valid_assessment_fixture_passes():
    assert list(_validator(ASSESSMENT).iter_errors(_valid_assessment())) == []


def test_assessment_rejects_non_peter_final_authority():
    value = _valid_assessment()
    value["final_authority"] = "gaia"
    errors = list(_validator(ASSESSMENT).iter_errors(value))
    assert errors


def test_valid_evidence_run_fixture_passes():
    assert list(_validator(EVIDENCE_RUN).iter_errors(_valid_evidence_run())) == []


def test_schemas_reject_unknown_top_level_fields():
    value = _valid_enrollment()
    value["execution_eligible"] = True
    errors = list(_validator(ENROLLMENT).iter_errors(value))
    assert errors
    assert any("execution_eligible" in error.message for error in errors)
