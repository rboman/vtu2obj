from typer.testing import CliRunner

from fossils_vtu2obj import __version__
from fossils_vtu2obj.cli import app

runner = CliRunner()


def test_cli_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "inspect" in result.output
    assert "list-arrays" in result.output
    assert "convert" in result.output
    assert "native-status" in result.output


def test_cli_version_option() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_native_status_command_succeeds_without_bridge() -> None:
    result = runner.invoke(app, ["native-status"])

    assert result.exit_code == 0
    assert "native bridge" in result.output.lower()
