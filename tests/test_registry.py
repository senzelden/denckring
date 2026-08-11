import pytest
from pydantic import BaseModel

from denckring.core import catalogue, registry
from denckring.core.base import BaseProcedure
from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import LanguagePack, Report


def test_get_raises_on_unknown_id() -> None:
    with pytest.raises(UnknownProcedure):
        registry.get("wobble")


def test_registered_ids_are_a_subset_of_the_catalogue() -> None:
    assert set(registry.all_procedures()) <= set(catalogue.ids())


def test_every_registered_procedure_is_a_base_procedure() -> None:
    for proc in registry.all_procedures().values():
        assert isinstance(proc, BaseProcedure)


def test_module_name_must_equal_procedure_id() -> None:
    for proc_id, proc in registry.all_procedures().items():
        assert type(proc).__module__.rsplit(".", 1)[-1] == proc_id


def test_registering_a_procedure_whose_module_disagrees_with_its_id_fails() -> None:
    class Params(BaseModel):
        pass

    class Mismatched(BaseProcedure[Params]):
        id = "definitely_not_this_module"

        @classmethod
        def params_model(cls) -> type[Params]:
            return Params

        def _check(self, text: str, pack: LanguagePack, params: Params) -> Report:
            raise NotImplementedError

    with pytest.raises(ValueError, match="module"):
        registry.register(Mismatched)
