from app.catalog import catalog, filter_rules, load_rules
from app.config import build_configure, build_context, build_run_options, parse_selector_list
from app.models import RunOptions, ScanContext
from app.paths import axe_core_home, axe_version


def test_local_axe_core_is_present():
    home = axe_core_home()
    assert (home / "package.json").exists()
    assert axe_version() == "4.13.0"
    assert (home / "lib" / "rules").is_dir()
    assert (home / "locales" / "de.json").exists()


def test_catalog_includes_axe_features():
    data = catalog()
    rule_ids = {rule["ruleId"] for rule in data["rules"]}
    assert "image-alt" in rule_ids
    assert "color-contrast" in rule_ids
    assert data["engine"]["version"] == "4.13.0"
    assert "wcag22aa" in data["presets"]
    assert any(item["id"] == "v2" for item in data["reporters"])
    assert any(item["id"] == "de" for item in data["locales"])
    assert "axe.runPartial" in data["publicApis"]
    assert any(check["id"] == "color-contrast" for check in data["checks"])


def test_filter_rules_by_tag():
    rules = filter_rules(["wcag2a"])
    assert rules
    assert all("wcag2a" in rule["tags"] for rule in rules)


def test_experimental_rules_are_disabled_by_default():
    experimental = [rule for rule in load_rules() if "experimental" in rule["tags"]]
    assert experimental
    assert all(rule["enabled"] is False for rule in experimental)


def test_parse_selector_list():
    assert parse_selector_list("main, #content") == ["main", "#content"]
    assert parse_selector_list("main") == "main"


def test_build_run_options_from_preset():
    options = build_run_options(None, "wcag22aa")
    assert options["runOnly"]["type"] == "tag"
    assert "wcag22aa" in options["runOnly"]["values"]


def test_build_run_options_xpath():
    options = build_run_options(RunOptions(xpath=True, ancestry=True), None)
    assert options["xpath"] is True
    assert options["ancestry"] is True


def test_build_context():
    context = build_context(ScanContext(include="main", exclude=".ad"))
    assert context["include"] == "main"
    assert context["exclude"] == ".ad"


def test_locale_configure():
    spec = build_configure(None, locale_id="de", enable_experimental=True)
    assert spec["locale"]["lang"] == "de"
    assert spec["tagExclude"] == []
