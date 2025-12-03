"""Tests for config field diff detection (T018)."""

import pytest

from doc_manager_mcp.indexing.analysis.semantic_diff import (
    ConfigFieldChange,
    compare_config_fields,
)
from doc_manager_mcp.indexing.analysis.tree_sitter import (
    ConfigField,
    Symbol,
    SymbolType,
)


def make_symbol(name: str, file: str, config_fields: list[ConfigField] | None = None) -> Symbol:
    """Helper to create a Symbol for testing."""
    return Symbol(
        name=name,
        type=SymbolType.CLASS,
        file=file,
        line=1,
        column=0,
        config_fields=config_fields,
    )


def make_config_field(
    name: str,
    parent: str,
    field_type: str | None = None,
    default_value: str | None = None,
    is_optional: bool = False,
) -> ConfigField:
    """Helper to create a ConfigField for testing."""
    return ConfigField(
        name=name,
        parent_symbol=parent,
        field_type=field_type,
        default_value=default_value,
        file="test.py",
        line=10,
        column=4,
        is_optional=is_optional,
    )


class TestFieldAddedDetection:
    """Test detection of added config fields."""

    def test_field_added_detected(self):
        """Test that added fields are detected."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("host", "Config", "str"),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("host", "Config", "str"),
                make_config_field("port", "Config", "int"),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].field_name == "port"
        assert changes[0].change_type == "added"
        assert changes[0].severity == "non-breaking"

    def test_field_added_has_correct_action(self):
        """Test that added fields have add_field_doc action."""
        old_symbols = {"test.py": [make_symbol("Config", "test.py", config_fields=[])]}
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("new_field", "Config", "str"),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].documentation_action == "add_field_doc"


class TestFieldRemovedDetection:
    """Test detection of removed config fields."""

    def test_field_removed_detected(self):
        """Test that removed fields are detected."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("host", "Config", "str"),
                make_config_field("port", "Config", "int"),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("host", "Config", "str"),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].field_name == "port"
        assert changes[0].change_type == "removed"
        assert changes[0].severity == "breaking"

    def test_field_removed_has_remove_action(self):
        """Test that removed fields have remove_field_doc action."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("old_field", "Config", "str"),
            ])]
        }
        new_symbols = {"test.py": [make_symbol("Config", "test.py", config_fields=[])]}

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].documentation_action == "remove_field_doc"


class TestTypeChangedDetection:
    """Test detection of type changes."""

    def test_type_changed_detected(self):
        """Test that type changes are detected."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("port", "Config", "str"),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("port", "Config", "int"),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].field_name == "port"
        assert changes[0].change_type == "type_changed"
        assert changes[0].old_type == "str"
        assert changes[0].new_type == "int"

    def test_type_widening_is_non_breaking(self):
        """Test that widening type changes (adding None) are non-breaking."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("value", "Config", "str"),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("value", "Config", "str | None"),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].severity == "non-breaking"


class TestDefaultChangedDetection:
    """Test detection of default value changes."""

    def test_default_changed_detected(self):
        """Test that default value changes are detected."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("timeout", "Config", "int", default_value="30"),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("timeout", "Config", "int", default_value="60"),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].change_type == "default_changed"
        assert changes[0].old_default == "30"
        assert changes[0].new_default == "60"
        assert changes[0].severity == "non-breaking"


class TestSeverityClassification:
    """Test severity classification of changes."""

    def test_breaking_changes_sorted_first(self):
        """Test that breaking changes are sorted before non-breaking."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("removed_field", "Config", "str"),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("added_field", "Config", "str"),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 2
        # Breaking (removed) should come first
        assert changes[0].severity == "breaking"
        assert changes[0].change_type == "removed"
        # Non-breaking (added) should come second
        assert changes[1].severity == "non-breaking"
        assert changes[1].change_type == "added"

    def test_optional_to_required_is_breaking(self):
        """Test that changing optional to required is breaking."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("field", "Config", "str", is_optional=True),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("field", "Config", "str", is_optional=False),
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        assert len(changes) == 1
        assert changes[0].severity == "breaking"


class TestMultipleChanges:
    """Test detection of multiple changes in one class."""

    def test_multiple_changes_detected(self):
        """Test that multiple field changes are all detected."""
        old_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("host", "Config", "str"),
                make_config_field("port", "Config", "int"),
                make_config_field("timeout", "Config", "int", default_value="30"),
            ])]
        }
        new_symbols = {
            "test.py": [make_symbol("Config", "test.py", config_fields=[
                make_config_field("host", "Config", "str | None"),  # type changed
                make_config_field("port", "Config", "int"),  # unchanged
                make_config_field("timeout", "Config", "int", default_value="60"),  # default changed
                make_config_field("new_field", "Config", "bool"),  # added
            ])]
        }

        changes = compare_config_fields(old_symbols, new_symbols)

        # Should detect: type_changed (host), default_changed (timeout), added (new_field)
        assert len(changes) == 3
        change_types = {c.field_name: c.change_type for c in changes}
        assert change_types["host"] == "type_changed"
        assert change_types["timeout"] == "default_changed"
        assert change_types["new_field"] == "added"
