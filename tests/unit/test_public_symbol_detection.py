"""Tests for public symbol detection following industry standards.

Tests that is_public_symbol() correctly implements conventions from
Sphinx autodoc, mkdocstrings/Griffe, and pdoc:
1. __all__ takes precedence when defined
2. Underscore convention as fallback
3. Configurable pattern-based filtering (presets + custom patterns)
"""

import pytest
from dataclasses import dataclass
from pathlib import Path

from doc_manager_mcp.core.project import (
    is_public_symbol,
    extract_module_all,
)
from doc_manager_mcp.core.api_coverage import (
    API_COVERAGE_PRESETS,
    ApiCoverageConfig,
    matches_any_pattern,
)


@dataclass
class MockSymbol:
    """Mock symbol for testing."""
    name: str
    file: str
    parent: str | None = None


class TestUnderscoreConvention:
    """Test basic underscore convention (no __all__ defined)."""

    def test_public_function_is_public(self):
        """Functions without underscore prefix are public."""
        symbol = MockSymbol(name="process_data", file="module.py")
        assert is_public_symbol(symbol) is True

    def test_private_function_is_private(self):
        """Functions with single underscore prefix are private."""
        symbol = MockSymbol(name="_internal_helper", file="module.py")
        assert is_public_symbol(symbol) is False

    def test_dunder_is_private(self):
        """Dunder methods are private (not part of API coverage)."""
        symbol = MockSymbol(name="__init__", file="module.py", parent="MyClass")
        assert is_public_symbol(symbol) is False

    def test_public_class_is_public(self):
        """Classes without underscore prefix are public."""
        symbol = MockSymbol(name="DataProcessor", file="module.py")
        assert is_public_symbol(symbol) is True

    def test_private_class_is_private(self):
        """Classes with underscore prefix are private."""
        symbol = MockSymbol(name="_InternalHelper", file="module.py")
        assert is_public_symbol(symbol) is False


class TestAllTakesPrecedence:
    """Test that __all__ takes absolute precedence."""

    def test_symbol_in_all_is_public(self):
        """Symbols listed in __all__ are public."""
        symbol = MockSymbol(name="process_data", file="module.py")
        module_all = {"process_data", "DataClass"}
        assert is_public_symbol(symbol, module_all) is True

    def test_symbol_not_in_all_is_private(self):
        """Symbols not in __all__ are private, even without underscore."""
        symbol = MockSymbol(name="helper_function", file="module.py")
        module_all = {"main_function"}
        assert is_public_symbol(symbol, module_all) is False

    def test_underscore_in_all_is_public(self):
        """Underscore-prefixed symbols are public if in __all__."""
        symbol = MockSymbol(name="_special_export", file="module.py")
        module_all = {"_special_export"}
        assert is_public_symbol(symbol, module_all) is True

    def test_empty_all_means_no_public_api(self):
        """Empty __all__ means module has no public API."""
        symbol = MockSymbol(name="some_function", file="module.py")
        module_all: set[str] = set()
        assert is_public_symbol(symbol, module_all) is False


class TestConfigurableExcludePatterns:
    """Test configurable exclude patterns via fnmatch."""

    def test_exact_match_excludes(self):
        """Exact name match excludes symbol."""
        symbol = MockSymbol(name="Config", file="models.py")
        assert is_public_symbol(symbol, exclude_patterns=["Config"]) is False

    def test_wildcard_suffix_excludes(self):
        """Wildcard suffix pattern excludes matching symbols."""
        symbol = MockSymbol(name="validate_email", file="validators.py")
        assert is_public_symbol(symbol, exclude_patterns=["validate_*"]) is False

    def test_wildcard_prefix_excludes(self):
        """Wildcard prefix pattern excludes matching symbols."""
        symbol = MockSymbol(name="test_something", file="tests.py")
        assert is_public_symbol(symbol, exclude_patterns=["test_*"]) is False

    def test_pattern_no_match_keeps_public(self):
        """Patterns that don't match keep symbol public."""
        symbol = MockSymbol(name="process_data", file="module.py")
        assert is_public_symbol(symbol, exclude_patterns=["validate_*"]) is True

    def test_multiple_patterns_any_match_excludes(self):
        """If any pattern matches, symbol is excluded."""
        symbol = MockSymbol(name="model_validator", file="models.py")
        patterns = ["validate_*", "model_validator", "Config"]
        assert is_public_symbol(symbol, exclude_patterns=patterns) is False


class TestConfigurableIncludePatterns:
    """Test include patterns override exclusions."""

    def test_include_overrides_exclude(self):
        """Include pattern overrides exclude pattern."""
        symbol = MockSymbol(name="validate_api", file="validators.py")
        # Would be excluded by validate_*, but include overrides
        assert is_public_symbol(
            symbol,
            exclude_patterns=["validate_*"],
            include_patterns=["validate_api"]
        ) is True

    def test_include_overrides_underscore(self):
        """Include pattern overrides underscore convention."""
        symbol = MockSymbol(name="_special_public", file="module.py")
        assert is_public_symbol(
            symbol,
            include_patterns=["_special_*"]
        ) is True

    def test_include_with_wildcard(self):
        """Include patterns support wildcards."""
        symbol = MockSymbol(name="my_internal_api", file="module.py")
        assert is_public_symbol(
            symbol,
            exclude_patterns=["my_internal_*"],
            include_patterns=["*_api"]
        ) is True


class TestPresetPatterns:
    """Test built-in preset pattern functionality."""

    def test_pydantic_preset_excludes_validators(self):
        """Pydantic preset excludes validator decorators."""
        config = ApiCoverageConfig(preset="pydantic")
        patterns = config.get_resolved_exclude_patterns()

        for name in ["model_validator", "field_validator", "root_validator", "validator"]:
            symbol = MockSymbol(name=name, file="models.py")
            assert is_public_symbol(symbol, exclude_patterns=patterns) is False

    def test_pydantic_preset_excludes_config(self):
        """Pydantic preset excludes Config class."""
        config = ApiCoverageConfig(preset="pydantic")
        patterns = config.get_resolved_exclude_patterns()
        symbol = MockSymbol(name="Config", file="models.py")
        assert is_public_symbol(symbol, exclude_patterns=patterns) is False

    def test_pydantic_preset_excludes_validate_wildcard(self):
        """Pydantic preset excludes validate_* functions."""
        config = ApiCoverageConfig(preset="pydantic")
        patterns = config.get_resolved_exclude_patterns()
        symbol = MockSymbol(name="validate_email", file="models.py")
        assert is_public_symbol(symbol, exclude_patterns=patterns) is False

    def test_django_preset_excludes_meta(self):
        """Django preset excludes Meta class."""
        config = ApiCoverageConfig(preset="django")
        patterns = config.get_resolved_exclude_patterns()
        symbol = MockSymbol(name="Meta", file="models.py")
        assert is_public_symbol(symbol, exclude_patterns=patterns) is False

    def test_django_preset_excludes_exceptions(self):
        """Django preset excludes DoesNotExist and MultipleObjectsReturned."""
        config = ApiCoverageConfig(preset="django")
        patterns = config.get_resolved_exclude_patterns()

        for name in ["DoesNotExist", "MultipleObjectsReturned"]:
            symbol = MockSymbol(name=name, file="models.py")
            assert is_public_symbol(symbol, exclude_patterns=patterns) is False

    def test_pytest_preset_excludes_test_functions(self):
        """Pytest preset excludes test_ functions."""
        config = ApiCoverageConfig(preset="pytest")
        patterns = config.get_resolved_exclude_patterns()
        symbol = MockSymbol(name="test_something", file="test_module.py")
        assert is_public_symbol(symbol, exclude_patterns=patterns) is False

    def test_pytest_preset_excludes_test_classes(self):
        """Pytest preset excludes Test* classes."""
        config = ApiCoverageConfig(preset="pytest")
        patterns = config.get_resolved_exclude_patterns()
        symbol = MockSymbol(name="TestSomething", file="test_module.py")
        assert is_public_symbol(symbol, exclude_patterns=patterns) is False


class TestPresetPlusCustomPatterns:
    """Test merging preset and custom patterns."""

    def test_preset_plus_custom_merged(self):
        """Preset and custom patterns are merged."""
        config = ApiCoverageConfig(
            preset="pydantic",
            exclude_symbols=["my_internal_*"]
        )
        patterns = config.get_resolved_exclude_patterns()

        # Preset pattern
        assert "Config" in patterns
        # Custom pattern
        assert "my_internal_*" in patterns

    def test_preset_plus_custom_both_work(self):
        """Both preset and custom patterns filter symbols."""
        config = ApiCoverageConfig(
            preset="pydantic",
            exclude_symbols=["helper_*"]
        )
        patterns = config.get_resolved_exclude_patterns()

        # Preset exclusion works
        symbol_config = MockSymbol(name="Config", file="models.py")
        assert is_public_symbol(symbol_config, exclude_patterns=patterns) is False

        # Custom exclusion works
        symbol_helper = MockSymbol(name="helper_function", file="utils.py")
        assert is_public_symbol(symbol_helper, exclude_patterns=patterns) is False

        # Non-matching symbol is public
        symbol_public = MockSymbol(name="process_data", file="module.py")
        assert is_public_symbol(symbol_public, exclude_patterns=patterns) is True


class TestStrategyOptions:
    """Test different strategy options."""

    def test_all_then_underscore_uses_all_when_present(self):
        """all_then_underscore strategy uses __all__ when defined."""
        symbol = MockSymbol(name="helper", file="module.py")
        module_all = {"main_func"}

        # Default strategy is all_then_underscore
        assert is_public_symbol(
            symbol,
            module_all=module_all,
            strategy="all_then_underscore"
        ) is False

    def test_all_then_underscore_falls_back_to_underscore(self):
        """all_then_underscore falls back to underscore when no __all__."""
        symbol = MockSymbol(name="public_func", file="module.py")

        # No module_all, so uses underscore convention
        assert is_public_symbol(
            symbol,
            module_all=None,
            strategy="all_then_underscore"
        ) is True

    def test_all_only_requires_all(self):
        """all_only strategy requires __all__ to be defined."""
        symbol = MockSymbol(name="public_func", file="module.py")

        # No __all__ means nothing is public
        assert is_public_symbol(
            symbol,
            module_all=None,
            strategy="all_only"
        ) is False

    def test_all_only_respects_all(self):
        """all_only strategy respects __all__ when defined."""
        symbol = MockSymbol(name="exported", file="module.py")
        module_all = {"exported"}

        assert is_public_symbol(
            symbol,
            module_all=module_all,
            strategy="all_only"
        ) is True

    def test_underscore_only_ignores_all(self):
        """underscore_only strategy ignores __all__."""
        symbol = MockSymbol(name="not_in_all", file="module.py")
        module_all = {"other_func"}  # Symbol not in __all__

        # Despite not being in __all__, it's public because no underscore
        assert is_public_symbol(
            symbol,
            module_all=module_all,
            strategy="underscore_only"
        ) is True

    def test_underscore_only_respects_underscore(self):
        """underscore_only strategy respects underscore convention."""
        symbol = MockSymbol(name="_private", file="module.py")

        assert is_public_symbol(
            symbol,
            module_all=None,
            strategy="underscore_only"
        ) is False


class TestGoConventions:
    """Test Go language conventions."""

    def test_exported_function_is_public(self):
        """Go functions starting with uppercase are exported."""
        symbol = MockSymbol(name="ProcessData", file="handler.go")
        assert is_public_symbol(symbol) is True

    def test_unexported_function_is_private(self):
        """Go functions starting with lowercase are unexported."""
        symbol = MockSymbol(name="processData", file="handler.go")
        assert is_public_symbol(symbol) is False

    def test_exported_type_is_public(self):
        """Go types starting with uppercase are exported."""
        symbol = MockSymbol(name="DataHandler", file="types.go")
        assert is_public_symbol(symbol) is True


class TestJavaScriptConventions:
    """Test JavaScript/TypeScript conventions."""

    def test_public_function_js(self):
        """JS functions without underscore are public."""
        symbol = MockSymbol(name="handleClick", file="component.js")
        assert is_public_symbol(symbol) is True

    def test_private_function_js(self):
        """JS functions with underscore are private."""
        symbol = MockSymbol(name="_handleClick", file="component.js")
        assert is_public_symbol(symbol) is False

    def test_public_function_ts(self):
        """TS functions without underscore are public."""
        symbol = MockSymbol(name="processData", file="service.ts")
        assert is_public_symbol(symbol) is True

    def test_public_function_tsx(self):
        """TSX functions without underscore are public."""
        symbol = MockSymbol(name="MyComponent", file="Component.tsx")
        assert is_public_symbol(symbol) is True


class TestExtractModuleAll:
    """Test __all__ extraction from Python modules."""

    def test_extract_all_list(self, tmp_path):
        """Extract __all__ from a simple list definition."""
        test_file = tmp_path / "module_with_all.py"
        test_file.write_text(
            '__all__ = ["func1", "func2", "MyClass"]\n'
            'def func1(): pass\n'
            'def func2(): pass\n'
            'def _private(): pass\n'
            'class MyClass: pass\n'
        )
        result = extract_module_all(test_file)
        assert result == {"func1", "func2", "MyClass"}

    def test_no_all_returns_none(self, tmp_path):
        """Module without __all__ returns None."""
        test_file = tmp_path / "module_no_all.py"
        test_file.write_text(
            'def func1(): pass\n'
            'def func2(): pass\n'
        )
        result = extract_module_all(test_file)
        assert result is None

    def test_empty_all_returns_empty_set(self, tmp_path):
        """Empty __all__ returns empty set (no public API)."""
        test_file = tmp_path / "module_empty_all.py"
        test_file.write_text(
            '__all__ = []\n'
            'def _internal(): pass\n'
        )
        result = extract_module_all(test_file)
        assert result == set()

    def test_syntax_error_returns_none(self, tmp_path):
        """Files with syntax errors return None gracefully."""
        test_file = tmp_path / "broken_module.py"
        test_file.write_text('def broken(\n')  # Syntax error
        result = extract_module_all(test_file)
        assert result is None


class TestMatchesAnyPattern:
    """Test the matches_any_pattern utility function."""

    def test_exact_match(self):
        """Exact string matches pattern."""
        assert matches_any_pattern("Config", ["Config", "Meta"]) is True

    def test_no_match(self):
        """Non-matching string returns False."""
        assert matches_any_pattern("MyClass", ["Config", "Meta"]) is False

    def test_wildcard_suffix(self):
        """Wildcard suffix matches."""
        assert matches_any_pattern("validate_email", ["validate_*"]) is True

    def test_wildcard_prefix(self):
        """Wildcard prefix matches."""
        assert matches_any_pattern("TestSomething", ["Test*"]) is True

    def test_wildcard_middle(self):
        """Wildcard in middle matches."""
        assert matches_any_pattern("my_internal_helper", ["my_*_helper"]) is True

    def test_empty_patterns(self):
        """Empty pattern list returns False."""
        assert matches_any_pattern("anything", []) is False

    def test_question_mark_wildcard(self):
        """Question mark matches single character."""
        assert matches_any_pattern("test_a", ["test_?"]) is True
        assert matches_any_pattern("test_ab", ["test_?"]) is False


class TestApiCoverageConfigModel:
    """Test ApiCoverageConfig Pydantic model."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = ApiCoverageConfig()
        assert config.strategy == "all_then_underscore"
        assert config.preset is None
        assert config.exclude_symbols == []
        assert config.include_symbols == []

    def test_preset_validation(self):
        """Only valid presets are accepted."""
        # Valid presets
        for preset in ["pydantic", "django", "fastapi", "pytest"]:
            config = ApiCoverageConfig(preset=preset)
            assert config.preset == preset

    def test_custom_patterns(self):
        """Custom patterns are stored correctly."""
        config = ApiCoverageConfig(
            exclude_symbols=["internal_*", "helper_*"],
            include_symbols=["public_api"]
        )
        assert config.exclude_symbols == ["internal_*", "helper_*"]
        assert config.include_symbols == ["public_api"]

    def test_resolved_patterns_no_preset(self):
        """Resolved patterns without preset returns only custom."""
        config = ApiCoverageConfig(
            exclude_symbols=["my_pattern"]
        )
        patterns = config.get_resolved_exclude_patterns()
        assert patterns == ["my_pattern"]

    def test_resolved_patterns_with_preset(self):
        """Resolved patterns with preset merges both."""
        config = ApiCoverageConfig(
            preset="pydantic",
            exclude_symbols=["my_pattern"]
        )
        patterns = config.get_resolved_exclude_patterns()

        # Should have preset patterns
        assert "Config" in patterns
        assert "model_validator" in patterns
        # Plus custom
        assert "my_pattern" in patterns


class TestPresetsExist:
    """Verify presets are properly defined."""

    def test_pydantic_preset_exists(self):
        """Pydantic preset is defined with expected patterns."""
        assert "pydantic" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["pydantic"]["exclude_symbols"]
        assert "Config" in patterns
        assert "model_validator" in patterns

    def test_django_preset_exists(self):
        """Django preset is defined with expected patterns."""
        assert "django" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["django"]["exclude_symbols"]
        assert "Meta" in patterns
        assert "DoesNotExist" in patterns

    def test_fastapi_preset_exists(self):
        """FastAPI preset is defined with expected patterns."""
        assert "fastapi" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["fastapi"]["exclude_symbols"]
        assert "Config" in patterns

    def test_pytest_preset_exists(self):
        """Pytest preset is defined with expected patterns."""
        assert "pytest" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["pytest"]["exclude_symbols"]
        assert "test_*" in patterns
        assert "Test*" in patterns

    def test_sqlalchemy_preset_exists(self):
        """SQLAlchemy preset is defined with expected patterns."""
        assert "sqlalchemy" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["sqlalchemy"]["exclude_symbols"]
        assert "metadata" in patterns
        assert "__table__" in patterns
        assert "_sa_*" in patterns

    def test_jest_preset_exists(self):
        """Jest preset is defined with expected patterns."""
        assert "jest" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["jest"]["exclude_symbols"]
        assert "describe" in patterns
        assert "it" in patterns
        assert "test" in patterns
        assert "expect" in patterns

    def test_vitest_preset_exists(self):
        """Vitest preset is defined with expected patterns."""
        assert "vitest" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["vitest"]["exclude_symbols"]
        assert "describe" in patterns
        assert "vi" in patterns
        assert "suite" in patterns

    def test_react_preset_exists(self):
        """React preset is defined with expected patterns."""
        assert "react" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["react"]["exclude_symbols"]
        assert "UNSAFE_*" in patterns
        assert "$$typeof" in patterns

    def test_vue_preset_exists(self):
        """Vue preset is defined with expected patterns."""
        assert "vue" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["vue"]["exclude_symbols"]
        assert "$_*" in patterns
        assert "__v*" in patterns

    def test_go_test_preset_exists(self):
        """Go test preset is defined with expected patterns."""
        assert "go-test" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["go-test"]["exclude_symbols"]
        assert "Test*" in patterns
        assert "Benchmark*" in patterns
        assert "Example*" in patterns
        assert "Fuzz*" in patterns

    def test_rust_test_preset_exists(self):
        """Rust test preset is defined with expected patterns."""
        assert "rust-test" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["rust-test"]["exclude_symbols"]
        assert "tests" in patterns
        assert "test_*" in patterns
        assert "bench_*" in patterns

    def test_serde_preset_exists(self):
        """Serde preset is defined with expected patterns."""
        assert "serde" in API_COVERAGE_PRESETS
        patterns = API_COVERAGE_PRESETS["serde"]["exclude_symbols"]
        assert "Serialize" in patterns
        assert "Deserialize" in patterns
        assert "__serde_*" in patterns
