"""Integration tests for workflow orchestration."""

import pytest
from pathlib import Path

from src.models import BootstrapInput, MigrateInput, SyncInput
from src.constants import ResponseFormat, Platform
from src.tools.workflows import bootstrap, migrate, sync


@pytest.mark.asyncio
class TestBootstrapWorkflow:
    """Integration tests for bootstrap workflow."""

    async def test_bootstrap_mkdocs_project(self, tmp_path):
        """Test bootstrapping a new MkDocs project."""
        # Create minimal project
        (tmp_path / "README.md").write_text("# Test Project")

        result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "bootstrap" in result.lower()
        assert "success" in result.lower()

        # Check that config was created
        assert (tmp_path / ".doc-manager.yml").exists()

        # Check that docs structure was created
        docs_dir = tmp_path / "docs"
        assert docs_dir.exists()
        assert (docs_dir / "index.md").exists()

        # Check memory initialized
        assert (tmp_path / ".doc-manager" / "memory").exists()

    async def test_bootstrap_hugo_project(self, tmp_path):
        """Test bootstrapping a Hugo project."""
        result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.HUGO,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "success" in result.lower()

        docs_dir = tmp_path / "docs"
        assert docs_dir.exists()

        # Hugo-specific structure
        content_dir = docs_dir / "content"
        assert content_dir.exists()

    async def test_bootstrap_docusaurus_project(self, tmp_path):
        """Test bootstrapping a Docusaurus project."""
        result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.DOCUSAURUS,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "success" in result.lower()

        # Docusaurus structure
        docs_dir = tmp_path / "docs"
        assert docs_dir.exists()
        assert (docs_dir / "intro.md").exists()

    async def test_bootstrap_with_custom_docs_path(self, tmp_path):
        """Test bootstrap with custom docs path."""
        result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.SPHINX,
            docs_path="documentation",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "success" in result.lower()

        # Custom path should be created
        docs_dir = tmp_path / "documentation"
        assert docs_dir.exists()

    async def test_bootstrap_includes_quality_assessment(self, tmp_path):
        """Test that bootstrap includes quality assessment."""
        result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should mention quality assessment
        assert "quality" in result.lower() or "assessment" in result.lower()

    async def test_bootstrap_json_output(self, tmp_path):
        """Test bootstrap with JSON output."""
        result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.VITEPRESS,
            response_format=ResponseFormat.JSON
        ))

        assert '"status":' in result
        assert '"platform":' in result
        assert '"steps":' in result


@pytest.mark.asyncio
class TestMigrateWorkflow:
    """Integration tests for migrate workflow."""

    async def test_migrate_to_new_platform(self, tmp_path):
        """Test migrating documentation to new platform."""
        # Create existing docs
        old_docs = tmp_path / "old-docs"
        old_docs.mkdir()
        (old_docs / "index.md").write_text("# Old Documentation")
        (old_docs / "guide.md").write_text("# User Guide")

        result = await migrate(MigrateInput(
            project_path=str(tmp_path),
            source_path="old-docs",
            target_platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "migrat" in result.lower()
        assert "success" in result.lower()

        # Check new docs created
        new_docs = tmp_path / "docs"
        assert new_docs.exists()
        assert (new_docs / "index.md").exists()

    async def test_migrate_with_custom_target_path(self, tmp_path):
        """Test migration with custom target path."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "doc.md").write_text("# Doc")

        result = await migrate(MigrateInput(
            project_path=str(tmp_path),
            source_path="source",
            target_platform=Platform.HUGO,
            target_path="hugo-docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Custom target should exist
        target = tmp_path / "hugo-docs"
        assert target.exists()

    async def test_migrate_preserves_content(self, tmp_path):
        """Test that migration preserves content."""
        source = tmp_path / "source"
        source.mkdir()

        original_content = "# Important Documentation\n\nThis content must be preserved."
        (source / "important.md").write_text(original_content)

        result = await migrate(MigrateInput(
            project_path=str(tmp_path),
            source_path="source",
            target_platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Content should exist in target
        target = tmp_path / "docs"
        migrated_file = target / "important.md"
        assert migrated_file.exists()
        assert "Important Documentation" in migrated_file.read_text()

    async def test_migrate_nested_structure(self, tmp_path):
        """Test migrating nested directory structure."""
        source = tmp_path / "source"
        guides = source / "guides"
        guides.mkdir(parents=True)

        (source / "index.md").write_text("# Index")
        (guides / "tutorial.md").write_text("# Tutorial")

        result = await migrate(MigrateInput(
            project_path=str(tmp_path),
            source_path="source",
            target_platform=Platform.SPHINX,
            response_format=ResponseFormat.MARKDOWN
        ))

        target = tmp_path / "docs"
        assert (target / "index.md").exists()
        assert (target / "guides" / "tutorial.md").exists()

    async def test_migrate_nonexistent_source(self, tmp_path):
        """Test error handling for nonexistent source."""
        result = await migrate(MigrateInput(
            project_path=str(tmp_path),
            source_path="nonexistent",
            target_platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "Error" in result or "not found" in result.lower()


@pytest.mark.asyncio
class TestSyncWorkflow:
    """Integration tests for sync workflow."""

    async def test_sync_detects_changes(self, tmp_path):
        """Test that sync detects code changes."""
        # Initialize project
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "api.py").write_text("def authenticate(): pass")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "api.md").write_text("# API\n\n## authenticate()")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Make changes
        (tmp_path / "src" / "api.py").write_text("def authenticate(token): pass")

        result = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "change" in result.lower()
        assert "api.py" in result

    async def test_sync_recommends_updates(self, tmp_path):
        """Test that sync recommends documentation updates."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "cli.py").write_text("# CLI tool")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "cli.md").write_text("# CLI Documentation")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Add new CLI flag
        (tmp_path / "cli.py").write_text("""
# CLI tool
parser.add_argument('--verbose')
""")

        result = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "update" in result.lower() or "recommend" in result.lower()

    async def test_sync_with_custom_docs_path(self, tmp_path):
        """Test sync with custom docs path."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "file.py").write_text("code")
        custom_docs = tmp_path / "documentation"
        custom_docs.mkdir()
        (custom_docs / "index.md").write_text("# Docs")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        (tmp_path / "file.py").write_text("modified code")

        result = await sync(SyncInput(
            project_path=str(tmp_path),
            docs_path="documentation",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "change" in result.lower()

    async def test_sync_no_changes(self, tmp_path):
        """Test sync when no changes detected."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "file.txt").write_text("content")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        result = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "no changes" in result.lower() or "up to date" in result.lower()

    async def test_sync_json_output(self, tmp_path):
        """Test sync with JSON output."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        result = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.JSON
        ))

        assert '"changes":' in result
        assert '"recommendations":' in result

    async def test_sync_without_baseline(self, tmp_path):
        """Test sync error when baseline doesn't exist."""
        result = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "baseline" in result.lower() or "initialize" in result.lower()

    async def test_sync_includes_priority_levels(self, tmp_path):
        """Test that sync output includes priority levels."""
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        (tmp_path / "important.py").write_text("critical code")

        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        (tmp_path / "important.py").write_text("modified critical code")

        result = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should mention priorities
        assert "priority" in result.lower() or "high" in result.lower() or "medium" in result.lower()
