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

        (tmp_path / "critical.py").write_text("def important_api(): pass")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        (tmp_path / "critical.py").write_text("def important_api(new_param): pass")

        result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should mention priority
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

        assert '"changes":' in result
        assert '"category":' in result
        assert '"priority":' in result

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
