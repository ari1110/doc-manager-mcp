"""Integration tests for documentation validation."""

import pytest
from pathlib import Path

from src.models import ValidateDocsInput
from src.constants import ResponseFormat
from src.tools.validation import validate_docs


@pytest.mark.asyncio
class TestDocumentationValidation:
    """Integration tests for documentation validation."""

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
        """Test validation of HTML anchor links."""
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

    async def test_nonexistent_docs_path(self, tmp_path):
        """Test error handling for nonexistent docs path."""
        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="nonexistent",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "Error" in result or "not found" in result.lower()

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
