from atfd.taxonomy import (
    FailureCategory,
    FailureSubcategory,
    TAXONOMY,
    get_category,
    get_subcategory,
    validate_category_string,
    all_categories,
    all_subcategories,
)


def test_taxonomy_has_7_categories():
    assert len(all_categories()) == 7


def test_taxonomy_has_24_subcategories():
    assert len(all_subcategories()) == 24


def test_category_names():
    names = {c.name for c in all_categories()}
    assert names == {"action", "state", "communication", "quality", "process", "safety", "infrastructure"}


def test_quality_has_5_subcategories():
    quality = get_category("quality")
    subs = [s for s in all_subcategories() if s.category == quality.name]
    assert len(subs) == 5


def test_get_subcategory():
    sub = get_subcategory("action.wrong_tool")
    assert sub.category == "action"
    assert sub.name == "wrong_tool"


def test_validate_valid_category():
    assert validate_category_string("action.wrong_tool") is True
    assert validate_category_string("quality.shallow_output") is True
    assert validate_category_string("infrastructure.timeout") is True


def test_validate_invalid_category():
    assert validate_category_string("fake.category") is False
    assert validate_category_string("action") is False
    assert validate_category_string("") is False


def test_subcategory_has_description():
    sub = get_subcategory("process.tool_loop")
    assert len(sub.description) > 0


def test_subcategory_has_example():
    sub = get_subcategory("action.wrong_tool")
    assert sub.example is not None
    assert len(sub.example) > 0


def test_all_subcategories_belong_to_valid_category():
    cat_names = {c.name for c in all_categories()}
    for sub in all_subcategories():
        assert sub.category in cat_names, f"{sub.category}.{sub.name} has invalid category"
