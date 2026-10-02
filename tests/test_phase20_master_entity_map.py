from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

def test_phase20_master_entity_map_resolves():
    root=Path(__file__).resolve().parents[1]
    mapping=yaml.safe_load((root/"registry/master-entity-map.yaml").read_text(encoding="utf-8"))
    schema=json.loads((root/"schemas/master-entity-map.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(mapping)) == []
    projects=yaml.safe_load((root/"registry/projects.yaml").read_text(encoding="utf-8"))["projects"]
    governance=yaml.safe_load((root/"registry/governance.yaml").read_text(encoding="utf-8"))
    pids={str(x["id"]) for x in projects}
    gids={str(x["id"]) for x in governance["systems"]+governance["planned_extractions"]}
    ext=[str(x["external_id"]) for x in mapping["mappings"]]
    native=[str(x["platform_core_id"]) for x in mapping["mappings"]]
    assert len(ext)==len(set(ext))
    assert len(native)==len(set(native))
    assert set(ext)=={"NE-APP-001","NE-FUT-001","NE-APP-002","NE-APP-003","NE-APP-004","NE-TOOL-010","NE-PROD-006","NE-APP-005","NE-FUT-002"}
    for item in mapping["mappings"]:
        nid=str(item["platform_core_id"])
        assert nid in gids
        if item["target_kind"]=="project_and_governance":
            assert nid in pids
