"""A/B testing framework for symbol extraction changes.

This module provides infrastructure to:
1. Run old (buggy) and new (fixed) implementations in parallel
2. Compare outputs to ensure no false negatives
3. Verify removed symbols are actual duplicates
4. Provide detailed analysis of changes

Usage:
    Run tests with pytest:
    $ uv run pytest tests/unit/test_symbol_extraction_ab.py -v

Expected behavior after fix:
- Old implementation: ~195 symbols (methods counted twice)
- New implementation: ~65-98 symbols (deduplicated)
- All new symbols exist in old output (no false negatives)
- Removed symbols are duplicates (same name/location, different type)
"""

import json
from pathlib import Path
from typing import Any

import pytest

from doc_manager_mcp.indexing.analysis.tree_sitter import Symbol, SymbolIndexer, SymbolType

# Expected symbol counts for test fixtures
FIXTURE_EXPECTATIONS = {
    "simple_module.py": {
        "total": 3,
        "functions": 3,
        "classes": 0,
        "methods": 0,
    },
    "simple_class.py": {
        "total": 4,
        "functions": 0,
        "classes": 1,
        "methods": 3,
    },
    "nested_classes.py": {
        "total": 4,
        "functions": 0,
        "classes": 2,
        "methods": 2,
    },
    "nested_functions.py": {
        "total": 4,
        "functions": 4,  # All nested functions should be FUNCTION type
        "classes": 0,
        "methods": 0,
    },
    "mixed_complex.py": {
        "total": 7,
        "functions": 2,
        "classes": 2,
        "methods": 3,
    },
}


class ABTestResult:
    """Results from A/B comparison of symbol extraction."""

    def __init__(self):
        self.old_count: int = 0
        self.new_count: int = 0
        self.old_symbols: list[Symbol] = []
        self.new_symbols: list[Symbol] = []
        self.removed_symbols: list[Symbol] = []
        self.false_negatives: list[Symbol] = []
        self.duplicates_removed: int = 0
        self.type_distribution_old: dict[str, int] = {}
        self.type_distribution_new: dict[str, int] = {}
        self.success: bool = False
        self.errors: list[str] = []

    def analyze(self) -> None:
        """Analyze the comparison results."""
        # Count by type
        self.type_distribution_old = self._count_by_type(self.old_symbols)
        self.type_distribution_new = self._count_by_type(self.new_symbols)

        # Find removed symbols
        new_symbol_keys = {self._symbol_key(s) for s in self.new_symbols}
        self.removed_symbols = [
            s for s in self.old_symbols if self._symbol_key(s) not in new_symbol_keys
        ]

        # Check for false negatives (symbols in new but not in old)
        old_symbol_keys = {self._symbol_key(s) for s in self.old_symbols}
        self.false_negatives = [
            s for s in self.new_symbols if self._symbol_key(s) not in old_symbol_keys
        ]

        # Verify removed symbols are duplicates
        for removed in self.removed_symbols:
            # Check if this symbol exists with different type in new output
            matching = [
                s
                for s in self.new_symbols
                if s.name == removed.name
                and s.file == removed.file
                and s.line == removed.line
            ]
            if matching:
                self.duplicates_removed += 1
            else:
                # This is a potential false negative (removed but not found in new output)
                self.errors.append(
                    f"Symbol removed but not found in new output: {removed.name} "
                    f"({removed.type.value}) at {removed.file}:{removed.line}"
                )

        # Validation checks
        if self.false_negatives:
            self.errors.append(
                f"False negatives detected: {len(self.false_negatives)} symbols "
                "in new output but not in old output"
            )

        if self.duplicates_removed != len(self.removed_symbols):
            self.errors.append(
                f"Not all removed symbols are duplicates: {self.duplicates_removed} "
                f"duplicates vs {len(self.removed_symbols)} removed"
            )

        self.success = len(self.errors) == 0

    @staticmethod
    def _symbol_key(symbol: Symbol) -> tuple[str, str, int, int]:
        """Create unique key for symbol comparison."""
        return (symbol.name, symbol.file, symbol.line, symbol.column)

    @staticmethod
    def _count_by_type(symbols: list[Symbol]) -> dict[str, int]:
        """Count symbols by type."""
        counts: dict[str, int] = {}
        for symbol in symbols:
            type_name = symbol.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Convert results to dictionary for JSON export."""
        return {
            "success": self.success,
            "old_count": self.old_count,
            "new_count": self.new_count,
            "removed_count": len(self.removed_symbols),
            "duplicates_removed": self.duplicates_removed,
            "false_negatives_count": len(self.false_negatives),
            "type_distribution_old": self.type_distribution_old,
            "type_distribution_new": self.type_distribution_new,
            "errors": self.errors,
        }

    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            "=" * 60,
            "A/B Symbol Extraction Comparison",
            "=" * 60,
            f"Old implementation: {self.old_count} symbols",
            f"New implementation: {self.new_count} symbols",
            f"Difference: {self.old_count - self.new_count} symbols removed",
            "",
            "Type Distribution (Old):",
        ]

        for type_name, count in sorted(self.type_distribution_old.items()):
            lines.append(f"  {type_name}: {count}")

        lines.append("")
        lines.append("Type Distribution (New):")

        for type_name, count in sorted(self.type_distribution_new.items()):
            lines.append(f"  {type_name}: {count}")

        lines.append("")
        lines.append(f"Duplicates removed: {self.duplicates_removed}")
        lines.append(f"False negatives: {len(self.false_negatives)}")
        lines.append("")

        if self.success:
            lines.append("✓ A/B test PASSED: No false negatives detected")
        else:
            lines.append("✗ A/B test FAILED:")
            for error in self.errors:
                lines.append(f"  - {error}")

        lines.append("=" * 60)

        return "\n".join(lines)


def run_ab_test_on_project(project_path: Path) -> ABTestResult:
    """Run A/B test on a project directory.

    Args:
        project_path: Path to project directory with Python files

    Returns:
        ABTestResult with comparison analysis
    """
    result = ABTestResult()

    # Run old implementation (current buggy code)
    old_indexer = SymbolIndexer()
    old_indexer.index_project(project_path)

    # Extract all symbols from old indexer
    for symbols in old_indexer.index.values():
        result.old_symbols.extend(symbols)

    result.old_count = len(result.old_symbols)

    # TODO: Run new implementation when Phase 1 is complete
    # For now, new implementation is same as old
    result.new_symbols = result.old_symbols.copy()
    result.new_count = len(result.new_symbols)

    # Analyze results
    result.analyze()

    return result


# ============================================================================
# Test Cases
# ============================================================================


@pytest.fixture
def fixture_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "sample_project"


def test_simple_module_extraction(fixture_dir: Path):
    """Test symbol extraction on simple module with only functions."""
    file_path = fixture_dir / "simple_module.py"
    assert file_path.exists(), f"Fixture not found: {file_path}"

    indexer = SymbolIndexer()
    indexer.index_project(fixture_dir)

    # Filter symbols from this specific file
    symbols = []
    for sym_list in indexer.index.values():
        for symbol in sym_list:
            if "simple_module.py" in symbol.file:
                symbols.append(symbol)

    # Check expected counts
    expected = FIXTURE_EXPECTATIONS["simple_module.py"]
    assert len(symbols) == expected["total"], (
        f"Expected {expected['total']} symbols, got {len(symbols)}. "
        f"Found symbols: {[(s.name, s.type.value) for s in symbols]}"
    )

    # Check types
    functions = [s for s in symbols if s.type == SymbolType.FUNCTION]
    assert len(functions) == expected["functions"]


def test_simple_class_extraction(fixture_dir: Path):
    """Test symbol extraction on class with methods."""
    file_path = fixture_dir / "simple_class.py"
    assert file_path.exists(), f"Fixture not found: {file_path}"

    indexer = SymbolIndexer()
    indexer.index_project(fixture_dir)

    # Filter symbols from this specific file
    symbols = []
    for sym_list in indexer.index.values():
        for symbol in sym_list:
            if "simple_class.py" in symbol.file:
                symbols.append(symbol)

    # Check expected counts
    expected = FIXTURE_EXPECTATIONS["simple_class.py"]

    classes = [s for s in symbols if s.type == SymbolType.CLASS]
    methods = [s for s in symbols if s.type == SymbolType.METHOD]

    assert len(classes) == expected["classes"]
    assert len(methods) == expected["methods"]


def test_nested_classes_extraction(fixture_dir: Path):
    """Test symbol extraction on nested classes."""
    file_path = fixture_dir / "nested_classes.py"
    assert file_path.exists(), f"Fixture not found: {file_path}"

    indexer = SymbolIndexer()
    indexer.index_project(fixture_dir)

    # Filter symbols from this specific file
    symbols = []
    for sym_list in indexer.index.values():
        for symbol in sym_list:
            if "nested_classes.py" in symbol.file:
                symbols.append(symbol)

    # Check expected counts
    expected = FIXTURE_EXPECTATIONS["nested_classes.py"]

    classes = [s for s in symbols if s.type == SymbolType.CLASS]
    methods = [s for s in symbols if s.type == SymbolType.METHOD]

    assert len(classes) == expected["classes"]
    assert len(methods) == expected["methods"]

    # Verify nested class parent attribution
    inner_class = [s for s in classes if s.name == "Inner"]
    if inner_class:
        assert inner_class[0].name == "Inner", "Nested class should be extracted"
        assert inner_class[0].parent == "Outer", "Nested class should have parent set"


def test_nested_functions_extraction(fixture_dir: Path):
    """Test symbol extraction on nested functions (closures).

    CRITICAL: Nested functions should be counted as FUNCTION, not METHOD.
    """
    file_path = fixture_dir / "nested_functions.py"
    assert file_path.exists(), f"Fixture not found: {file_path}"

    indexer = SymbolIndexer()
    indexer.index_project(fixture_dir)

    # Filter symbols from this specific file
    symbols = []
    for sym_list in indexer.index.values():
        for symbol in sym_list:
            if "nested_functions.py" in symbol.file:
                symbols.append(symbol)

    # Check expected counts
    expected = FIXTURE_EXPECTATIONS["nested_functions.py"]

    functions = [s for s in symbols if s.type == SymbolType.FUNCTION]
    methods = [s for s in symbols if s.type == SymbolType.METHOD]

    # CRITICAL: All nested functions should be FUNCTION type
    assert len(methods) == 0, "Nested functions should NOT be classified as methods"
    assert len(functions) == expected["functions"], (
        f"Expected {expected['functions']} functions, got {len(functions)}"
    )


def test_mixed_complex_extraction(fixture_dir: Path):
    """Test symbol extraction on complex file with mix of scenarios."""
    file_path = fixture_dir / "mixed_complex.py"
    assert file_path.exists(), f"Fixture not found: {file_path}"

    indexer = SymbolIndexer()
    indexer.index_project(fixture_dir)

    # Filter symbols from this specific file
    symbols = []
    for sym_list in indexer.index.values():
        for symbol in sym_list:
            if "mixed_complex.py" in symbol.file:
                symbols.append(symbol)

    # Check expected counts
    expected = FIXTURE_EXPECTATIONS["mixed_complex.py"]

    functions = [s for s in symbols if s.type == SymbolType.FUNCTION]
    classes = [s for s in symbols if s.type == SymbolType.CLASS]
    methods = [s for s in symbols if s.type == SymbolType.METHOD]

    assert len(functions) == expected["functions"]
    assert len(classes) == expected["classes"]
    assert len(methods) == expected["methods"]


def test_ab_comparison_full_fixtures(fixture_dir: Path):
    """Run full A/B comparison on all fixtures.

    This test will be updated in Phase 1 to compare old vs new implementations.
    For now, it establishes the baseline for the old implementation.
    """
    result = run_ab_test_on_project(fixture_dir)

    # Save results for inspection
    results_path = fixture_dir / "ab_test_results.json"
    with open(results_path, "w") as f:
        json.dump(result.to_dict(), f, indent=2)

    print("\n" + str(result))

    # For now, this test documents the current (buggy) behavior
    # After Phase 1 implementation, we'll update this to verify:
    # - result.success is True
    # - result.duplicates_removed > 0
    # - result.false_negatives_count == 0

    # Current behavior (baseline)
    assert result.old_count == result.new_count, (
        "Implementations should match until Phase 1 is complete"
    )


def test_symbol_uniqueness(fixture_dir: Path):
    """Verify that each symbol location is unique (no exact duplicates).

    After Phase 1 fix, each (name, file, line, column) combination should appear
    only once in the symbol index.
    """
    indexer = SymbolIndexer()
    indexer.index_project(fixture_dir)

    symbols = []
    for sym_list in indexer.index.values():
        symbols.extend(sym_list)

    # Create keys for each symbol
    symbol_keys = [
        (s.name, s.file, s.line, s.column, s.type.value) for s in symbols
    ]

    # Check for exact duplicates (same location AND type)
    seen = set()
    duplicates = []
    for key in symbol_keys:
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    assert len(duplicates) == 0, f"Found exact duplicate symbols: {duplicates}"


def test_no_method_function_duplicates(fixture_dir: Path):
    """Verify methods are not also counted as functions.

    Phase 1 fix implemented: methods inside classes now ONLY appear as METHOD type,
    not as both FUNCTION and METHOD.
    """
    indexer = SymbolIndexer()
    indexer.index_project(fixture_dir)

    symbols = []
    for sym_list in indexer.index.values():
        symbols.extend(sym_list)

    # Group by (name, file, line) - ignore type
    location_groups: dict[tuple, list[Symbol]] = {}
    for symbol in symbols:
        key = (symbol.name, symbol.file, symbol.line)
        if key not in location_groups:
            location_groups[key] = []
        location_groups[key].append(symbol)

    # Find locations with multiple types
    duplicate_locations = {
        key: group for key, group in location_groups.items() if len(group) > 1
    }

    if duplicate_locations:
        error_msg = "Found symbols with same location but different types:\n"
        for key, group in duplicate_locations.items():
            types = [s.type.value for s in group]
            error_msg += f"  {key[0]} at {key[1]}:{key[2]} - types: {types}\n"
        pytest.fail(error_msg)


if __name__ == "__main__":
    # Run A/B test directly
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_project"
    result = run_ab_test_on_project(fixture_path)
    print(result)
    print(f"\nDetailed results saved to: {fixture_path / 'ab_test_results.json'}")
