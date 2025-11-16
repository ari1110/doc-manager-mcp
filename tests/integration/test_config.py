"""Integration tests for configuration initialization."""

import pytest
from pathlib import Path
import yaml

from src.models import InitializeConfigInput
from src.constants import ResponseFormat, Platform
from src.tools.config import initialize_config


@pytest.mark.asyncio
class TestConfigInitialization:
    """Integration tests for config initialization."""

    async def test_initialize_basic_config(self, tmp_path):
        """Test initializing basic configuration."""
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "successfully" in result.lower()

        config_file = tmp_path / ".doc-manager.yml"
        assert config_file.exists()

        with open(config_file) as f:
            config = yaml.safe_load(f)
            assert config["platform"] == "mkdocs"
            assert "exclude" in config
            assert "metadata" in config

    async def test_initialize_with_custom_docs_path(self, tmp_path):
        """Test initializing with custom docs path."""
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.HUGO,
            docs_path="documentation",
            response_format=ResponseFormat.MARKDOWN
        ))

        config_file = tmp_path / ".doc-manager.yml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
            assert config["docs_path"] == "documentation"
            assert config["platform"] == "hugo"

    async def test_initialize_with_sources(self, tmp_path):
        """Test initializing with source patterns."""
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.SPHINX,
            sources=["src/**/*.py", "lib/**/*.py"],
            response_format=ResponseFormat.MARKDOWN
        ))

        config_file = tmp_path / ".doc-manager.yml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
            assert len(config["sources"]) == 2
            assert "src/**/*.py" in config["sources"]

    async def test_overwrite_existing_config(self, tmp_path):
        """Test overwriting existing configuration."""
        # Create initial config
        config_file = tmp_path / ".doc-manager.yml"
        config_file.write_text("platform: mkdocs\nexclude: []\n")

        # Overwrite
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.DOCUSAURUS,
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "successfully" in result.lower()

        with open(config_file) as f:
            config = yaml.safe_load(f)
            assert config["platform"] == "docusaurus"

    async def test_json_output_format(self, tmp_path):
        """Test JSON output format."""
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.VITEPRESS,
            response_format=ResponseFormat.JSON
        ))

        assert '"status":' in result
        assert '"success"' in result.lower()
        assert '"config_path":' in result

    async def test_all_platforms(self, tmp_path):
        """Test config initialization for all platforms."""
        platforms = [
            Platform.HUGO, Platform.DOCUSAURUS, Platform.MKDOCS,
            Platform.SPHINX, Platform.VITEPRESS, Platform.JEKYLL, Platform.GITBOOK
        ]

        for platform in platforms:
            # Create subdirectory for each platform
            platform_dir = tmp_path / platform.value
            platform_dir.mkdir()

            result = await initialize_config(InitializeConfigInput(
                project_path=str(platform_dir),
                platform=platform,
                response_format=ResponseFormat.MARKDOWN
            ))

            assert "successfully" in result.lower()
            config_file = platform_dir / ".doc-manager.yml"
            assert config_file.exists()

    async def test_config_with_detected_language(self, tmp_path):
        """Test that config includes detected language."""
        # Create a Python project indicator
        (tmp_path / "requirements.txt").write_text("pytest==7.0.0")

        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.SPHINX,
            response_format=ResponseFormat.MARKDOWN
        ))

        config_file = tmp_path / ".doc-manager.yml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
            assert config["metadata"]["language"] == "Python"

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
            InitializeConfigInput(
                project_path=nonexistent_path,
                platform=Platform.MKDOCS,
                response_format=ResponseFormat.MARKDOWN
            )

        assert "does not exist" in str(exc_info.value)

    async def test_default_exclude_patterns(self, tmp_path):
        """Test that default exclude patterns are included."""
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        config_file = tmp_path / ".doc-manager.yml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
            exclude = config["exclude"]
            assert any("node_modules" in pattern for pattern in exclude)
            assert any("dist" in pattern or "build" in pattern for pattern in exclude)
            assert any(".git" in pattern for pattern in exclude)

    async def test_metadata_includes_timestamp(self, tmp_path):
        """Test that metadata includes creation timestamp."""
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.HUGO,
            response_format=ResponseFormat.MARKDOWN
        ))

        config_file = tmp_path / ".doc-manager.yml"
        with open(config_file) as f:
            config = yaml.safe_load(f)
            assert "created" in config["metadata"]
            assert "version" in config["metadata"]
