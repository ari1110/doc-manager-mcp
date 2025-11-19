"""Comprehensive tests for Phase 1 semantic change detection.

This module tests the semantic change detection functionality including:
- Symbol comparison and change detection
- Baseline persistence (save/load)
- Integration with map_changes tool
- Error handling and edge cases
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from doc_manager_mcp.indexing.semantic_diff import (
    SemanticChange,
    _is_public_api,
    compare_symbols,
    load_symbol_baseline,
    save_symbol_baseline,
)
from doc_manager_mcp.indexing.tree_sitter import Symbol, SymbolType


class TestCompareSymbols:
    """Tests for symbol comparison and change detection."""

    def test_compare_symbols_added(self):
        """Test detection of added functions/classes."""
        old_symbols = {
            "file1.py": [
                Symbol(
                    name="existing_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def existing_func():",
                )
            ]
        }

        new_symbols = {
            "file1.py": [
                Symbol(
                    name="existing_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def existing_func():",
                ),
                Symbol(
                    name="new_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=20,
                    column=0,
                    signature="def new_func():",
                ),
            ]
        }

        changes = compare_symbols(old_symbols, new_symbols)

        # Should detect one added function
        assert len(changes) == 1
        assert changes[0].change_type == "added"
        assert changes[0].name == "new_func"
        assert changes[0].symbol_type == "function"
        assert changes[0].severity == "non-breaking"
        assert changes[0].old_signature is None
        assert changes[0].new_signature == "def new_func():"

    def test_compare_symbols_removed(self):
        """Test detection of removed symbols (breaking severity)."""
        old_symbols = {
            "file1.py": [
                Symbol(
                    name="removed_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def removed_func():",
                ),
                Symbol(
                    name="kept_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=20,
                    column=0,
                    signature="def kept_func():",
                ),
            ]
        }

        new_symbols = {
            "file1.py": [
                Symbol(
                    name="kept_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=20,
                    column=0,
                    signature="def kept_func():",
                )
            ]
        }

        changes = compare_symbols(old_symbols, new_symbols)

        # Should detect one removed function with breaking severity
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].name == "removed_func"
        assert changes[0].severity == "breaking"
        assert changes[0].line is None  # No line in new version
        assert changes[0].new_signature is None
        assert changes[0].old_signature == "def removed_func():"

    def test_compare_symbols_signature_changed(self):
        """Test detection of signature changes."""
        old_symbols = {
            "file1.py": [
                Symbol(
                    name="my_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def my_func(x):",
                )
            ]
        }

        new_symbols = {
            "file1.py": [
                Symbol(
                    name="my_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def my_func(x, y):",
                )
            ]
        }

        changes = compare_symbols(old_symbols, new_symbols)

        # Should detect signature change
        assert len(changes) == 1
        assert changes[0].change_type == "signature_changed"
        assert changes[0].name == "my_func"
        assert changes[0].old_signature == "def my_func(x):"
        assert changes[0].new_signature == "def my_func(x, y):"
        # Public function -> breaking change
        assert changes[0].severity == "breaking"

    def test_compare_symbols_implementation_changed(self):
        """Test detection of non-breaking implementation changes."""
        old_symbols = {
            "file1.py": [
                Symbol(
                    name="my_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def my_func():",
                    doc="Old docstring",
                )
            ]
        }

        new_symbols = {
            "file1.py": [
                Symbol(
                    name="my_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=15,  # Line changed
                    column=0,
                    signature="def my_func():",  # Same signature
                    doc="New docstring",  # Doc changed
                )
            ]
        }

        changes = compare_symbols(old_symbols, new_symbols)

        # Should detect implementation change (line/doc changed, signature same)
        assert len(changes) == 1
        assert changes[0].change_type == "modified"
        assert changes[0].name == "my_func"
        assert changes[0].severity == "non-breaking"
        assert changes[0].old_signature == changes[0].new_signature

    def test_compare_symbols_severity_classification(self):
        """Test severity classification for public vs private API."""
        # Test Python private function (underscore prefix)
        old_symbols_py = {
            "file.py": [
                Symbol(
                    name="_private_func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                    signature="def _private_func(x):",
                )
            ]
        }

        new_symbols_py = {
            "file.py": [
                Symbol(
                    name="_private_func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                    signature="def _private_func(x, y):",
                )
            ]
        }

        changes = compare_symbols(old_symbols_py, new_symbols_py)
        # Private function signature change -> non-breaking
        assert changes[0].severity == "non-breaking"

        # Test Go public function (uppercase first letter)
        old_symbols_go = {
            "file.go": [
                Symbol(
                    name="PublicFunc",
                    type=SymbolType.FUNCTION,
                    file="file.go",
                    line=10,
                    column=0,
                    signature="func PublicFunc(x int)",
                )
            ]
        }

        new_symbols_go = {
            "file.go": [
                Symbol(
                    name="PublicFunc",
                    type=SymbolType.FUNCTION,
                    file="file.go",
                    line=10,
                    column=0,
                    signature="func PublicFunc(x, y int)",
                )
            ]
        }

        changes = compare_symbols(old_symbols_go, new_symbols_go)
        # Public function signature change -> breaking
        assert changes[0].severity == "breaking"

        # Test Go private function (lowercase first letter)
        old_symbols_go_private = {
            "file.go": [
                Symbol(
                    name="privateFunc",
                    type=SymbolType.FUNCTION,
                    file="file.go",
                    line=10,
                    column=0,
                    signature="func privateFunc(x int)",
                )
            ]
        }

        new_symbols_go_private = {
            "file.go": [
                Symbol(
                    name="privateFunc",
                    type=SymbolType.FUNCTION,
                    file="file.go",
                    line=10,
                    column=0,
                    signature="func privateFunc(x, y int)",
                )
            ]
        }

        changes = compare_symbols(old_symbols_go_private, new_symbols_go_private)
        # Private function signature change -> non-breaking
        assert changes[0].severity == "non-breaking"

    def test_compare_symbols_sorting(self):
        """Test that changes are sorted by severity (breaking first) then file path."""
        old_symbols = {
            "b_file.py": [
                Symbol(
                    name="func1",
                    type=SymbolType.FUNCTION,
                    file="b_file.py",
                    line=10,
                    column=0,
                    signature="def func1():",
                )
            ],
            "a_file.py": [
                Symbol(
                    name="func2",
                    type=SymbolType.FUNCTION,
                    file="a_file.py",
                    line=10,
                    column=0,
                    signature="def func2():",
                )
            ],
        }

        new_symbols = {
            "b_file.py": [
                # Keep func1, add new_func
                Symbol(
                    name="func1",
                    type=SymbolType.FUNCTION,
                    file="b_file.py",
                    line=10,
                    column=0,
                    signature="def func1():",
                ),
                Symbol(
                    name="new_func",
                    type=SymbolType.FUNCTION,
                    file="b_file.py",
                    line=20,
                    column=0,
                    signature="def new_func():",
                )
            ]
            # func2 removed -> breaking change in a_file.py
        }

        changes = compare_symbols(old_symbols, new_symbols)

        # Should have 2 changes: 1 removed (breaking), 1 added (non-breaking)
        assert len(changes) == 2
        # First: breaking change (removed func2 from a_file.py)
        assert changes[0].severity == "breaking"
        assert changes[0].change_type == "removed"
        assert changes[0].file == "a_file.py"
        # Second: non-breaking change (added new_func to b_file.py)
        assert changes[1].severity == "non-breaking"
        assert changes[1].change_type == "added"
        assert changes[1].file == "b_file.py"

    def test_compare_symbols_empty_baselines(self):
        """Test comparison with empty baselines."""
        # Empty old, some new -> all added
        changes = compare_symbols({}, {"file.py": [
            Symbol(
                name="func",
                type=SymbolType.FUNCTION,
                file="file.py",
                line=10,
                column=0,
                signature="def func():",
            )
        ]})
        assert len(changes) == 1
        assert changes[0].change_type == "added"

        # Some old, empty new -> all removed
        changes = compare_symbols({
            "file.py": [
                Symbol(
                    name="func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                    signature="def func():",
                )
            ]
        }, {})
        assert len(changes) == 1
        assert changes[0].change_type == "removed"

        # Both empty -> no changes
        changes = compare_symbols({}, {})
        assert len(changes) == 0

    def test_compare_symbols_multiple_files(self):
        """Test comparison across multiple files."""
        old_symbols = {
            "file1.py": [
                Symbol(
                    name="func1",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def func1():",
                )
            ],
            "file2.py": [
                Symbol(
                    name="func2",
                    type=SymbolType.FUNCTION,
                    file="file2.py",
                    line=10,
                    column=0,
                    signature="def func2():",
                )
            ],
        }

        new_symbols = {
            "file1.py": [
                Symbol(
                    name="func1",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=0,
                    signature="def func1(x):",  # Signature changed
                )
            ],
            "file2.py": [
                Symbol(
                    name="func2",
                    type=SymbolType.FUNCTION,
                    file="file2.py",
                    line=10,
                    column=0,
                    signature="def func2():",  # Unchanged
                )
            ],
        }

        changes = compare_symbols(old_symbols, new_symbols)

        # Should only detect the signature change in file1
        assert len(changes) == 1
        assert changes[0].change_type == "signature_changed"
        assert changes[0].file == "file1.py"


class TestBaselinePersistence:
    """Tests for baseline save/load functionality."""

    def test_save_and_load_baseline(self, tmp_path):
        """Test round-trip JSON serialization of baseline."""
        baseline_path = tmp_path / "symbol-baseline.json"

        # Create test symbols
        symbols = {
            "file1.py": [
                Symbol(
                    name="test_func",
                    type=SymbolType.FUNCTION,
                    file="file1.py",
                    line=10,
                    column=5,
                    signature="def test_func():",
                    parent=None,
                    doc="Test docstring",
                )
            ],
            "file2.py": [
                Symbol(
                    name="TestClass",
                    type=SymbolType.CLASS,
                    file="file2.py",
                    line=20,
                    column=0,
                    signature=None,
                    parent=None,
                    doc=None,
                ),
                Symbol(
                    name="test_method",
                    type=SymbolType.METHOD,
                    file="file2.py",
                    line=25,
                    column=4,
                    signature="def test_method(self):",
                    parent="TestClass",
                    doc=None,
                ),
            ],
        }

        # Save baseline
        save_symbol_baseline(baseline_path, symbols)

        # Verify file exists
        assert baseline_path.exists()

        # Load baseline
        loaded = load_symbol_baseline(baseline_path)

        # Verify loaded data matches original
        assert loaded is not None
        assert len(loaded) == 2
        assert "file1.py" in loaded
        assert "file2.py" in loaded

        # Check file1.py symbols
        assert len(loaded["file1.py"]) == 1
        sym = loaded["file1.py"][0]
        assert sym.name == "test_func"
        assert sym.type == SymbolType.FUNCTION
        assert sym.file == "file1.py"
        assert sym.line == 10
        assert sym.column == 5
        assert sym.signature == "def test_func():"
        assert sym.parent is None
        assert sym.doc == "Test docstring"

        # Check file2.py symbols
        assert len(loaded["file2.py"]) == 2
        class_sym = loaded["file2.py"][0]
        assert class_sym.name == "TestClass"
        assert class_sym.type == SymbolType.CLASS
        method_sym = loaded["file2.py"][1]
        assert method_sym.name == "test_method"
        assert method_sym.type == SymbolType.METHOD
        assert method_sym.parent == "TestClass"

    def test_load_baseline_missing_file(self, tmp_path):
        """Test that load returns None gracefully when file doesn't exist."""
        baseline_path = tmp_path / "nonexistent.json"
        result = load_symbol_baseline(baseline_path)
        assert result is None

    def test_load_baseline_invalid_json(self, tmp_path):
        """Test that load returns None on JSON parse errors."""
        baseline_path = tmp_path / "invalid.json"

        # Write invalid JSON
        baseline_path.write_text("{ this is not valid json }", encoding="utf-8")

        result = load_symbol_baseline(baseline_path)
        assert result is None

    def test_load_baseline_missing_symbols_key(self, tmp_path):
        """Test that load returns None when 'symbols' key is missing."""
        baseline_path = tmp_path / "baseline.json"

        # Write JSON without 'symbols' key
        baseline_path.write_text('{"version": "1.0"}', encoding="utf-8")

        result = load_symbol_baseline(baseline_path)
        assert result is None

    def test_load_baseline_invalid_structure(self, tmp_path):
        """Test that load returns None when JSON structure is invalid."""
        baseline_path = tmp_path / "baseline.json"

        # Write JSON that's not a dict
        baseline_path.write_text('["not", "a", "dict"]', encoding="utf-8")

        result = load_symbol_baseline(baseline_path)
        assert result is None

    def test_load_baseline_skips_invalid_symbols(self, tmp_path):
        """Test that invalid symbol entries are skipped but valid ones are loaded."""
        baseline_path = tmp_path / "baseline.json"

        # Write baseline with mix of valid and invalid symbols
        data = {
            "version": "1.0",
            "symbols": {
                "file.py": [
                    {
                        "name": "valid_func",
                        "type": "function",
                        "file": "file.py",
                        "line": 10,
                        "column": 0,
                        "signature": "def valid_func():",
                    },
                    {
                        "name": "invalid_symbol",
                        # Missing required fields
                    },
                    {
                        "name": "another_valid",
                        "type": "function",
                        "file": "file.py",
                        "line": 20,
                        "column": 0,
                    },
                ]
            },
        }
        baseline_path.write_text(json.dumps(data), encoding="utf-8")

        result = load_symbol_baseline(baseline_path)

        # Should load valid symbols and skip invalid one
        assert result is not None
        assert "file.py" in result
        assert len(result["file.py"]) == 2  # Only 2 valid symbols
        assert result["file.py"][0].name == "valid_func"
        assert result["file.py"][1].name == "another_valid"

    def test_save_baseline_atomic_write(self, tmp_path):
        """Test that save uses atomic write pattern (temp file + rename)."""
        baseline_path = tmp_path / "baseline.json"

        symbols = {
            "file.py": [
                Symbol(
                    name="func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                )
            ]
        }

        # Save baseline
        save_symbol_baseline(baseline_path, symbols)

        # Verify final file exists
        assert baseline_path.exists()

        # Verify no temp files left behind
        temp_files = list(tmp_path.glob(".symbol-baseline-*.tmp"))
        assert len(temp_files) == 0

    def test_save_baseline_creates_directory(self, tmp_path):
        """Test that save creates parent directory if it doesn't exist."""
        baseline_path = tmp_path / "nested" / "dir" / "baseline.json"

        symbols = {
            "file.py": [
                Symbol(
                    name="func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                )
            ]
        }

        # Directory doesn't exist yet
        assert not baseline_path.parent.exists()

        # Save should create directory
        save_symbol_baseline(baseline_path, symbols)

        # Verify directory and file exist
        assert baseline_path.parent.exists()
        assert baseline_path.exists()

    def test_save_baseline_preserves_created_at(self, tmp_path):
        """Test that save preserves created_at timestamp on updates."""
        baseline_path = tmp_path / "baseline.json"

        symbols_v1 = {
            "file.py": [
                Symbol(
                    name="func_v1",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                )
            ]
        }

        symbols_v2 = {
            "file.py": [
                Symbol(
                    name="func_v2",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=20,
                    column=0,
                )
            ]
        }

        # First save
        save_symbol_baseline(baseline_path, symbols_v1)

        # Read created_at timestamp
        with open(baseline_path, encoding="utf-8") as f:
            data_v1 = json.load(f)
        created_at_v1 = data_v1["created_at"]

        # Second save (update)
        save_symbol_baseline(baseline_path, symbols_v2)

        # Read timestamps again
        with open(baseline_path, encoding="utf-8") as f:
            data_v2 = json.load(f)

        # created_at should be preserved
        assert data_v2["created_at"] == created_at_v1
        # updated_at should be newer
        assert data_v2["updated_at"] != created_at_v1

    def test_save_baseline_invalid_input(self):
        """Test that save raises ValueError for invalid input."""
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"

            # Not a dict
            with pytest.raises(ValueError, match="must be a dictionary"):
                save_symbol_baseline(baseline_path, "not a dict")  # type: ignore

            # Not a dict
            with pytest.raises(ValueError, match="must be a dictionary"):
                save_symbol_baseline(baseline_path, ["not", "a", "dict"])  # type: ignore

    def test_baseline_json_format(self, tmp_path):
        """Test that saved JSON matches specification."""
        baseline_path = tmp_path / "baseline.json"

        symbols = {
            "file.py": [
                Symbol(
                    name="func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                    signature="def func():",
                    parent=None,
                    doc="Docstring",
                )
            ]
        }

        save_symbol_baseline(baseline_path, symbols)

        # Read and verify JSON structure
        with open(baseline_path, encoding="utf-8") as f:
            data = json.load(f)

        # Check required top-level fields
        assert "version" in data
        assert data["version"] == "1.0"
        assert "created_at" in data
        assert "updated_at" in data
        assert "project_root" in data
        assert "symbols" in data

        # Check symbols structure
        assert isinstance(data["symbols"], dict)
        assert "file.py" in data["symbols"]
        assert isinstance(data["symbols"]["file.py"], list)
        assert len(data["symbols"]["file.py"]) == 1

        # Check symbol fields
        sym = data["symbols"]["file.py"][0]
        assert sym["name"] == "func"
        assert sym["type"] == "function"
        assert sym["file"] == "file.py"
        assert sym["line"] == 10
        assert sym["column"] == 0
        assert sym["signature"] == "def func():"
        assert sym["parent"] is None
        assert sym["doc"] == "Docstring"


class TestIntegration:
    """Integration tests for semantic change detection with map_changes."""

    @patch("doc_manager_mcp.tools.changes.SymbolIndexer")
    def test_get_semantic_changes_first_run(self, mock_indexer_class, tmp_path):
        """Test that first run creates baseline and returns empty list."""
        from doc_manager_mcp.tools.changes import _get_semantic_changes

        # Setup mock indexer
        mock_indexer = MagicMock()
        mock_indexer.index_symbols.return_value = {
            "file.py": [
                Symbol(
                    name="func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                )
            ]
        }
        mock_indexer_class.return_value = mock_indexer

        # Create project directory structure
        memory_dir = tmp_path / ".doc-manager" / "memory"
        memory_dir.mkdir(parents=True)

        # First run (no baseline exists)
        changes = _get_semantic_changes(tmp_path)

        # Should return empty list on first run
        assert changes == []

        # Should have created baseline
        baseline_path = memory_dir / "symbol-baseline.json"
        assert baseline_path.exists()

    @patch("doc_manager_mcp.tools.changes.SymbolIndexer")
    def test_get_semantic_changes_subsequent_run(self, mock_indexer_class, tmp_path):
        """Test that subsequent runs detect changes."""
        from doc_manager_mcp.tools.changes import _get_semantic_changes

        # Create baseline first
        baseline_path = tmp_path / ".doc-manager" / "memory" / "symbol-baseline.json"
        baseline_path.parent.mkdir(parents=True, exist_ok=True)

        old_symbols = {
            "file.py": [
                Symbol(
                    name="old_func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                    signature="def old_func():",
                )
            ]
        }
        save_symbol_baseline(baseline_path, old_symbols)

        # Setup mock indexer to return new symbols
        mock_indexer = MagicMock()
        mock_indexer.index_symbols.return_value = {
            "file.py": [
                Symbol(
                    name="new_func",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=20,
                    column=0,
                    signature="def new_func():",
                )
            ]
        }
        mock_indexer_class.return_value = mock_indexer

        # Run semantic diff
        changes = _get_semantic_changes(tmp_path)

        # Should detect removed and added functions
        assert len(changes) == 2
        change_types = {c.change_type for c in changes}
        assert "removed" in change_types
        assert "added" in change_types

    @patch("doc_manager_mcp.tools.changes.SymbolIndexer")
    def test_get_semantic_changes_error_handling(self, mock_indexer_class, tmp_path):
        """Test that errors are handled gracefully and return empty list."""
        from doc_manager_mcp.tools.changes import _get_semantic_changes

        # Make indexer raise exception
        mock_indexer_class.side_effect = Exception("TreeSitter not available")

        # Should return empty list instead of crashing
        changes = _get_semantic_changes(tmp_path)
        assert changes == []

    @patch("doc_manager_mcp.tools.changes.SymbolIndexer")
    @patch("doc_manager_mcp.tools.changes._get_changed_files_from_checksums")
    @patch("doc_manager_mcp.tools.changes._load_baseline")
    @patch("doc_manager_mcp.tools.changes._map_to_affected_docs")
    def test_map_changes_with_semantic_enabled(
        self,
        mock_map_docs,
        mock_load_baseline,
        mock_get_changed_files,
        mock_indexer_class,
        tmp_path,
    ):
        """Test end-to-end map_changes with semantic analysis enabled."""
        import asyncio
        from doc_manager_mcp.models import MapChangesInput
        from doc_manager_mcp.tools.changes import map_changes
        from doc_manager_mcp.constants import ChangeDetectionMode

        # Setup mocks
        mock_load_baseline.return_value = {"files": {}, "timestamp": "2024-01-01"}
        mock_get_changed_files.return_value = [
            {"file": "src/main.py", "change_type": "modified"}
        ]
        mock_map_docs.return_value = []

        # Setup symbol indexer mock
        mock_indexer = MagicMock()
        mock_indexer.index_symbols.return_value = {
            "src/main.py": [
                Symbol(
                    name="new_func",
                    type=SymbolType.FUNCTION,
                    file="src/main.py",
                    line=10,
                    column=0,
                    signature="def new_func():",
                )
            ]
        }
        mock_indexer_class.return_value = mock_indexer

        # Create baseline
        baseline_path = tmp_path / ".doc-manager" / "memory" / "symbol-baseline.json"
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        save_symbol_baseline(baseline_path, {})

        # Run map_changes with semantic enabled
        params = MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            include_semantic=True,
        )

        result = asyncio.run(map_changes(params))

        # Result should be dict (not error string)
        assert isinstance(result, dict)
        assert "semantic_changes" in result
        # Should have detected added function
        assert len(result["semantic_changes"]) == 1

    @patch("doc_manager_mcp.tools.changes._get_changed_files_from_checksums")
    @patch("doc_manager_mcp.tools.changes._load_baseline")
    @patch("doc_manager_mcp.tools.changes._map_to_affected_docs")
    def test_map_changes_with_semantic_disabled(
        self, mock_map_docs, mock_load_baseline, mock_get_changed_files, tmp_path
    ):
        """Test that semantic changes are not included when disabled."""
        import asyncio
        from doc_manager_mcp.models import MapChangesInput
        from doc_manager_mcp.tools.changes import map_changes
        from doc_manager_mcp.constants import ChangeDetectionMode

        # Setup mocks
        mock_load_baseline.return_value = {"files": {}, "timestamp": "2024-01-01"}
        mock_get_changed_files.return_value = []
        mock_map_docs.return_value = []

        # Run map_changes with semantic disabled (default)
        params = MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            include_semantic=False,
        )

        result = asyncio.run(map_changes(params))

        # Result should have empty semantic_changes
        assert isinstance(result, dict)
        assert "semantic_changes" in result
        assert result["semantic_changes"] == []

    @patch("doc_manager_mcp.tools.changes.SymbolIndexer")
    def test_semantic_changes_baseline_updates_after_run(
        self, mock_indexer_class, tmp_path
    ):
        """Test that baseline is updated after each run."""
        from doc_manager_mcp.tools.changes import _get_semantic_changes

        baseline_path = tmp_path / ".doc-manager" / "memory" / "symbol-baseline.json"
        baseline_path.parent.mkdir(parents=True, exist_ok=True)

        # First run
        mock_indexer_v1 = MagicMock()
        symbols_v1 = {
            "file.py": [
                Symbol(
                    name="func_v1",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=10,
                    column=0,
                )
            ]
        }
        mock_indexer_v1.index_symbols.return_value = symbols_v1
        mock_indexer_class.return_value = mock_indexer_v1

        _get_semantic_changes(tmp_path)

        # Load baseline and verify it has v1 symbols
        baseline = load_symbol_baseline(baseline_path)
        assert baseline is not None
        assert baseline["file.py"][0].name == "func_v1"

        # Second run with different symbols
        mock_indexer_v2 = MagicMock()
        symbols_v2 = {
            "file.py": [
                Symbol(
                    name="func_v2",
                    type=SymbolType.FUNCTION,
                    file="file.py",
                    line=20,
                    column=0,
                )
            ]
        }
        mock_indexer_v2.index_symbols.return_value = symbols_v2
        mock_indexer_class.return_value = mock_indexer_v2

        _get_semantic_changes(tmp_path)

        # Baseline should now have v2 symbols
        baseline = load_symbol_baseline(baseline_path)
        assert baseline is not None
        assert baseline["file.py"][0].name == "func_v2"


class TestIsPublicApi:
    """Direct unit tests for _is_public_api helper function.

    Tests language-specific naming conventions:
    - Python: underscore prefix = private
    - Go: uppercase first letter = public
    - JavaScript/TypeScript: all public
    """

    def test_python_public_function(self):
        """Test that Python functions without underscore prefix are public."""
        symbol = Symbol(
            name="public_function",
            type=SymbolType.FUNCTION,
            file="src/module.py",
            line=10,
            column=0,
            signature="def public_function():"
        )

        assert _is_public_api(symbol) is True, "Python function without underscore should be public"

    def test_python_private_function(self):
        """Test that Python functions with underscore prefix are private."""
        symbol = Symbol(
            name="_private_function",
            type=SymbolType.FUNCTION,
            file="src/module.py",
            line=20,
            column=0,
            signature="def _private_function():"
        )

        assert _is_public_api(symbol) is False, "Python function with underscore should be private"

    def test_python_dunder_method(self):
        """Test that Python dunder methods are considered private."""
        symbol = Symbol(
            name="__init__",
            type=SymbolType.FUNCTION,
            file="src/module.py",
            line=30,
            column=4,
            signature="def __init__(self):"
        )

        assert _is_public_api(symbol) is False, "Python dunder methods should be private"

    def test_python_public_class(self):
        """Test that Python classes without underscore are public."""
        symbol = Symbol(
            name="PublicClass",
            type=SymbolType.CLASS,
            file="src/module.py",
            line=40,
            column=0,
            signature="class PublicClass:"
        )

        assert _is_public_api(symbol) is True, "Python class without underscore should be public"

    def test_python_private_class(self):
        """Test that Python classes with underscore are private."""
        symbol = Symbol(
            name="_PrivateClass",
            type=SymbolType.CLASS,
            file="src/module.py",
            line=50,
            column=0,
            signature="class _PrivateClass:"
        )

        assert _is_public_api(symbol) is False, "Python class with underscore should be private"

    def test_go_public_function(self):
        """Test that Go functions with uppercase first letter are public."""
        symbol = Symbol(
            name="PublicFunction",
            type=SymbolType.FUNCTION,
            file="src/module.go",
            line=10,
            column=0,
            signature="func PublicFunction() {}"
        )

        assert _is_public_api(symbol) is True, "Go function with uppercase should be public"

    def test_go_private_function(self):
        """Test that Go functions with lowercase first letter are private."""
        symbol = Symbol(
            name="privateFunction",
            type=SymbolType.FUNCTION,
            file="src/module.go",
            line=20,
            column=0,
            signature="func privateFunction() {}"
        )

        assert _is_public_api(symbol) is False, "Go function with lowercase should be private"

    def test_go_public_struct(self):
        """Test that Go structs with uppercase are public."""
        symbol = Symbol(
            name="PublicStruct",
            type=SymbolType.CLASS,
            file="src/module.go",
            line=30,
            column=0,
            signature="type PublicStruct struct {"
        )

        assert _is_public_api(symbol) is True, "Go struct with uppercase should be public"

    def test_go_private_struct(self):
        """Test that Go structs with lowercase are private."""
        symbol = Symbol(
            name="privateStruct",
            type=SymbolType.CLASS,
            file="src/module.go",
            line=40,
            column=0,
            signature="type privateStruct struct {"
        )

        assert _is_public_api(symbol) is False, "Go struct with lowercase should be private"

    def test_typescript_function(self):
        """Test that TypeScript functions are always public."""
        symbol = Symbol(
            name="someFunction",
            type=SymbolType.FUNCTION,
            file="src/module.ts",
            line=10,
            column=0,
            signature="function someFunction() {}"
        )

        assert _is_public_api(symbol) is True, "TypeScript function should be public"

    def test_typescript_class(self):
        """Test that TypeScript classes are always public."""
        symbol = Symbol(
            name="SomeClass",
            type=SymbolType.CLASS,
            file="src/module.ts",
            line=20,
            column=0,
            signature="class SomeClass {"
        )

        assert _is_public_api(symbol) is True, "TypeScript class should be public"

    def test_javascript_function(self):
        """Test that JavaScript functions are always public."""
        symbol = Symbol(
            name="someFunction",
            type=SymbolType.FUNCTION,
            file="src/module.js",
            line=10,
            column=0,
            signature="function someFunction() {}"
        )

        assert _is_public_api(symbol) is True, "JavaScript function should be public"

    def test_jsx_component(self):
        """Test that JSX components are always public."""
        symbol = Symbol(
            name="MyComponent",
            type=SymbolType.FUNCTION,
            file="src/components.jsx",
            line=10,
            column=0,
            signature="function MyComponent() {"
        )

        assert _is_public_api(symbol) is True, "JSX component should be public"

    def test_tsx_component(self):
        """Test that TSX components are always public."""
        symbol = Symbol(
            name="MyComponent",
            type=SymbolType.FUNCTION,
            file="src/components.tsx",
            line=10,
            column=0,
            signature="function MyComponent() {"
        )

        assert _is_public_api(symbol) is True, "TSX component should be public"

    def test_empty_name(self):
        """Test that symbols with empty names are not public."""
        symbol = Symbol(
            name="",
            type=SymbolType.FUNCTION,
            file="src/module.py",
            line=10,
            column=0,
            signature="def ():"
        )

        assert _is_public_api(symbol) is False, "Symbol with empty name should not be public"

    def test_none_name(self):
        """Test that symbols with None names are not public."""
        symbol = Symbol(
            name=None,  # type: ignore[arg-type]
            type=SymbolType.FUNCTION,
            file="src/module.py",
            line=10,
            column=0,
            signature="def None:"
        )

        assert _is_public_api(symbol) is False, "Symbol with None name should not be public"

    def test_unknown_language_defaults_public(self):
        """Test that unknown file extensions default to public."""
        symbol = Symbol(
            name="someFunction",
            type=SymbolType.FUNCTION,
            file="src/module.cpp",
            line=10,
            column=0,
            signature="void someFunction() {}"
        )

        assert _is_public_api(symbol) is True, "Unknown language should default to public"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
