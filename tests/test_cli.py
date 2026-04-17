from pathlib import Path

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


def test_inspect_command_reports_dataset_shape(sample_vtu_path: Path) -> None:
    result = runner.invoke(app, ["inspect", str(sample_vtu_path)])

    assert result.exit_code == 0
    assert "Points: 4" in result.output
    assert "Cells: 1" in result.output


def test_list_arrays_command_lists_point_and_cell_arrays(sample_vtu_path: Path) -> None:
    result = runner.invoke(app, ["list-arrays", str(sample_vtu_path)])

    assert result.exit_code == 0
    assert "stress_von_mises" in result.output
    assert "displacement" in result.output
    assert "cell_stress_von_mises" in result.output


def test_convert_command_writes_obj_bundle(
    sample_vtu_path: Path,
    tmp_path: Path,
) -> None:
    output_prefix = tmp_path / "converted" / "model"
    result = runner.invoke(
        app,
        [
            "convert",
            str(sample_vtu_path),
            str(output_prefix),
            "--field",
            "stress_von_mises",
            "--colormap",
            "rainbow",
            "--n-colors",
            "16",
        ],
    )

    assert result.exit_code == 0
    assert output_prefix.with_suffix(".obj").is_file()
    assert output_prefix.with_suffix(".mtl").is_file()
    assert output_prefix.with_suffix(".png").is_file()


def test_convert_command_supports_scalar_cell_data(
    sample_vtu_path: Path,
    tmp_path: Path,
) -> None:
    output_prefix = tmp_path / "converted_cell" / "model"
    result = runner.invoke(
        app,
        [
            "convert",
            str(sample_vtu_path),
            str(output_prefix),
            "--field",
            "cell_stress_von_mises",
            "--colormap",
            "cool_to_warm",
            "--n-colors",
            "16",
        ],
    )

    assert result.exit_code == 0
    assert output_prefix.with_suffix(".obj").is_file()
