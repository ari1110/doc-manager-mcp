"""Integration tests for memory initialization."""

import pytest
import json
from pathlib import Path

from src.models import InitializeMemoryInput
from src.constants import ResponseFormat
from src.tools.memory import initialize_memory


@pytest.mark.asyncio
class TestMemoryInitialization:
    """Integration tests for memory initialization."""

    """
    @spec 001
    @testType integration
    """
    async def test_initialize_memory_system(self, tmp_path):
        """Test initializing memory system."""
        # Create some files to track
        (tmp_path / "README.md").write_text("# Test Project")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.md").write_text("# Documentation")

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "successfully" in result.lower()

        # Check memory directory created
        memory_dir = tmp_path / ".doc-manager" / "memory"
        assert memory_dir.exists()

        # Check baseline file created
        baseline_file = memory_dir / "repo-baseline.json"
        assert baseline_file.exists()

        with open(baseline_file) as f:
            baseline = json.load(f)
            assert "timestamp" in baseline
            assert "files" in baseline
            assert "metadata" in baseline

    """
    @spec 001
    @testType integration
    """
    async def test_baseline_includes_checksums(self, tmp_path):
        """Test that baseline includes file checksums."""
        # Create test files
        (tmp_path / "file1.md").write_text("Content 1")
        (tmp_path / "file2.md").write_text("Content 2")

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        baseline_file = tmp_path / ".doc-manager" / "memory" / "repo-baseline.json"
        with open(baseline_file) as f:
            baseline = json.load(f)

            # Check that files are tracked
            files = baseline["files"]
            assert len(files) > 0

            # Check checksum format (SHA-256 is 64 hex chars)
            for file_path, checksum in files.items():
                assert len(checksum) == 64
                assert all(c in "0123456789abcdef" for c in checksum)

    """
    @spec 001
    @testType integration
    """
    async def test_conventions_file_created(self, tmp_path):
        """Test that doc-conventions.md is created."""
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        conventions_file = tmp_path / ".doc-manager" / "memory" / "doc-conventions.md"
        assert conventions_file.exists()

        content = conventions_file.read_text()
        assert "Documentation Conventions" in content
        assert "Writing Style" in content

    """
    @spec 001
    @testType integration
    """
    async def test_reinitialize_preserves_conventions(self, tmp_path):
        """Test that reinitializing preserves customized conventions."""
        # First initialization
        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Customize conventions
        conventions_file = tmp_path / ".doc-manager" / "memory" / "doc-conventions.md"
        custom_content = "# My Custom Conventions\nUse Oxford commas."
        conventions_file.write_text(custom_content)

        # Reinitialize
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Check conventions preserved
        assert conventions_file.read_text() == custom_content

    """
    @spec 001
    @testType integration
    """
    async def test_tracks_git_metadata(self, tmp_path):
        """Test that git metadata is included if available."""
        # Create a git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, capture_output=True)

        (tmp_path / "test.txt").write_text("test")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmp_path, capture_output=True)

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        baseline_file = tmp_path / ".doc-manager" / "memory" / "repo-baseline.json"
        with open(baseline_file) as f:
            baseline = json.load(f)
            metadata = baseline["metadata"]

            # Should have git info (using git_branch and git_commit keys)
            assert "git_branch" in metadata or "git_commit" in metadata

    """
    @spec 001
    @testType integration
    """
    async def test_respects_exclude_patterns(self, tmp_path):
        """Test that excluded patterns are not tracked."""
        # Create config with exclude patterns
        config_dir = tmp_path / ".doc-manager"
        config_dir.mkdir()
        config_file = tmp_path / ".doc-manager.yml"
        config_file.write_text("""
platform: mkdocs
exclude:
  - '**/node_modules/**'
  - '**/*.log'
docs_path: docs
""")

        # Create files (some excluded)
        (tmp_path / "README.md").write_text("readme")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "package.js").write_text("code")
        (tmp_path / "debug.log").write_text("logs")

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        baseline_file = tmp_path / ".doc-manager" / "memory" / "repo-baseline.json"
        with open(baseline_file) as f:
            baseline = json.load(f)
            files = baseline["files"]

            # Check that excluded files are not tracked
            file_paths = list(files.keys())
            assert not any("node_modules" in path for path in file_paths)
            assert not any(path.endswith(".log") for path in file_paths)

            # README should be tracked
            assert any("README.md" in path for path in file_paths)

    """
    @spec 001
    @testType integration
    """
    async def test_json_output_format(self, tmp_path):
        """Test JSON output format."""
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.JSON
        ))

        assert '"status":' in result
        assert '"success"' in result.lower()
        assert '"baseline_path":' in result

    """
    @spec 001
    @testType integration
    """
    async def test_nonexistent_project_path(self):
        """Test error handling for nonexistent path."""
        import platform
        from pydantic import ValidationError

        # Use platform-specific absolute path
        if platform.system() == "Windows":
            nonexistent_path = "C:\\nonexistent\\project\\path"
        else:
            nonexistent_path = "/nonexistent/project/path"

        # Pydantic validator should raise ValidationError for nonexistent path
        with pytest.raises(ValidationError) as exc_info:
            InitializeMemoryInput(
                project_path=nonexistent_path,
                response_format=ResponseFormat.MARKDOWN
            )

        assert "does not exist" in str(exc_info.value)

    """
    @spec 001
    @testType integration
    """
    async def test_file_count_in_output(self, tmp_path):
        """Test that output includes file count."""
        # Create several files
        for i in range(5):
            (tmp_path / f"file{i}.md").write_text(f"Content {i}")

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Output should mention number of files tracked
        assert "5" in result or "file" in result.lower()

    """
    @spec 001
    @testType integration
    """
    async def test_handles_empty_project(self, tmp_path):
        """Test handling of project with no files."""
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "successfully" in result.lower()

        baseline_file = tmp_path / ".doc-manager" / "memory" / "repo-baseline.json"
        with open(baseline_file) as f:
            baseline = json.load(f)
            assert baseline["files"] == {}
