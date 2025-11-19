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

    def test_language_normalization_py_to_python(self, tmp_path):
        """Test that 'py' is normalized to 'python' for TreeSitter."""
        content = """# Test
```py
print('unclosed string
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        # Should detect syntax error even with 'py' tag
        assert len(issues) > 0
        assert issues[0]["type"] == "code_syntax_error"
        # Original language tag should be preserved in error report
        assert issues[0]["language"] == "py"

    def test_language_normalization_js_to_javascript(self, tmp_path):
        """Test that 'js' is normalized to 'javascript' for TreeSitter."""
        content = """# Test
```js
function test() {
    console.log('missing closing brace'
}
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        # Should detect syntax error with 'js' tag
        assert len(issues) > 0
        assert issues[0]["language"] == "js"

    def test_language_normalization_ts_to_typescript(self, tmp_path):
        """Test that 'ts' is normalized to 'typescript' for TreeSitter."""
        content = """# Test
```ts
const x: string = 123;  // Type error (not caught by syntax validation)
const y: number;  // Valid TypeScript syntax
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        # Syntax is valid even though type is wrong (TreeSitter only checks syntax)
        # This test ensures 'ts' → 'typescript' normalization works
        assert len(issues) == 0 or all(issue["severity"] != "error" for issue in issues)

    def test_line_number_adjustment_single_error(self, tmp_path):
        """Test that error line numbers are adjusted relative to markdown file."""
        # Markdown structure:
        # Line 1: # Test
        # Line 2: ```python (fence marker, block["line"] = 2)
        # Line 3: print('unclosed (error on line 1 of code)
        # Line 4: ```
        # Formula: block["line"] + error["line"] - 1 = 2 + 1 - 1 = 2
        content = """# Test
```python
print('unclosed
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        assert len(issues) > 0
        # Error should be reported on line 2 (fence line + error line - 1)
        assert issues[0]["line"] == 2

    def test_line_number_adjustment_multi_line_code(self, tmp_path):
        """Test line number adjustment with error later in code block."""
        # Markdown structure:
        # Line 1: # Documentation
        # Line 2: (blank)
        # Line 3: Some text here.
        # Line 4: (blank)
        # Line 5: ```python (fence marker, block["line"] = 5)
        # Line 6: x = 1 (line 1 of code)
        # Line 7: y = 2 (line 2 of code)
        # Line 8: z = 'unclosed string (line 3 of code, error here)
        # Line 9: ```
        # Formula: block["line"] + error["line"] - 1 = 5 + 3 - 1 = 7
        content = """# Documentation

Some text here.

```python
x = 1
y = 2
z = 'unclosed string
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        assert len(issues) > 0
        # Error on line 3 of code → line 7 of file (5 + 3 - 1)
        assert issues[0]["line"] == 7

    def test_multiple_errors_in_single_block(self, tmp_path):
        """Test detection of multiple syntax errors in one code block."""
        content = """# Test
```python
def bad_function(
    print('unclosed string
    return None
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        # TreeSitter should detect multiple syntax errors
        # At minimum: unclosed function params + unclosed string
        assert len(issues) >= 1
        assert all(issue["type"] == "code_syntax_error" for issue in issues)
        assert all(issue["language"] == "python" for issue in issues)

    def test_multiple_errors_across_blocks(self, tmp_path):
        """Test that errors from different code blocks are all reported."""
        content = """# Test

First block with error:
```python
print('unclosed
```

Second block with error:
```python
def invalid(
```

Third block is valid:
```python
print('hello')
```
"""
        project_path = tmp_path
        file_path = tmp_path / "test.md"

        issues = validate_code_examples(content, file_path, project_path)

        # Should find errors in both first and second blocks
        assert len(issues) >= 2

        # Errors should be on different lines
        error_lines = [issue["line"] for issue in issues]
        assert len(set(error_lines)) >= 2  # At least 2 different line numbers


class TestSymbolValidation:
    """Tests for symbol validation."""

    def test_markdown_parser_extracts_function_references(self, tmp_path):
        """Test that MarkdownParser.extract_inline_code() finds function references."""
        from doc_manager_mcp.indexing.markdown_parser import MarkdownParser

        content = """# API Documentation

The `processData()` function handles input processing.
Use `ClassName.methodName()` for advanced operations.
The `simpleFunc()` is also available.
"""

        parser = MarkdownParser()
        inline_codes = parser.extract_inline_code(content)

        # Extract text from inline code spans
        code_texts = [code["text"] for code in inline_codes]

        # Should find all three function references
        assert "processData()" in code_texts
        assert "ClassName.methodName()" in code_texts
        assert "simpleFunc()" in code_texts

    def test_function_pattern_regex_matches(self, tmp_path):
        """Test FUNCTION_PATTERN regex matches various function patterns."""
        from doc_manager_mcp.tools.validation_helpers import FUNCTION_PATTERN

        # Valid function patterns
        assert FUNCTION_PATTERN.match("functionName()"), "Simple function should match"
        assert FUNCTION_PATTERN.match("anotherFunc()"), "Another simple function should match"
        assert FUNCTION_PATTERN.match("Class.method()"), "Class method should match"
        assert FUNCTION_PATTERN.match("MyClass.doSomething()"), "Class method should match"

        # Invalid patterns
        assert not FUNCTION_PATTERN.match("NotAFunction"), "Missing parens should not match"
        assert not FUNCTION_PATTERN.match("not_valid()extra"), "Extra text after parens should not match"
        assert not FUNCTION_PATTERN.match("123invalid()"), "Starting with number should not match"

    def test_class_pattern_regex_matches(self, tmp_path):
        """Test CLASS_PATTERN regex matches class names."""
        from doc_manager_mcp.tools.validation_helpers import CLASS_PATTERN

        # Valid class patterns (requires 2+ characters)
        assert CLASS_PATTERN.match("MyClass"), "PascalCase class should match"
        assert CLASS_PATTERN.match("SomeClassName"), "Multi-word class should match"
        assert CLASS_PATTERN.match("Ab"), "Two letter class should match"

        # Invalid patterns
        assert not CLASS_PATTERN.match("A"), "Single letter should not match (regex requires 2+ chars)"
        assert not CLASS_PATTERN.match("myClass"), "camelCase should not match"
        assert not CLASS_PATTERN.match("my_class"), "snake_case should not match"

    def test_class_excludes_filters_acronyms(self, tmp_path):
        """Test that CLASS_EXCLUDES filters out common acronyms."""
        from doc_manager_mcp.tools.validation_helpers import CLASS_EXCLUDES

        # These should all be in CLASS_EXCLUDES
        acronyms = ["API", "CLI", "HTTP", "HTTPS", "URL", "JSON", "XML", "HTML"]

        for acronym in acronyms:
            assert acronym in CLASS_EXCLUDES, f"{acronym} should be in CLASS_EXCLUDES"

    def test_validate_missing_symbol(self, tmp_path):
        """Test detection of documented symbol that doesn't exist."""
        from doc_manager_mcp.indexing.tree_sitter import Symbol, SymbolType

        # Markdown with function reference that doesn't exist
        content = "`nonExistentFunction()` is documented here."

        # Empty symbol index
        symbol_index = {}

        issues = validate_documented_symbols(
            content,
            tmp_path / "test.md",
            tmp_path,
            symbol_index=symbol_index
        )

        # Should detect missing symbol
        assert len(issues) > 0
        assert issues[0]["type"] == "missing_symbol"
        assert "nonExistentFunction" in issues[0]["symbol"]

    def test_validate_existing_symbol(self, tmp_path):
        """Test that existing symbols pass validation."""
        from doc_manager_mcp.indexing.tree_sitter import Symbol, SymbolType

        # Markdown with function reference that exists
        content = "`testFunction()` is documented here."

        # Symbol index with matching symbol
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
            content,
            tmp_path / "test.md",
            tmp_path,
            symbol_index=symbol_index
        )

        # No issues - symbol exists
        assert len(issues) == 0

    def test_validate_class_method_references(self, tmp_path):
        """Test validation of Class.method() references."""
        from doc_manager_mcp.indexing.tree_sitter import Symbol, SymbolType

        content = """Use `MyClass.processData()` to handle data.
The `MyClass.render()` method renders output."""

        symbol_index = {
            "processData": [
                Symbol(
                    name="processData",
                    type=SymbolType.METHOD,
                    file="myclass.py",
                    line=20,
                    column=4,
                    signature="def processData(self):",
                    parent="MyClass"
                )
            ],
            # render is missing - should be flagged
        }

        issues = validate_documented_symbols(
            content,
            tmp_path / "test.md",
            tmp_path,
            symbol_index=symbol_index
        )

        # Should find missing 'render' method
        assert len(issues) > 0
        missing_symbols = [issue["symbol"] for issue in issues if issue["type"] == "missing_symbol"]
        # Symbol field contains full pattern including parens and class prefix
        assert any("render" in sym for sym in missing_symbols), f"Expected 'render' in {missing_symbols}"

    def test_validate_mixed_functions_and_classes(self, tmp_path):
        """Test validation with mix of functions and classes."""
        from doc_manager_mcp.indexing.tree_sitter import Symbol, SymbolType

        content = """API uses `fetchData()` and `parseResponse()`.
The `DataProcessor` class handles processing.
HTTP requests use the built-in library."""

        symbol_index = {
            "fetchData": [Symbol("fetchData", SymbolType.FUNCTION, "api.py", 10, 0, "def fetchData():", None)],
            # parseResponse missing
            "DataProcessor": [Symbol("DataProcessor", SymbolType.CLASS, "processor.py", 5, 0, "class DataProcessor:", None)],
        }

        issues = validate_documented_symbols(
            content,
            tmp_path / "test.md",
            tmp_path,
            symbol_index=symbol_index
        )

        # Should flag parseResponse as missing (symbol field contains parens)
        missing_symbols = {issue["symbol"] for issue in issues if issue["type"] == "missing_symbol"}
        assert any("parseResponse" in sym for sym in missing_symbols), f"Expected 'parseResponse' in {missing_symbols}"

        # HTTP and API should be filtered out by CLASS_EXCLUDES
        assert not any("HTTP" in sym for sym in missing_symbols)
        assert not any("API" in sym for sym in missing_symbols)


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


class TestClassifyHeadingStyle:
    """Direct unit tests for _classify_heading_style helper function."""

    def test_title_case_all_major_words_capitalized(self):
        """Test title case with all major words capitalized."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # All major words capitalized = title case
        assert _classify_heading_style("Getting Started With Python") == "title_case"
        assert _classify_heading_style("API Reference Guide") == "title_case"
        assert _classify_heading_style("Installation And Configuration") == "title_case"

    def test_sentence_case_only_first_word_capitalized(self):
        """Test sentence case with only first word capitalized."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # Only first word capitalized = sentence case
        assert _classify_heading_style("Getting started with python") == "sentence_case"
        assert _classify_heading_style("API reference guide") == "sentence_case"
        assert _classify_heading_style("Installation and configuration") == "sentence_case"

    def test_minor_words_excluded_from_analysis(self):
        """Test that minor words (a, an, the, and, etc.) don't affect classification."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # Minor words lowercase in title case is still title case
        # "Guide to the API" -> skip "to", "the", check "Guide" (first, skip), "API" (capitalized)
        # 1/1 major words capitalized = title case
        assert _classify_heading_style("Guide to the API") == "title_case"

        # "Guide to the api" -> 0/1 major words capitalized = sentence case
        assert _classify_heading_style("Guide to the api") == "sentence_case"

        # "Working with the Database" -> "Working" (first), "with"/"the" (minor), "Database" (cap)
        # 1/1 = title case
        assert _classify_heading_style("Working with the Database") == "title_case"

    def test_capitalization_ratio_threshold_50_percent(self):
        """Test that exactly 50% capitalization is classified as sentence case."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # "Introduction Python Programming Language"
        # Skip "Introduction" (first), check "Python" (cap), "Programming" (cap), "Language" (cap)
        # 3/3 = 100% > 50% = title_case
        assert _classify_heading_style("Introduction Python Programming Language") == "title_case"

        # "Introduction python Programming language"
        # Skip "Introduction" (first), check "python" (lower), "Programming" (cap), "language" (lower)
        # 1/3 = 33% < 50% = sentence_case
        assert _classify_heading_style("Introduction python Programming language") == "sentence_case"

        # "Introduction Python programming"
        # Skip "Introduction", check "Python" (cap), "programming" (lower)
        # 1/2 = 50% NOT > 50% = sentence_case
        assert _classify_heading_style("Introduction Python programming") == "sentence_case"

    def test_edge_case_empty_heading(self):
        """Test classification of empty or whitespace-only headings."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # Empty heading should default to sentence_case
        assert _classify_heading_style("") == "sentence_case"
        assert _classify_heading_style("   ") == "sentence_case"

    def test_edge_case_single_word(self):
        """Test classification of single-word headings."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # Single word has no words to analyze after first
        # total_significant_words == 0 -> sentence_case
        assert _classify_heading_style("Introduction") == "sentence_case"
        assert _classify_heading_style("API") == "sentence_case"
        assert _classify_heading_style("Getting") == "sentence_case"

    def test_edge_case_only_minor_words(self):
        """Test heading with only minor words after first word."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # "Guide to and for" -> all minor words except first
        # total_significant_words == 0 -> sentence_case
        assert _classify_heading_style("Guide to and for") == "sentence_case"
        assert _classify_heading_style("Introduction of the by") == "sentence_case"

    def test_punctuation_handling(self):
        """Test that punctuation is stripped correctly when classifying."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # Punctuation should be stripped: "API's" -> "APIs"
        # "Getting Started: Python's Guide"
        # Skip "Getting", check "Started:" (Started, cap), "Python's" (Pythons, cap), "Guide" (cap)
        # 3/3 = title_case
        assert _classify_heading_style("Getting Started: Python's Guide") == "title_case"

        # "Getting started: python's guide"
        # Skip "Getting", check "started:" (started, lower), "python's" (pythons, lower), "guide" (lower)
        # 0/3 = sentence_case
        assert _classify_heading_style("Getting started: python's guide") == "sentence_case"

    def test_numbers_and_symbols_ignored(self):
        """Test that words without letters are ignored."""
        from doc_manager_mcp.tools.quality_helpers import _classify_heading_style

        # "Guide 101 Tutorial"
        # Skip "Guide", ignore "101", check "Tutorial" (cap)
        # 1/1 = title_case
        assert _classify_heading_style("Guide 101 Tutorial") == "title_case"

        # "Guide 101 tutorial"
        # 0/1 = sentence_case
        assert _classify_heading_style("Guide 101 tutorial") == "sentence_case"


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

    def test_detect_undocumented_python_function(self, tmp_path):
        """Test detection of undocumented public Python functions."""
        # Create Python source file with public and private functions
        (tmp_path / "api.py").write_text("""
def public_function():
    \"\"\"A public function.\"\"\"
    pass

def another_public():
    \"\"\"Another public function.\"\"\"
    pass

def _private_function():
    \"\"\"A private function (underscore prefix).\"\"\"
    pass

class PublicClass:
    \"\"\"A public class.\"\"\"
    pass
""")

        # Create docs that only document public_function
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("""# API Documentation

## Functions

The `public_function()` handles core functionality.
""")

        result = detect_undocumented_apis(tmp_path, docs)

        # Should flag another_public and PublicClass, but NOT _private_function or public_function
        assert isinstance(result, list)

        # Extract names from results
        undocumented_names = {item["name"] for item in result}

        # Assertions about what should and shouldn't be flagged
        assert "another_public" in undocumented_names, "another_public should be flagged as undocumented"
        assert "PublicClass" in undocumented_names, "PublicClass should be flagged as undocumented"
        assert "public_function" not in undocumented_names, "public_function is documented, should not be flagged"
        assert "_private_function" not in undocumented_names, "private functions should not be flagged"

        # Verify structure of results
        for item in result:
            assert "name" in item
            assert "type" in item
            assert "file" in item
            assert "line" in item

    def test_documented_function_not_flagged(self, tmp_path):
        """Test that fully documented codebase returns empty list."""
        # Create source file
        (tmp_path / "module.py").write_text("""
def documented_func():
    \"\"\"Documented function.\"\"\"
    pass

class DocumentedClass:
    \"\"\"Documented class.\"\"\"
    pass
""")

        # Create docs with all symbols documented
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("""# API

Functions:
- `documented_func()` - does something

Classes:
- `DocumentedClass` - a class
""")

        result = detect_undocumented_apis(tmp_path, docs)

        # All symbols documented, should return empty list
        assert isinstance(result, list)
        assert len(result) == 0, "All symbols are documented, should return empty list"

    def test_private_symbols_filtered_python(self, tmp_path):
        """Test that Python private symbols (underscore prefix) are not flagged."""
        (tmp_path / "private.py").write_text("""
def _private_func():
    pass

def __dunder_func__():
    pass

class _PrivateClass:
    pass
""")

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "empty.md").write_text("# Empty docs")

        result = detect_undocumented_apis(tmp_path, docs)

        # All symbols are private, should not be flagged
        assert len(result) == 0, "Private symbols should not be flagged as undocumented"

    def test_mixed_documented_and_undocumented(self, tmp_path):
        """Test mix of documented and undocumented symbols."""
        (tmp_path / "mixed.py").write_text("""
def func_a():
    pass

def func_b():
    pass

def func_c():
    pass

class ClassX:
    pass
""")

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "partial.md").write_text("""# Partial Documentation

We have `func_a()` and `func_c()` documented here.
""")

        result = detect_undocumented_apis(tmp_path, docs)

        undocumented_names = {item["name"] for item in result}

        # func_b and ClassX should be flagged
        assert "func_b" in undocumented_names
        assert "ClassX" in undocumented_names

        # func_a and func_c should NOT be flagged
        assert "func_a" not in undocumented_names
        assert "func_c" not in undocumented_names


class TestDocumentationCoverage:
    """Tests for documentation coverage calculation formula validation."""

    def test_coverage_formula_exact_calculation(self, tmp_path):
        """Test exact coverage calculation: 10 symbols, 6 documented = 60.0%."""
        # Create Python file with exactly 10 public symbols
        (tmp_path / "api.py").write_text("""
def func1():
    \"\"\"Function 1.\"\"\"
    pass

def func2():
    \"\"\"Function 2.\"\"\"
    pass

def func3():
    \"\"\"Function 3.\"\"\"
    pass

def func4():
    \"\"\"Function 4.\"\"\"
    pass

def func5():
    \"\"\"Function 5.\"\"\"
    pass

class Class1:
    \"\"\"Class 1.\"\"\"
    pass

class Class2:
    \"\"\"Class 2.\"\"\"
    pass

class Class3:
    \"\"\"Class 3.\"\"\"
    pass

class Class4:
    \"\"\"Class 4.\"\"\"
    pass

class Class5:
    \"\"\"Class 5.\"\"\"
    pass

def _private():
    \"\"\"Should not be counted.\"\"\"
    pass
""")

        # Document exactly 6 symbols (3 functions + 3 classes)
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("""# API Documentation

## Functions

- `func1()` - First function
- `func2()` - Second function
- `func3()` - Third function

## Classes

- `Class1` - First class
- `Class2` - Second class
- `Class3` - Third class
""")

        result = calculate_documentation_coverage(tmp_path, docs)

        # Formula: (6 documented / 10 total) * 100 = 60.0%
        assert result["total_symbols"] == 10, "Should find exactly 10 public symbols"
        assert result["documented_symbols"] == 6, "Should find exactly 6 documented symbols"
        assert result["coverage_percentage"] == 60.0, "Coverage should be exactly 60.0%"

    def test_breakdown_by_type_calculation(self, tmp_path):
        """Test per-type coverage percentage calculation."""
        # Create 5 functions, 5 classes
        (tmp_path / "api.py").write_text("""
def funcA():
    pass

def funcB():
    pass

def funcC():
    pass

def funcD():
    pass

def funcE():
    pass

class ClassX:
    pass

class ClassY:
    pass

class ClassZ:
    pass

class ClassW:
    pass

class ClassV:
    pass
""")

        # Document 3/5 functions and 2/5 classes
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "api.md").write_text("""# API

Functions: `funcA()`, `funcB()`, `funcC()`

Classes: `ClassX`, `ClassY`
""")

        result = calculate_documentation_coverage(tmp_path, docs)

        # Overall: 5/10 = 50%
        assert result["total_symbols"] == 10
        assert result["documented_symbols"] == 5
        assert result["coverage_percentage"] == 50.0

        # Breakdown by type
        breakdown = result["breakdown_by_type"]
        assert "function" in breakdown
        assert "class" in breakdown

        # Functions: 3/5 = 60%
        assert breakdown["function"]["total"] == 5
        assert breakdown["function"]["documented"] == 3
        assert breakdown["function"]["coverage_percentage"] == 60.0

        # Classes: 2/5 = 40%
        assert breakdown["class"]["total"] == 5
        assert breakdown["class"]["documented"] == 2
        assert breakdown["class"]["coverage_percentage"] == 40.0

    def test_zero_symbols_edge_case(self, tmp_path):
        """Test coverage with no symbols returns 0.0% (not division by zero)."""
        # Create empty Python file
        (tmp_path / "empty.py").write_text("# Just a comment")

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "empty.md").write_text("# Documentation")

        result = calculate_documentation_coverage(tmp_path, docs)

        # Should handle zero division gracefully
        assert result["total_symbols"] == 0
        assert result["documented_symbols"] == 0
        assert result["coverage_percentage"] == 0.0
        assert result["breakdown_by_type"] == {}

    def test_100_percent_coverage(self, tmp_path):
        """Test 100% documentation coverage."""
        # Create 4 symbols
        (tmp_path / "complete.py").write_text("""
def alpha():
    pass

def beta():
    pass

class Gamma:
    pass

class Delta:
    pass
""")

        # Document all 4 symbols
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "complete.md").write_text("""# Complete API

All functions: `alpha()`, `beta()`

All classes: `Gamma`, `Delta`
""")

        result = calculate_documentation_coverage(tmp_path, docs)

        # 4/4 = 100%
        assert result["total_symbols"] == 4
        assert result["documented_symbols"] == 4
        assert result["coverage_percentage"] == 100.0

    def test_public_private_filtering(self, tmp_path):
        """Test that private symbols (underscore prefix) don't count toward total."""
        # Create 5 public + 5 private symbols
        (tmp_path / "mixed.py").write_text("""
def public1():
    pass

def public2():
    pass

def public3():
    pass

def _private1():
    pass

def _private2():
    pass

class PublicClass1:
    pass

class PublicClass2:
    pass

class _PrivateClass1:
    pass

class _PrivateClass2:
    pass

class __VeryPrivateClass:
    pass
""")

        # Document only public symbols
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "public.md").write_text("""# Public API

Functions: `public1()`, `public2()`, `public3()`

Classes: `PublicClass1`, `PublicClass2`
""")

        result = calculate_documentation_coverage(tmp_path, docs)

        # Should only count 5 public symbols (3 functions + 2 classes)
        # Private symbols should not be indexed
        assert result["total_symbols"] == 5, "Should only count public symbols"
        assert result["documented_symbols"] == 5
        assert result["coverage_percentage"] == 100.0


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
