
import pytest
from pathlib import Path

from src.models import (
    InitializeConfigInput,
    InitializeMemoryInput,
    DetectPlatformInput,
    AssessQualityInput,
    ValidateDocsInput,
    MapChangesInput,
    TrackDependenciesInput,
    BootstrapInput,
    MigrateInput,
    SyncInput
)
from src.constants import ResponseFormat, DocumentationPlatform, ChangeDetectionMode


class TestOptionalFieldHandling:
    """Test that all models handle None values gracefully for optional fields (T045 - US5)."""

    def test_initialize_config_with_all_none_optionals(self, tmp_path):
        """Test InitializeConfigInput with all optional fields as None."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # All optional fields explicitly None
        model = InitializeConfigInput(
            project_path=str(project_dir),
            platform=None,
            exclude_patterns=None,
            docs_path=None,
            sources=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.project_path == str(project_dir.resolve())
        assert model.platform is None
        assert model.exclude_patterns is None
        assert model.docs_path is None
        assert model.sources is None
        assert model.response_format == ResponseFormat.MARKDOWN

    def test_initialize_config_with_empty_lists(self, tmp_path):
        """Test InitializeConfigInput with empty lists for pattern fields."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Empty lists should be accepted
        model = InitializeConfigInput(
            project_path=str(project_dir),
            exclude_patterns=[],
            sources=[],
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.exclude_patterns == []
        assert model.sources == []

    def test_assess_quality_with_none_optionals(self, tmp_path):
        """Test AssessQualityInput with None for optional fields."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = AssessQualityInput(
            project_path=str(project_dir),
            docs_path=None,
            criteria=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.docs_path is None
        assert model.criteria is None

    def test_validate_docs_with_none_optionals(self, tmp_path):
        """Test ValidateDocsInput with None docs_path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = ValidateDocsInput(
            project_path=str(project_dir),
            docs_path=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.docs_path is None
        assert model.check_links is True  # Default value
        assert model.check_assets is True
        assert model.check_snippets is True

    def test_map_changes_with_none_optionals(self, tmp_path):
        """Test MapChangesInput with None since_commit."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = MapChangesInput(
            project_path=str(project_dir),
            since_commit=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.since_commit is None
        assert model.mode == ChangeDetectionMode.CHECKSUM  # Default

    def test_track_dependencies_with_none_optionals(self, tmp_path):
        """Test TrackDependenciesInput with None docs_path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = TrackDependenciesInput(
            project_path=str(project_dir),
            docs_path=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.docs_path is None

    def test_bootstrap_with_none_platform(self, tmp_path):
        """Test BootstrapInput with None platform (auto-detect)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = BootstrapInput(
            project_path=str(project_dir),
            platform=None,
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.platform is None
        assert model.docs_path == "docs"

    def test_migrate_with_none_platform(self, tmp_path):
        """Test MigrateInput with None target_platform."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = MigrateInput(
            project_path=str(project_dir),
            source_path="old-docs",
            target_platform=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.target_platform is None
        assert model.preserve_history is True  # Default

    def test_sync_with_none_docs_path(self, tmp_path):
        """Test SyncInput with None docs_path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = SyncInput(
            project_path=str(project_dir),
            docs_path=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.docs_path is None
        assert model.mode == "reactive"  # Default


class TestOptionalFieldDefaults:
    """Test that optional fields use correct default values (T045 - US5)."""

    def test_initialize_config_default_exclude_patterns(self, tmp_path):
        """Test that InitializeConfigInput uses sensible default exclude patterns."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Don't specify exclude_patterns - should use default
        model = InitializeConfigInput(
            project_path=str(project_dir),
            response_format=ResponseFormat.MARKDOWN
        )

        # Should have default exclude patterns
        assert model.exclude_patterns is not None
        assert "**/node_modules" in model.exclude_patterns
        assert "**/dist" in model.exclude_patterns
        assert "**/.git" in model.exclude_patterns

    def test_validate_docs_boolean_defaults(self, tmp_path):
        """Test that ValidateDocsInput boolean fields default to True."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = ValidateDocsInput(
            project_path=str(project_dir),
            response_format=ResponseFormat.MARKDOWN
        )

        # All checks should default to True
        assert model.check_links is True
        assert model.check_assets is True
        assert model.check_snippets is True

    def test_map_changes_mode_default(self, tmp_path):
        """Test that MapChangesInput defaults to checksum mode."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = MapChangesInput(
            project_path=str(project_dir),
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.mode == ChangeDetectionMode.CHECKSUM

    def test_sync_mode_default(self, tmp_path):
        """Test that SyncInput defaults to reactive mode."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = SyncInput(
            project_path=str(project_dir),
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.mode == "reactive"

    def test_migrate_preserve_history_default(self, tmp_path):
        """Test that MigrateInput defaults to preserving history."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = MigrateInput(
            project_path=str(project_dir),
            source_path="old-docs",
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.preserve_history is True
