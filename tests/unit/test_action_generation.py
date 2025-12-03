"""Tests for action item generation (T019)."""

import pytest

from doc_manager_mcp.core.actions import ActionGenerator, ActionItem, actions_to_dicts
from doc_manager_mcp.indexing.analysis.semantic_diff import (
    ConfigFieldChange,
    SemanticChange,
)


@pytest.fixture
def generator():
    """Create an ActionGenerator for testing."""
    return ActionGenerator(docs_path="docs")


class TestSemanticChangeActions:
    """Test action generation from semantic changes."""

    def test_function_added_action(self, generator):
        """Test action for added function."""
        changes = [
            SemanticChange(
                name="new_function",
                change_type="added",
                symbol_type="function",
                file="src/module.py",
                line=10,
                old_signature=None,
                new_signature="def new_function(x: int) -> str",
                severity="non-breaking",
            )
        ]

        actions = generator.generate_actions(changes, [])

        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "add_section"
        assert action.priority == "medium"
        assert "new_function" in action.description

    def test_function_removed_critical_priority(self, generator):
        """Test that removed function gets critical priority."""
        changes = [
            SemanticChange(
                name="old_function",
                change_type="removed",
                symbol_type="function",
                file="src/module.py",
                line=None,
                old_signature="def old_function()",
                new_signature=None,
                severity="breaking",
            )
        ]

        actions = generator.generate_actions(changes, [])

        assert len(actions) == 1
        assert actions[0].priority == "critical"
        assert actions[0].action_type == "remove_section"

    def test_signature_changed_high_priority(self, generator):
        """Test that signature changes get high priority."""
        changes = [
            SemanticChange(
                name="my_function",
                change_type="signature_changed",
                symbol_type="function",
                file="src/module.py",
                line=15,
                old_signature="def my_function(x)",
                new_signature="def my_function(x, y)",
                severity="breaking",
            )
        ]

        actions = generator.generate_actions(changes, [])

        assert len(actions) == 1
        assert actions[0].priority == "high"
        assert actions[0].action_type == "update_section"


class TestConfigFieldActions:
    """Test action generation from config field changes."""

    def test_field_added_high_priority(self, generator):
        """Test that added config field gets high priority."""
        changes = [
            ConfigFieldChange(
                field_name="new_setting",
                parent_symbol="AppConfig",
                change_type="added",
                file="config.py",
                line=20,
                old_type=None,
                new_type="str",
                old_default=None,
                new_default='"default"',
                severity="non-breaking",
                documentation_action="add_field_doc",
            )
        ]

        actions = generator.generate_actions([], changes)

        assert len(actions) == 1
        assert actions[0].priority == "high"
        assert actions[0].action_type == "add_field_doc"
        assert "new_setting" in actions[0].description

    def test_field_removed_critical_priority(self, generator):
        """Test that removed config field gets critical priority."""
        changes = [
            ConfigFieldChange(
                field_name="deprecated_setting",
                parent_symbol="AppConfig",
                change_type="removed",
                file="config.py",
                line=None,
                old_type="str",
                new_type=None,
                old_default=None,
                new_default=None,
                severity="breaking",
                documentation_action="remove_field_doc",
            )
        ]

        actions = generator.generate_actions([], changes)

        assert len(actions) == 1
        assert actions[0].priority == "critical"

    def test_default_changed_medium_priority(self, generator):
        """Test that default value changes get medium priority."""
        changes = [
            ConfigFieldChange(
                field_name="timeout",
                parent_symbol="AppConfig",
                change_type="default_changed",
                file="config.py",
                line=25,
                old_type="int",
                new_type="int",
                old_default="30",
                new_default="60",
                severity="non-breaking",
                documentation_action="update_example",
            )
        ]

        actions = generator.generate_actions([], changes)

        assert len(actions) == 1
        assert actions[0].priority == "medium"
        assert actions[0].action_type == "update_example"


class TestPrioritySorting:
    """Test that actions are sorted by priority."""

    def test_actions_sorted_by_priority(self, generator):
        """Test that critical comes before high, high before medium."""
        semantic_changes = [
            SemanticChange(
                name="new_func",
                change_type="added",
                symbol_type="function",
                file="a.py",
                line=1,
                old_signature=None,
                new_signature="def new_func()",
                severity="non-breaking",
            ),
        ]
        config_changes = [
            ConfigFieldChange(
                field_name="removed_field",
                parent_symbol="Config",
                change_type="removed",
                file="b.py",
                line=None,
                old_type="str",
                new_type=None,
                old_default=None,
                new_default=None,
                severity="breaking",
                documentation_action="remove_field_doc",
            ),
            ConfigFieldChange(
                field_name="new_field",
                parent_symbol="Config",
                change_type="added",
                file="b.py",
                line=10,
                old_type=None,
                new_type="str",
                old_default=None,
                new_default=None,
                severity="non-breaking",
                documentation_action="add_field_doc",
            ),
        ]

        actions = generator.generate_actions(semantic_changes, config_changes)

        # Should be: critical (removed_field), high (new_field), medium (new_func)
        priorities = [a.priority for a in actions]
        assert priorities == ["critical", "high", "medium"]


class TestSourceChangeReference:
    """Test that source changes are correctly referenced."""

    def test_semantic_change_reference(self, generator):
        """Test that semantic change is referenced in action."""
        changes = [
            SemanticChange(
                name="my_func",
                change_type="added",
                symbol_type="function",
                file="test.py",
                line=10,
                old_signature=None,
                new_signature="def my_func()",
                severity="non-breaking",
            )
        ]

        actions = generator.generate_actions(changes, [])

        assert len(actions) == 1
        source = actions[0].source_change
        assert source["type"] == "semantic"
        assert source["name"] == "my_func"
        assert source["change_type"] == "added"

    def test_config_change_reference(self, generator):
        """Test that config change is referenced in action."""
        changes = [
            ConfigFieldChange(
                field_name="setting",
                parent_symbol="Config",
                change_type="added",
                file="config.py",
                line=5,
                old_type=None,
                new_type="str",
                old_default=None,
                new_default=None,
                severity="non-breaking",
                documentation_action="add_field_doc",
            )
        ]

        actions = generator.generate_actions([], changes)

        assert len(actions) == 1
        source = actions[0].source_change
        assert source["type"] == "config_field"
        assert source["field_name"] == "setting"
        assert source["parent_symbol"] == "Config"


class TestActionsToDict:
    """Test serialization of actions to dictionaries."""

    def test_actions_to_dicts(self, generator):
        """Test conversion to JSON-serializable dicts."""
        changes = [
            SemanticChange(
                name="test",
                change_type="added",
                symbol_type="function",
                file="test.py",
                line=1,
                old_signature=None,
                new_signature="def test()",
                severity="non-breaking",
            )
        ]

        actions = generator.generate_actions(changes, [])
        dicts = actions_to_dicts(actions)

        assert len(dicts) == 1
        assert isinstance(dicts[0], dict)
        assert "action_type" in dicts[0]
        assert "target_file" in dicts[0]
        assert "priority" in dicts[0]
