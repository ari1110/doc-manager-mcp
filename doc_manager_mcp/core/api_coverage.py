"""API coverage configuration and symbol filtering.

This module provides configurable symbol filtering for API documentation coverage
metrics, following industry standards from Sphinx autodoc, mkdocstrings, and pdoc.

Key features:
- Presets for common frameworks across multiple languages
- Custom pattern-based symbol exclusion/inclusion
- fnmatch (shell-style) pattern matching

Supported presets by language:
- Python: pydantic, django, fastapi, pytest, sqlalchemy
- JavaScript/TypeScript: jest, vitest, react, vue
- Go: go-test
- Rust: rust-test, serde
"""

from fnmatch import fnmatch
from typing import Literal

from pydantic import BaseModel, Field

# Built-in presets for common frameworks
API_COVERAGE_PRESETS: dict[str, dict[str, list[str]]] = {
    # ===================
    # Python Frameworks
    # ===================
    "pydantic": {
        "exclude_symbols": [
            "Config",
            "model_config",
            "model_validator",
            "field_validator",
            "root_validator",
            "validator",
            "validate_*",
        ]
    },
    "django": {
        "exclude_symbols": [
            "Meta",
            "DoesNotExist",
            "MultipleObjectsReturned",
        ]
    },
    "fastapi": {
        "exclude_symbols": [
            "Config",
            "model_config",
        ]
    },
    "pytest": {
        "exclude_symbols": [
            "test_*",
            "Test*",
            "fixture",
            "conftest",
        ]
    },
    "sqlalchemy": {
        "exclude_symbols": [
            "metadata",
            "__table__",
            "__tablename__",
            "__mapper__",
            "_sa_*",
            "registry",
        ]
    },
    # ===========================
    # JavaScript/TypeScript
    # ===========================
    "jest": {
        "exclude_symbols": [
            "describe",
            "it",
            "test",
            "beforeEach",
            "afterEach",
            "beforeAll",
            "afterAll",
            "expect",
        ]
    },
    "vitest": {
        "exclude_symbols": [
            "describe",
            "it",
            "test",
            "suite",
            "beforeEach",
            "afterEach",
            "beforeAll",
            "afterAll",
            "expect",
            "vi",
        ]
    },
    "react": {
        "exclude_symbols": [
            "_render*",
            "UNSAFE_*",
            "__*",
            "$$typeof",
        ]
    },
    "vue": {
        "exclude_symbols": [
            "$_*",
            "__v*",
            "_c",
            "_h",
            "_s",
            "_v",
            "_e",
            "_m",
            "_l",
        ]
    },
    # ===================
    # Go Frameworks
    # ===================
    "go-test": {
        "exclude_symbols": [
            "Test*",
            "Benchmark*",
            "Example*",
            "Fuzz*",
        ]
    },
    # ===================
    # Rust Frameworks
    # ===================
    "rust-test": {
        "exclude_symbols": [
            "tests",
            "test_*",
            "bench_*",
        ]
    },
    "serde": {
        "exclude_symbols": [
            "Serialize",
            "Deserialize",
            "__serde_*",
        ]
    },
}

# Valid preset names
PresetName = Literal[
    # Python
    "pydantic", "django", "fastapi", "pytest", "sqlalchemy",
    # JavaScript/TypeScript
    "jest", "vitest", "react", "vue",
    # Go
    "go-test",
    # Rust
    "rust-test", "serde",
]

# Valid strategy names
StrategyName = Literal["all_then_underscore", "all_only", "underscore_only"]


class ApiCoverageConfig(BaseModel):
    """Configuration for API coverage symbol filtering.

    Attributes:
        strategy: How to determine public symbols.
            - "all_then_underscore": Use __all__ if defined, else underscore convention
            - "all_only": Only symbols in __all__ are public (strict)
            - "underscore_only": Only use underscore convention, ignore __all__
        preset: Optional preset name for common frameworks.
        exclude_symbols: Patterns for symbols to exclude (fnmatch syntax).
        include_symbols: Patterns for symbols to force-include (overrides exclusions).
    """

    strategy: StrategyName = Field(
        default="all_then_underscore",
        description="Strategy for determining public symbols"
    )
    preset: PresetName | None = Field(
        default=None,
        description="Preset for common frameworks (see API_COVERAGE_PRESETS for full list)"
    )
    exclude_symbols: list[str] = Field(
        default_factory=list,
        description="Patterns for symbols to exclude (fnmatch syntax)"
    )
    include_symbols: list[str] = Field(
        default_factory=list,
        description="Patterns for symbols to force-include"
    )

    def get_resolved_exclude_patterns(self) -> list[str]:
        """Get merged exclude patterns from preset + custom.

        Returns:
            Combined list of exclude patterns (preset patterns first, then custom).
        """
        patterns: list[str] = []

        # Add preset patterns if specified
        if self.preset and self.preset in API_COVERAGE_PRESETS:
            preset_patterns = API_COVERAGE_PRESETS[self.preset].get("exclude_symbols", [])
            patterns.extend(preset_patterns)

        # Add custom patterns
        patterns.extend(self.exclude_symbols)

        return patterns


def matches_any_pattern(name: str, patterns: list[str]) -> bool:
    """Check if a symbol name matches any of the given patterns.

    Uses fnmatch (shell-style) pattern matching:
    - * matches everything
    - ? matches single character
    - [seq] matches any character in seq
    - [!seq] matches any character NOT in seq

    Args:
        name: Symbol name to check
        patterns: List of fnmatch patterns

    Returns:
        True if name matches any pattern, False otherwise
    """
    return any(fnmatch(name, pattern) for pattern in patterns)


def get_default_config() -> ApiCoverageConfig:
    """Get default API coverage configuration.

    Returns:
        ApiCoverageConfig with default values (industry-standard behavior).
    """
    return ApiCoverageConfig()
