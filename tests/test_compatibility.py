from pathlib import Path

from new_earth_platform.compatibility import find_rule, is_compatible
from new_earth_platform.validation import validate_requirement


def test_compatibility_requirement_parsing() -> None:
    assert validate_requirement(">=1.0")
    assert validate_requirement(">=1.0,<2.0")
    assert validate_requirement("~=1.4")
    assert not validate_requirement("not a version")


def test_compatibility_rule_lookup_and_evaluation() -> None:
    root = Path(__file__).resolve().parents[1]
    rule = find_rule(root, "microgrow-control-centre", "microgrow", "microgrow-device-api")
    assert rule is not None
    assert rule.requirement == ">=1.0,<2.0"
    assert is_compatible(root, "microgrow-control-centre", "microgrow", "1.5.0") is True
    assert is_compatible(root, "microgrow-control-centre", "microgrow", "2.0.0") is False


def test_local_ai_runtime_compatibility_rules_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    rule = find_rule(root, "gaia", "new-earth-local-ai-runtime", "local-ai-runtime-chat")
    assert rule is not None
    assert rule.requirement == ">=0.1.0,<0.2.0"
    assert is_compatible(root, "gaia", "new-earth-local-ai-runtime", "0.1.0", "local-ai-runtime-chat") is True
    assert is_compatible(root, "gaia", "new-earth-local-ai-runtime", "0.2.0", "local-ai-runtime-chat") is False
