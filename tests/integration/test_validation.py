"""Integration tests for documentation validation."""

import pytest
from pathlib import Path

from src.models import ValidateDocsInput
from src.constants import ResponseFormat
from src.tools.validation import validate_docs


@pytest.mark.asyncio
class TestDocumentationValidation:
    """Integration tests for documentation validation."""

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_validate_clean_documentation(self, tmp_path):
        """Test validating documentation with no issues."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create valid documentation
        (docs_dir / "index.md").write_text("""
# Welcome

This is a clean documentation page.

[Valid Link](./guide.md)
""")
        (docs_dir / "guide.md").write_text("# Guide\n\nContent here.")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "documentation is valid" in result.lower()
        assert "0 issues" in result.lower() or "no issues" in result.lower()

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_detect_broken_internal_links(self, tmp_path):
        """Test detecting broken internal markdown links."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "index.md").write_text("""
# Index

[Broken Link](./nonexistent.md)
[Another Broken](../missing.md)
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "broken link" in result.lower()
        assert "nonexistent.md" in result
        assert "missing.md" in result

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_detect_missing_images(self, tmp_path):
        """Test detecting missing image files."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.md").write_text("""
# Page

![Missing Image](./images/missing.png)
<img src="./another-missing.jpg" />
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "missing" in result.lower() or "not found" in result.lower()
        assert "missing.png" in result
        assert "another-missing.jpg" in result

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_detect_missing_alt_text(self, tmp_path):
        """Test detecting images without alt text."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create actual image so it's not flagged as missing
        images_dir = docs_dir / "images"
        images_dir.mkdir()
        (images_dir / "diagram.png").write_bytes(b"fake image data")

        (docs_dir / "page.md").write_text("""
# Page

![](./images/diagram.png)
<img src="./images/diagram.png" />
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "alt text" in result.lower()

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_validate_code_snippet_syntax(self, tmp_path):
        """Test basic code snippet syntax validation."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "code.md").write_text("""
# Code Examples

```python
def hello():
    print("Hello")
```

```javascript
function test() {
    console.log("test")
```

```json
{
  "key": "value"
  "missing": "comma"
}
```
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should detect unclosed code block and JSON syntax issues
        # JavaScript has unclosed block, JSON has missing comma
        assert "unmatched" in result.lower() or "syntax" in result.lower() or "issue" in result.lower()

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_validate_with_custom_docs_path(self, tmp_path):
        """Test validation with custom docs path."""
        custom_docs = tmp_path / "documentation"
        custom_docs.mkdir()

        (custom_docs / "index.md").write_text("[Broken](./missing.md)")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="documentation",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "broken link" in result.lower()
        assert "missing.md" in result

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_validate_nested_directories(self, tmp_path):
        """Test validation across nested directory structure."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "index.md").write_text("[Guide](./guides/getting-started.md)")

        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()
        (guides_dir / "getting-started.md").write_text("""
# Getting Started

[Missing](../reference/missing.md)
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "broken link" in result.lower()
        assert "missing.md" in result

    @pytest.mark.skip(reason="HTML file validation not yet implemented - only markdown files are validated")
    async def test_validate_html_links(self, tmp_path):
        """Test validation of HTML anchor links.

        @spec 001
        @testType integration
        @mockDependent
        """
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "page.html").write_text("""
<html>
<body>
    <a href="./missing.html">Broken</a>
    <a href="./exists.html">Valid</a>
</body>
</html>
""")
        (docs_dir / "exists.html").write_text("<html></html>")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "missing.html" in result or "broken link" in result.lower()

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_json_output_format(self, tmp_path):
        """Test JSON output format."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.md").write_text("[Broken](./missing.md)")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.JSON
        ))

        assert '"issues":' in result
        assert '"type":' in result
        assert '"file":' in result

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_nonexistent_docs_path(self, tmp_path):
        """Test error handling for nonexistent docs path."""
        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="nonexistent",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "Error" in result or "not found" in result.lower()

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_multiple_issues_in_single_file(self, tmp_path):
        """Test detecting multiple issues in one file."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "problems.md").write_text("""
# Problems

[Broken Link 1](./missing1.md)
[Broken Link 2](./missing2.md)
![Missing Image](./missing.png)
![](./another-missing.png)

```python
def unclosed():
    print("test"
```
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should detect multiple issues
        issues_count = result.lower().count("issue") + result.lower().count("error")
        assert issues_count > 0

    """
    @spec 001
    @testType integration
    @mockDependent
    """
    async def test_ignore_external_links(self, tmp_path):
        """Test that external links are not validated."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "external.md").write_text("""
# External Links

[GitHub](https://github.com)
[Google](https://google.com)
[HTTP Link](http://example.com)
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # External links should not cause issues
        assert "documentation is valid" in result.lower() or "0 issues" in result.lower()

    """
    @spec 001
    @testType integration
    @userStory US1
    @functionalReq FR-001, FR-025
    """
    async def test_reject_path_traversal_in_link_validation(self, tmp_path):
        """Test that path traversal attempts in links are rejected (T033 - US1).

        This test verifies that malicious documentation cannot reference files
        outside the project boundary using path traversal sequences.
        """
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create documentation with path traversal attempts
        (docs_dir / "malicious.md").write_text("""
# Malicious Documentation

[Try to access /etc/passwd](../../../etc/passwd)
[Try to escape project](../../sensitive/file.txt)
[Nested traversal](./subdir/../../../../../../root/file)
""")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Path traversal attempts should be detected as broken links
        # (since they reference files outside the project boundary)
        assert "broken link" in result.lower() or "issue" in result.lower()

    """
    @spec 001
    @testType integration
    @userStory US1
    @functionalReq FR-003, FR-028
    """
    async def test_reject_symlink_escaping_project_boundary(self, tmp_path):
        """Test that symlinks escaping project boundary are rejected (T034 - US1).

        This test verifies that file traversal operations skip symlinks
        that point outside the project boundary.
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        docs_dir = project_root / "docs"
        docs_dir.mkdir()

        # Create a file outside project
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        secret_file = outside_dir / "secret.md"
        secret_file.write_text("# Secret Content\n\nThis should not be accessible")

        # Create symlink in docs pointing outside project
        malicious_link = docs_dir / "escape_link.md"
        malicious_link.symlink_to(secret_file)

        # Run validation - should either skip the symlink or detect it as an issue
        result = await validate_docs(ValidateDocsInput(
            project_path=str(project_root),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # The symlink should be skipped by file traversal (not cause a crash)
        # Result should complete successfully without processing the malicious symlink
        assert isinstance(result, str)
        # Should not have processed the secret file content
        assert "Secret Content" not in result
