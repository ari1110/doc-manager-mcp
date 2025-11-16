"""Integration tests for dependency tracking."""

import pytest
import json
from pathlib import Path

from src.models import TrackDependenciesInput
from src.constants import ResponseFormat
from src.tools.dependencies import track_dependencies


@pytest.mark.asyncio
class TestDependencyTracking:
    """Integration tests for dependency tracking."""

    async def test_track_file_path_references(self, tmp_path):
        """Test tracking file path references in docs."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "guide.md").write_text("""
# Configuration Guide

Edit the `config.yaml` file in the root directory.
Modify settings in `src/settings.py`.
""")

        # Create referenced files
        (tmp_path / "config.yaml").write_text("key: value")
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "settings.py").write_text("SETTING = True")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "config.yaml" in result
        assert "settings.py" in result
        assert "dependency" in result.lower()
    async def test_track_function_references(self, tmp_path):
        """Test tracking function references in docs."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "api.md").write_text("""
# API Reference

## authenticate()

Call the `authenticate()` function to log in.
Use `validate_token()` to check tokens.
The `get_user_info()` method returns user data.
""")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "authenticate" in result
        assert "validate_token" in result
        assert "get_user_info" in result
    async def test_track_class_references(self, tmp_path):
        """Test tracking class references in docs."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "classes.md").write_text("""
# Classes

## UserManager

The `UserManager` class handles user operations.
Inherits from `BaseManager`.
Uses `DatabaseConnection` for storage.
""")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "UserManager" in result
        assert "BaseManager" in result
        assert "DatabaseConnection" in result
    async def test_track_command_references(self, tmp_path):
        """Test tracking CLI command references."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "cli.md").write_text("""
# CLI Usage

Run `docmgr init` to initialize.
Use `docmgr validate --strict` for validation.
Execute `docmgr sync --auto` for synchronization.
""")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "docmgr init" in result or "init" in result
        assert "validate" in result
        assert "sync" in result
    async def test_track_config_key_references(self, tmp_path):
        """Test tracking configuration key references."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "config.md").write_text("""
# Configuration

Set `platform: hugo` in your config.
Configure `docs_path: "docs"` as needed.
Use `exclude` patterns to ignore files.
""")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "platform" in result
        assert "docs_path" in result
        assert "exclude" in result
    async def test_bidirectional_graph_creation(self, tmp_path):
        """Test that bidirectional dependency graph is created."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "api.md").write_text("Use `main_function()` from `app.py`")
        (docs_dir / "guide.md").write_text("The `main_function()` is the entry point")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Check that dependencies file was created
        deps_file = tmp_path / ".doc-manager" / "dependencies.json"
        assert deps_file.exists()

        with open(deps_file) as f:
            deps = json.load(f)
            assert "doc_to_code" in deps
            assert "code_to_doc" in deps

    async def test_multiple_docs_referencing_same_code(self, tmp_path):
        """Test multiple docs referencing the same code element."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "quickstart.md").write_text("Use `init()` to start")
        (docs_dir / "tutorial.md").write_text("First call `init()` function")
        (docs_dir / "reference.md").write_text("## init()\n\nInitializes the system")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        deps_file = tmp_path / ".doc-manager" / "dependencies.json"
        with open(deps_file) as f:
            deps = json.load(f)
            code_to_doc = deps["code_to_doc"]

            # init() should map to multiple docs
            init_refs = [ref for ref in code_to_doc if "init" in ref.lower()]
            assert len(init_refs) > 0

    async def test_track_across_nested_directories(self, tmp_path):
        """Test tracking dependencies across nested directory structure."""
        docs_dir = tmp_path / "docs"
        guides_dir = docs_dir / "guides"
        ref_dir = docs_dir / "reference"

        guides_dir.mkdir(parents=True)
        ref_dir.mkdir(parents=True)

        (guides_dir / "setup.md").write_text("Edit `setup.cfg` file")
        (ref_dir / "api.md").write_text("Call `setup()` function")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "setup" in result.lower()

    async def test_json_output_format(self, tmp_path):
        """Test JSON output format."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("Reference to `test_function()`")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.JSON
        ))

        assert '"doc_to_code":' in result
        assert '"code_to_doc":' in result
        assert '"total_references":' in result

    async def test_empty_docs_directory(self, tmp_path):
        """Test tracking with empty docs directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "0 references" in result or "no references" in result.lower()

    async def test_nonexistent_docs_path(self, tmp_path):
        """Test error handling for nonexistent docs path."""
        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="nonexistent",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "Error" in result or "not found" in result.lower()

    async def test_complex_code_references(self, tmp_path):
        """Test tracking complex code references."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "advanced.md").write_text("""
# Advanced Usage

Import from `src/models/user.py`:
```python
from src.models.user import User, UserRole
```

Configure in `config/production.yaml`.
Run `app --mode=production --verbose`.
Call `User.authenticate(username, password)`.
""")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should detect multiple reference types
        assert "user.py" in result or "User" in result
        assert "production.yaml" in result or "config" in result
    async def test_save_dependencies_file(self, tmp_path):
        """Test that dependencies are saved to file."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("Use `function()` from `file.py`")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        deps_file = tmp_path / ".doc-manager" / "dependencies.json"
        assert deps_file.exists()

        with open(deps_file) as f:
            deps = json.load(f)
            assert "generated_at" in deps
            assert "doc_to_code" in deps
            assert "code_to_doc" in deps

    async def test_large_dependency_graph_triggers_truncation(self, tmp_path):
        """Test that large dependency graphs are properly truncated (T056 - US4).

        This test creates many documentation files with many references to generate
        a dependency graph large enough to trigger the 25K character response limit.
        """
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create many documentation files, each with many references
        # This should generate a response > 25K characters
        for doc_num in range(150):
            content_lines = [f"# Documentation File {doc_num}\n\n"]

            # Add many code references to create large dependency graph
            for ref_num in range(40):
                content_lines.append(f"- Function `function_{ref_num}()` in `module{ref_num}.py`\n")
                content_lines.append(f"- Class `Class{ref_num}` implementation details\n")
                content_lines.append(f"- See `utils/helper{ref_num}.py` for utilities\n")

            (docs_dir / f"doc{doc_num}.md").write_text("".join(content_lines))

        # Track dependencies - should generate very large output
        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Verify response is truncated to limit
        assert len(result) <= 25000, (
            f"Response should be truncated to 25K, got {len(result)} chars"
        )

        # Verify truncation message is present
        assert "truncated" in result.lower()
        assert "25,000 character limit" in result

        # Verify helpful tip is included
        assert "Tip:" in result or "reduce output" in result.lower()

    async def test_json_dependency_graph_also_truncated(self, tmp_path):
        """Test that JSON responses are also truncated for large graphs (T056 - US4)."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create many files with references
        for i in range(120):
            content = f"# Doc {i}\n\n"
            for j in range(35):
                content += f"Reference `file{j}.py`, `class{j}`, `function{j}()`\n"
            (docs_dir / f"doc{i}.md").write_text(content)

        # Request JSON format
        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.JSON
        ))

        # JSON responses should also be limited
        assert len(result) <= 25000, f"JSON response should be truncated, got {len(result)} chars"

        # Should still be valid JSON (or truncation message)
        assert result.startswith("{") or "truncated" in result.lower()


@pytest.mark.asyncio
class TestPreciseDependencyMatching:

    async def test_no_substring_false_positives(self, tmp_path):
        """Test that substring matching false positives are eliminated (T091 - FR-026).

        Verifies that:
        - "save.py" matches only "save.py", NOT "autosave.py"
        - "add" command matches only "cmd/add.go", NOT "cmd/add_user.go"

        This test proves the implementation uses path separators to prevent
        false positives that would occur with naive substring matching.
        """
        # Setup: create source files that would trigger false positives with substring matching
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "save.py").write_text("def save(): pass")
        (src_dir / "autosave.py").write_text("def autosave(): pass")

        cmd_dir = tmp_path / "cmd"
        cmd_dir.mkdir()
        (cmd_dir / "add.go").write_text("package main\nfunc add() {}")
        (cmd_dir / "add_user.go").write_text("package main\nfunc addUser() {}")

        # Create docs mentioning save.py (should NOT match autosave.py)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text("See `save.py` for details")

        # Track dependencies
        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.JSON
        ))

        result_data = json.loads(result)

        # Verify save.py matched, autosave.py did NOT match
        all_matched_files = []
        for doc_file, source_files in result_data.get("doc_to_code", {}).items():
            all_matched_files.extend(source_files)

        # save.py should be matched
        assert any("save.py" in f and "autosave.py" not in f for f in all_matched_files), \
            f"save.py should be matched. Got: {all_matched_files}"

        # autosave.py should NOT be matched (this is the critical assertion)
        assert not any("autosave.py" in f for f in all_matched_files), \
            f"autosave.py should NOT be matched (substring false positive). Got: {all_matched_files}"

        # Create docs mentioning "add" command (should NOT match add_user)
        (docs_dir / "cli.md").write_text("Run the `add` command to add items")

        # Track dependencies again
        result2 = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.JSON
        ))

        result_data2 = json.loads(result2)

        # Collect all matched files
        all_matched_files2 = []
        for doc_file, source_files in result_data2.get("doc_to_code", {}).items():
            all_matched_files2.extend(source_files)

        # cmd/add.go should be matched
        assert any("cmd/add.go" in f for f in all_matched_files2), \
            f"cmd/add.go should be matched. Got: {all_matched_files2}"

        # cmd/add_user.go should NOT be matched (this proves no substring false positive)
        assert not any("cmd/add_user.go" in f for f in all_matched_files2), \
            f"cmd/add_user.go should NOT be matched (substring false positive). Got: {all_matched_files2}"
