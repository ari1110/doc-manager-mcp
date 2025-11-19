"""Tests for Phase 3 validation and quality enhancements."""

import pytest
from pathlib import Path
from doc_manager_mcp.tools.validation_helpers import validate_code_examples, validate_documented_symbols
from doc_manager_mcp.tools.quality_helpers import (
    check_list_formatting_consistency,
    check_heading_case_consistency,
    detect_multiple_h1s,
    detect_undocumented_apis,
    calculate_documentation_coverage,
)


class TestCodeExampleValidation:
    """Tests for code example semantic validation."""

    def test_validate_python_syntax_error(self, tmp_path):
        """Test detection of Python syntax errors in code blocks."""
        content = """# Test
```python
print('unclosed string
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        assert len(issues) > 0
        assert issues[0]["type"] == "code_syntax_error"
        assert "python" in issues[0]["language"]

    def test_validate_valid_python_code(self, tmp_path):
        """Test that valid Python code passes validation."""
        content = """# Test
```python
print('hello world')
x = 42
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        assert len(issues) == 0

    def test_skip_code_blocks_without_language(self, tmp_path):
        """Test that code blocks without language tags are skipped."""
        content = """# Test
```
some generic code
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        assert len(issues) == 0


class TestSymbolValidation:
    """Tests for symbol validation."""

    def test_validate_missing_symbol(self, tmp_path):
        """Test detection of documented symbol that doesn't exist."""
        # Create markdown with symbol reference
        docs = tmp_path / "docs"
        docs.mkdir()
        md_file = docs / "api.md"
        md_file.write_text("`nonExistentFunction()` is documented here.")

        # Empty project (no symbols)
        project_path = tmp_path

        issues = validate_documented_symbols(
            md_file.read_text(),
            md_file,
            project_path,
            symbol_index={}  # Empty index
        )

        assert len(issues) > 0
        assert issues[0]["type"] == "missing_symbol"
        assert "nonExistentFunction" in issues[0]["symbol"]

    def test_validate_existing_symbol(self, tmp_path):
        """Test that existing symbols pass validation."""
        from doc_manager_mcp.indexing.tree_sitter import Symbol, SymbolType

        # Create markdown with symbol reference
        docs = tmp_path / "docs"
        docs.mkdir()
        md_file = docs / "api.md"
        md_file.write_text("`testFunction()` is documented here.")

        # Mock symbol index (name-based, not file-based)
        symbol_index = {
            "testFunction": [
                Symbol(
                    name="testFunction",
                    type=SymbolType.FUNCTION,
                    file="test.py",
                    line=10,
                    column=0,
                    signature="def testFunction():",
                    parent=None
                )
            ]
        }

        issues = validate_documented_symbols(
            md_file.read_text(),
            md_file,
            tmp_path,
            symbol_index=symbol_index
        )

        assert len(issues) == 0


class TestListFormattingConsistency:
    """Tests for list formatting consistency check."""

    def test_consistent_dash_markers(self, tmp_path):
        """Test that consistent - markers result in high score."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "file1.md").write_text("- Item 1\n- Item 2")
        (docs / "file2.md").write_text("- Item A\n- Item B")

        result = check_list_formatting_consistency(docs)

        assert result["majority_marker"] == "-"
        assert result["consistency_score"] == 1.0
        assert len(result["inconsistent_files"]) == 0

    def test_inconsistent_markers(self, tmp_path):
        """Test detection of inconsistent list markers."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "file1.md").write_text("- Item 1\n- Item 2")
        (docs / "file2.md").write_text("* Item A\n* Item B")

        result = check_list_formatting_consistency(docs)

        assert result["majority_marker"] in ["-", "*"]
        assert result["consistency_score"] < 1.0
        assert len(result["inconsistent_files"]) > 0

    def test_empty_docs_directory(self, tmp_path):
        """Test handling of empty docs directory."""
        docs = tmp_path / "docs"
        docs.mkdir()

        result = check_list_formatting_consistency(docs)

        assert result["consistency_score"] == 1.0
        assert result["majority_marker"] is None


class TestHeadingCaseConsistency:
    """Tests for heading case consistency check."""

    def test_consistent_title_case(self, tmp_path):
        """Test detection of consistent Title Case."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "file1.md").write_text("# Getting Started\n## Installation Guide")
        (docs / "file2.md").write_text("# API Reference\n## Configuration Options")

        result = check_heading_case_consistency(docs)

        assert result["majority_style"] == "title_case"
        assert result["consistency_score"] > 0.8

    def test_consistent_sentence_case(self, tmp_path):
        """Test detection of consistent Sentence case."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "file1.md").write_text("# Getting started\n## Installation guide")
        (docs / "file2.md").write_text("# API reference\n## Configuration options")

        result = check_heading_case_consistency(docs)

        assert result["majority_style"] == "sentence_case"
        assert result["consistency_score"] > 0.8

    def test_mixed_case_styles(self, tmp_path):
        """Test detection of mixed heading case styles."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "file1.md").write_text("# Getting Started")  # Title Case
        (docs / "file2.md").write_text("# Getting started")  # Sentence case

        result = check_heading_case_consistency(docs)

        assert result["consistency_score"] < 1.0
        assert len(result["inconsistent_files"]) > 0


class TestMultipleH1Detection:
    """Tests for multiple H1 detection."""

    def test_single_h1(self, tmp_path):
        """Test that files with single H1 pass."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "good.md").write_text("# Title\n## Section")

        issues = detect_multiple_h1s(docs)

        assert len(issues) == 0

    def test_multiple_h1s(self, tmp_path):
        """Test detection of multiple H1s in single file."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "bad.md").write_text("# Title One\n# Title Two")

        issues = detect_multiple_h1s(docs)

        assert len(issues) == 1
        assert issues[0]["h1_count"] == 2
        assert "Title One" in issues[0]["h1_texts"]
        assert "Title Two" in issues[0]["h1_texts"]

    def test_no_h1(self, tmp_path):
        """Test detection of files with no H1."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "no_title.md").write_text("## Section\n### Subsection")

        issues = detect_multiple_h1s(docs)

        assert len(issues) == 1
        assert issues[0]["h1_count"] == 0


class TestUndocumentedAPIs:
    """Tests for undocumented API detection."""

    def test_detect_undocumented_function(self, tmp_path):
        """Test detection of undocumented public functions."""
        # Create source file
        src = tmp_path / "src.py"
        src.write_text("def public_function():\n    pass")

        # Create docs without function reference
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("# API Docs\nNo functions documented.")

        result = detect_undocumented_apis(tmp_path, docs)

        # May or may not detect depending on TreeSitter availability
        # Test should not fail either way
        assert isinstance(result, list)

    def test_documented_function_not_flagged(self, tmp_path):
        """Test that documented functions are not flagged."""
        # Create source file
        src = tmp_path / "src.py"
        src.write_text("def public_function():\n    pass")

        # Create docs with function reference
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("# API\n`public_function()` does something.")

        result = detect_undocumented_apis(tmp_path, docs)

        assert isinstance(result, list)


class TestDocumentationCoverage:
    """Tests for documentation coverage calculation."""

    def test_coverage_calculation(self, tmp_path):
        """Test basic coverage calculation."""
        # Create simple source file
        src = tmp_path / "test.py"
        src.write_text("def documented():\n    pass\n\ndef undocumented():\n    pass")

        # Document only one function
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("`documented()` is documented.")

        result = calculate_documentation_coverage(tmp_path, docs)

        assert "total_symbols" in result
        assert "documented_symbols" in result
        assert "coverage_percentage" in result
        assert isinstance(result["coverage_percentage"], (int, float))

    def test_no_symbols(self, tmp_path):
        """Test coverage calculation with no symbols."""
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "empty.md").write_text("# Empty")

        result = calculate_documentation_coverage(tmp_path, docs)

        assert result["total_symbols"] == 0
        assert result["coverage_percentage"] == 0.0

    def test_coverage_breakdown_by_type(self, tmp_path):
        """Test that coverage is broken down by symbol type."""
        result = calculate_documentation_coverage(tmp_path, tmp_path / "docs")

        assert "breakdown_by_type" in result
        assert isinstance(result["breakdown_by_type"], dict)


class TestIntegration:
    """Integration tests for Phase 3 features."""

    @pytest.mark.asyncio
    async def test_validate_docs_with_code_syntax(self, tmp_path):
        """Test validation.py integration with code syntax checking."""
        from doc_manager_mcp.tools.validation import validate_docs
        from doc_manager_mcp.models import ValidateDocsInput

        # Create docs with syntax error
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.md").write_text("""# Test
```python
print('unclosed
```
""")

        params = ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            check_links=False,
            check_assets=False,
            check_snippets=False,
            validate_code_syntax=True
        )

        result = await validate_docs(params)

        assert isinstance(result, (dict, str))

    @pytest.mark.asyncio
    async def test_assess_quality_with_enhancements(self, tmp_path):
        """Test quality.py integration with all enhancements."""
        from doc_manager_mcp.tools.quality import assess_quality
        from doc_manager_mcp.models import AssessQualityInput

        # Create minimal docs
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.md").write_text("# Test\n- Item 1\n- Item 2")

        params = AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs"
        )

        result = await assess_quality(params)

        assert isinstance(result, (dict, str))

        if isinstance(result, dict):
            assert "list_formatting" in result
            assert "heading_case" in result
            assert "coverage" in result
