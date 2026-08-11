from denckring import check, get


def test_folding_on_by_default_treats_accents_as_the_base_letter() -> None:
    assert not check("lipogram", "café", forbidden="e").satisfied


def test_folding_off_treats_the_accented_form_as_a_different_letter() -> None:
    assert check("lipogram", "café", forbidden="e", fold_diacritics=False).satisfied


def test_the_parameter_is_exposed_in_the_json_schema() -> None:
    schema = get("lipogram").params_schema()
    assert "fold_diacritics" in schema["properties"]


def test_word_length_procedures_do_not_carry_the_parameter() -> None:
    assert "fold_diacritics" not in get("snowball").params_schema()["properties"]


def test_prisoners_constraint_does_not_carry_the_parameter() -> None:
    schema = get("prisoners_constraint").params_schema()
    assert "fold_diacritics" not in schema["properties"]
