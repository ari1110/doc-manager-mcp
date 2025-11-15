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


@pytest.mark.asyncio
class TestValidationLineNumbers:
    """Integration tests for accurate line numbers in validation reports.

    @spec 001
    @functionalReq FR-029
    @testType integration
    """

    async def test_accurate_line_numbers_in_reports(self, tmp_path):
        """Test that validation reports show accurate line numbers (1-based indexing).

        This test creates markdown files with errors at specific line numbers
        and verifies that the validation report correctly identifies those lines.

        @spec 001
        @functionalReq FR-029
        @testType integration
        """
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create test file with broken link at line 5
        # Each line is explicitly counted to prove accuracy
        doc_content = (
            "# Test Doc\n"              # line 1
            "\n"                          # line 2
            "Some content here.\n"       # line 3
            "\n"                          # line 4
            "[broken](./missing.md)\n"   # line 5 - BROKEN LINK HERE
            "\n"                          # line 6
            "More content.\n"            # line 7
        )
        (docs_dir / "test.md").write_text(doc_content)

        # Create second file with error at line 10
        doc2_content = (
            "# Another Test\n"           # line 1
            "\n"                          # line 2
            "Line 3\n"                   # line 3
            "Line 4\n"                   # line 4
            "Line 5\n"                   # line 5
            "Line 6\n"                   # line 6
            "Line 7\n"                   # line 7
            "Line 8\n"                   # line 8
            "\n"                          # line 9
            "![missing](./img.png)\n"    # line 10 - MISSING IMAGE HERE
            "\n"                          # line 11
        )
        (docs_dir / "test2.md").write_text(doc2_content)

        # Create third file with missing alt text at line 3
        doc3_content = (
            "# Alt Text Test\n"          # line 1
            "\n"                          # line 2
            "![](./valid.png)\n"         # line 3 - MISSING ALT TEXT
        )
        (docs_dir / "test3.md").write_text(doc3_content)

        # Create the valid image referenced
        (docs_dir / "valid.png").write_bytes(b"fake image")

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        result_lower = result.lower()

        # Verify line 5 appears in report for broken link
        # Check multiple formats: "line 5", "5:", ":5", etc.
        assert ("line 5" in result_lower or
                ":5:" in result or
                " 5:" in result or
                "test.md:5" in result.lower()), \
            f"Expected line 5 for broken link in test.md, got:\n{result}"

        # Verify line 10 appears in report for missing image
        assert ("line 10" in result_lower or
                ":10:" in result or
                " 10:" in result or
                "test2.md:10" in result.lower()), \
            f"Expected line 10 for missing image in test2.md, got:\n{result}"

        # Verify line 3 appears in report for missing alt text
        assert ("line 3" in result_lower or
                ":3:" in result or
                " 3:" in result or
                "test3.md:3" in result.lower()), \
            f"Expected line 3 for missing alt text in test3.md, got:\n{result}"

        # Critical: Verify NO line 0 appears (off-by-one error check)
        assert "line 0" not in result_lower, \
            f"Found 'line 0' in report (off-by-one error):\n{result}"
        assert ":0:" not in result, \
            f"Found ':0:' in report (off-by-one error):\n{result}"

        # Verify we don't have off-by-one errors (line 4 instead of 5, etc.)
        # The broken link is NOT on line 4 or 6
        if "test.md" in result:
            # Extract the line number for test.md's broken link
            test_md_section = result[result.find("test.md"):result.find("test.md") + 200]
            assert "line 4" not in test_md_section or "line 5" in test_md_section, \
                f"Broken link reported on wrong line (should be 5, not 4):\n{test_md_section}"
            assert "line 6" not in test_md_section or "line 5" in test_md_section, \
                f"Broken link reported on wrong line (should be 5, not 6):\n{test_md_section}"
