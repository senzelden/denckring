from pathlib import Path

import pytest
from new_procedure import class_name, scaffold


def _empty_tree(root: Path) -> None:
    (root / "src/denckring/procedures").mkdir(parents=True)
    (root / "src/denckring/eval/fixtures/golden").mkdir(parents=True)
    (root / "tests/strategies").mkdir(parents=True)
    (root / "src/denckring/data").mkdir(parents=True)
    (root / "src/denckring/data/catalogue.yaml").write_text("procedures:\n", encoding="utf-8")


def test_class_name_is_pascal_case() -> None:
    assert class_name("reverse_snowball") == "ReverseSnowball"
    assert class_name("n_plus_7") == "NPlus7"


def test_scaffold_writes_five_files(tmp_path: Path) -> None:
    _empty_tree(tmp_path)

    written = scaffold("demo_thing", tmp_path)

    assert len(written) == 5
    module = (tmp_path / "src/denckring/procedures/demo_thing.py").read_text(encoding="utf-8")
    assert "class DemoThing(BaseProcedure[DemoThingParams])" in module
    assert 'id = "demo_thing"' in module
    assert "raise NotImplementedError" in module


def test_scaffold_refuses_to_overwrite(tmp_path: Path) -> None:
    (tmp_path / "src/denckring/procedures").mkdir(parents=True)
    (tmp_path / "src/denckring/procedures/demo_thing.py").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        scaffold("demo_thing", tmp_path)


def test_scaffold_appends_a_catalogue_row(tmp_path: Path) -> None:
    _empty_tree(tmp_path)

    scaffold("demo_thing", tmp_path)

    catalogue_text = (tmp_path / "src/denckring/data/catalogue.yaml").read_text(encoding="utf-8")
    assert "id: demo_thing" in catalogue_text
    assert "FILL IN" in catalogue_text
