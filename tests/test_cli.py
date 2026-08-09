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
