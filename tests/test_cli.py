from typer.testing import CliRunner

from new_earth_platform.cli import app


def test_cli_validate_passes() -> None:
    result = CliRunner().invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "Platform validation passed" in result.output


def test_cli_doctor_passes() -> None:
    result = CliRunner().invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    assert "PROJECT CONTRACT" in result.output


def test_cli_impact_reports_declared_scope() -> None:
    result = CliRunner().invoke(app, ["impact", "microgrow"])
    assert result.exit_code == 0
    assert "Declared architecture impact only" in result.output
    assert "microgrow-control-centre" in result.output


def test_cli_surfaces_local_ai_runtime() -> None:
    governance = CliRunner().invoke(app, ["governance", "new-earth-local-ai-runtime"])
    assert governance.exit_code == 0
    assert "New Earth Local AI Runtime" in governance.output
    assert "platform_service" in governance.output

    services = CliRunner().invoke(app, ["services", "--json"])
    assert services.exit_code == 0
    assert "local-ai-runtime" in services.output

    interfaces = CliRunner().invoke(app, ["interfaces", "--json"])
    assert interfaces.exit_code == 0
    assert "local-ai-runtime-chat" in interfaces.output

    dependencies = CliRunner().invoke(app, ["dependencies", "--json"])
    assert dependencies.exit_code == 0
    assert "new-earth-local-ai-runtime" in dependencies.output
