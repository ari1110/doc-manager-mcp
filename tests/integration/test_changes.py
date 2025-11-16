"""Integration tests for change mapping."""

import pytest
import json
from pathlib import Path

from src.models import MapChangesInput
from src.constants import ResponseFormat, ChangeDetectionMode
from src.tools.changes import map_changes


@pytest.mark.asyncio
class TestChangeMapping:
    """Integration tests for change mapping."""

    async def test_map_changes_checksum_mode(self, tmp_path):
        """Test mapping changes using checksum comparison."""
        # Initialize memory system
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "README.md").write_text("# Original")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("# Guide")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Modify files
        (tmp_path / "README.md").write_text("# Modified README")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "new.py").write_text("def new_function(): pass")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "change" in result.lower()
        assert "README.md" in result

    async def test_categorize_cli_changes(self, tmp_path):
        """Test categorizing CLI-related changes."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "cli.py").write_text("def main(): pass")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Modify CLI
        (tmp_path / "cli.py").write_text("""
def main():
    parser.add_argument('--new-flag')
    pass
""")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "cli" in result.lower()
    async def test_categorize_api_changes(self, tmp_path):
        """Test categorizing API-related changes."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        api_dir = tmp_path / "src" / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "endpoints.py").write_text("def get_users(): pass")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Add new API endpoint
        (api_dir / "endpoints.py").write_text("""
def get_users(): pass
def create_user(): pass
""")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "api" in result.lower()
    async def test_categorize_config_changes(self, tmp_path):
        """Test categorizing configuration changes."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "config.yaml").write_text("setting: value")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Modify config
        (tmp_path / "config.yaml").write_text("setting: new_value\nnew_setting: true")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "config" in result.lower()

    async def test_map_with_docs_mapping(self, tmp_path):
        """Test mapping changes to affected documentation."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        # Create source and docs
        (tmp_path / "api.py").write_text("def authenticate(): pass")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "api-reference.md").write_text("""
# API Reference

## authenticate()

Function for authentication.
""")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Modify API
        (tmp_path / "api.py").write_text("""
def authenticate(username, password):
    # New signature
    pass
""")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "api.py" in result
        assert "docs" in result.lower() or "documentation" in result.lower()
    async def test_priority_levels(self, tmp_path):
        """Test that changes are assigned priority levels."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        # Create an API file that will trigger doc mapping
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "api.py").write_text("def important_api(): pass")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        (tmp_path / "src" / "api.py").write_text("def important_api(new_param): pass")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should mention priority (since src/ changes trigger API doc mapping)
        assert "priority" in result.lower() or "high" in result.lower() or "medium" in result.lower()

    async def test_json_output_format(self, tmp_path):
        """Test JSON output format."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "file.py").write_text("original")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        (tmp_path / "file.py").write_text("modified")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.JSON
        ))

        assert '"changed_files":' in result
        assert '"change_type":' in result
        assert '"affected_documentation":' in result

    async def test_no_changes_detected(self, tmp_path):
        """Test when no changes are detected."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "file.txt").write_text("content")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "no changes" in result.lower() or "0 changes" in result

    async def test_new_files_detected(self, tmp_path):
        """Test detecting newly added files."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Add new file
        (tmp_path / "new_feature.py").write_text("def new_feature(): pass")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "new" in result.lower() or "added" in result.lower()
        assert "new_feature.py" in result

    async def test_multiple_change_categories(self, tmp_path):
        """Test detecting multiple categories of changes."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "cli.py").write_text("cli code")
        (tmp_path / "config.json").write_text('{"key": "value"}')
        (tmp_path / "api.py").write_text("api code")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Modify all
        (tmp_path / "cli.py").write_text("modified cli")
        (tmp_path / "config.json").write_text('{"key": "new_value"}')
        (tmp_path / "api.py").write_text("modified api")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should detect multiple categories
        categories_found = sum([
            "cli" in result.lower(),
            "config" in result.lower(),
            "api" in result.lower()
        ])
        assert categories_found >= 2

    async def test_command_injection_via_commit_hash_rejected(self, tmp_path):
        """Test that shell metacharacters in commit hash are rejected (T022 - US2).

        This integration test verifies that command injection attempts
        are blocked by Pydantic validation before reaching git commands.
        """
        from pydantic import ValidationError

        # Malicious commit hash attempts
        malicious_hashes = [
            "HEAD; rm -rf /",           # Command separator
            "abc123 && echo pwned",     # Command chaining
            "abc123 | cat /etc/passwd", # Pipe to command
            "$(whoami)",                # Command substitution
            "`whoami`",                 # Backtick substitution
            "abc123 > /tmp/exploit",    # Redirection
            "abc123\nrm -rf /",         # Newline injection
            "'; DROP TABLE users; --", # SQL-style injection attempt
        ]

        for malicious_hash in malicious_hashes:
            with pytest.raises(ValidationError) as exc_info:
                MapChangesInput(
                    project_path=str(tmp_path),
                    since_commit=malicious_hash,
                    mode=ChangeDetectionMode.GIT_DIFF,
                    response_format=ResponseFormat.MARKDOWN
                )

            # Verify error message mentions invalid format
            error = exc_info.value
            assert "Invalid git commit hash format" in str(error), \
                f"Expected validation error for: {malicious_hash}"

            # Verify security reason is mentioned
            assert "command injection" in str(error).lower(), \
                f"Error should mention command injection for: {malicious_hash}"

    async def test_valid_commit_hash_accepted_in_git_mode(self, tmp_path, monkeypatch):
        """Test that valid commit hashes are accepted in git diff mode (T022 - US2).

        This verifies that legitimate commit hashes pass validation
        and reach the git command layer safely.
        """
        # Mock git command to avoid needing real git repo
        def mock_run_git_command(cwd, *args, check_git_available=True):
            # Verify arguments are in safe array form
            assert args[0] == "diff"
            assert args[1] == "--name-status"
            # args[2] is the commit hash
            assert args[3] == "HEAD"
            return ""  # Empty diff

        monkeypatch.setattr("src.tools.changes.run_git_command", mock_run_git_command)

        # Valid commit hashes
        valid_hashes = [
            "abc1234",           # Short hash (7 chars)
            "abcdef0123456789",  # Medium hash (16 chars)
            "a" * 40,            # Full SHA-1 (40 chars)
            "ABCDEF0",           # Uppercase allowed
            "1234567",           # All digits allowed
        ]

        for valid_hash in valid_hashes:
            # Should not raise ValidationError
            result = await map_changes(MapChangesInput(
                project_path=str(tmp_path),
                since_commit=valid_hash,
                mode=ChangeDetectionMode.GIT_DIFF,
                response_format=ResponseFormat.MARKDOWN
            ))

            # Should execute successfully
            assert isinstance(result, str)
            assert "Error" not in result or "no changes" in result.lower()

    async def test_missing_git_binary_failure_mode(self, tmp_path, monkeypatch):
        """Test clear error when git binary is missing (T023 - US2).

        Verifies that missing git binary produces a helpful error message
        rather than cryptic failures.
        """
        # Mock shutil.which to simulate git not found
        monkeypatch.setattr("shutil.which", lambda x: None if x == "git" else "/usr/bin/" + x)

        # Attempt to use git diff mode without git installed
        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            since_commit="abc1234",
            mode=ChangeDetectionMode.GIT_DIFF,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should contain clear error message
        assert "Error" in result or "error" in result.lower()
        assert "git" in result.lower()

        # Should mention git is required or not found
        assert any(phrase in result.lower() for phrase in [
            "git is required",
            "git not found",
            "git binary",
            "install git"
        ]), f"Error message should clearly indicate git is missing: {result}"
