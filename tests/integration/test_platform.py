"""Integration tests for platform detection tool."""

import pytest
import tempfile
from pathlib import Path

from src.models import DetectPlatformInput
from src.constants import ResponseFormat
from src.tools.platform import detect_platform


@pytest.mark.asyncio
class TestPlatformDetection:
    """Integration tests for platform detection."""

    async def test_detect_hugo_root_config(self, tmp_path):
        """Test detecting Hugo from root config file."""
        (tmp_path / "hugo.toml").write_text('[params]\ntitle = "Test"')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "HUGO" in result
        assert "high confidence" in result
        assert "project root" in result

    async def test_detect_mkdocs_root_config(self, tmp_path):
        """Test detecting MkDocs from root config."""
        (tmp_path / "mkdocs.yml").write_text('site_name: Test')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "MKDOCS" in result
        assert "high confidence" in result

    async def test_detect_docusaurus_root_config(self, tmp_path):
        """Test detecting Docusaurus from root config."""
        (tmp_path / "docusaurus.config.js").write_text('module.exports = {}')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "DOCUSAURUS" in result
        assert "high confidence" in result

    async def test_detect_hugo_in_subdirectory(self, tmp_path):
        """Test detecting Hugo in docsite subdirectory."""
        docsite = tmp_path / "docsite"
        docsite.mkdir()
        (docsite / "hugo.yaml").write_text('title: Test')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "HUGO" in result
        assert "docsite" in result

    async def test_detect_from_package_json(self, tmp_path):
        """Test detecting from package.json dependencies."""
        (tmp_path / "package.json").write_text('''
        {
            "dependencies": {
                "@docusaurus/core": "^2.0.0"
            }
        }
        ''')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "DOCUSAURUS" in result
        assert "medium confidence" in result

    async def test_detect_from_requirements_txt(self, tmp_path):
        """Test detecting from requirements.txt."""
        (tmp_path / "requirements.txt").write_text('mkdocs==1.4.0\nmkdocs-material==9.0.0')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "MKDOCS" in result
        assert "medium confidence" in result

    async def test_recommend_based_on_language(self, tmp_path):
        """Test recommendation based on project language."""
        (tmp_path / "go.mod").write_text('module example.com/test')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "HUGO" in result
        assert "Go" in result

    async def test_json_output_format(self, tmp_path):
        """Test JSON output format."""
        (tmp_path / "mkdocs.yml").write_text('site_name: Test')

        result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.JSON
        ))

        assert '"platform":' in result
        assert '"mkdocs"' in result
        assert '"confidence":' in result
        assert '"high"' in result

    async def test_nonexistent_project_path(self):
        """Test error handling for nonexistent path."""
        result = await detect_platform(DetectPlatformInput(
            project_path="/nonexistent/path",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "Error" in result
        assert "does not exist" in result
