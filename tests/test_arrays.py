from pathlib import Path

from fossils_vtu2obj.arrays import array_names, find_array, require_array
from fossils_vtu2obj.io_vtk import inspect_dataset
from fossils_vtu2obj.model import ArrayInfo, DatasetSummary


def test_find_array_on_point_data() -> None:
    summary = DatasetSummary(
        source_path=Path("sample.vtu"),
        n_points=4,
        n_cells=1,
        point_arrays=(
            ArrayInfo(
                name="stress_von_mises",
                association="point",
                components=1,
                tuples=4,
            ),
        ),
    )

    result = find_array(summary=summary, field_name="stress_von_mises")

    assert result is not None
    assert result.name == "stress_von_mises"
    assert array_names(summary.point_arrays) == ("stress_von_mises",)


def test_require_array_raises_for_missing_field() -> None:
    summary = DatasetSummary(source_path=Path("sample.vtu"), n_points=0, n_cells=0)

    try:
        require_array(summary=summary, field_name="missing")
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected a ValueError for an unknown array.")


def test_inspect_dataset_discovers_point_and_cell_arrays(sample_vtu_path: Path) -> None:
    summary = inspect_dataset(sample_vtu_path)

    assert summary.n_points == 4
    assert summary.n_cells == 1
    assert array_names(summary.point_arrays) == ("stress_von_mises", "displacement")
    assert array_names(summary.cell_arrays) == ("cell_stress_von_mises",)

    displacement = require_array(summary, "displacement")
    assert displacement.is_vector
