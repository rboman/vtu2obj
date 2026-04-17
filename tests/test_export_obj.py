from pathlib import Path

from fossils_vtu2obj.export_obj import expected_export_bundle


def test_expected_export_bundle_uses_output_prefix() -> None:
    bundle = expected_export_bundle(Path("out/model"))

    assert bundle.obj_path == Path("out/model.obj")
    assert bundle.mtl_path == Path("out/model.mtl")
    assert bundle.texture_path == Path("out/model.png")
