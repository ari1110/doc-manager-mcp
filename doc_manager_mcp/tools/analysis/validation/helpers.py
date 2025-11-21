"""Helper functions for validation.py to prevent file bloat."""

from pathlib import Path
from typing import Any

from doc_manager_mcp.constants import CLASS_EXCLUDES, CLASS_PATTERN, FUNCTION_PATTERN
from doc_manager_mcp.core import get_doc_relative_path
from doc_manager_mcp.indexing.analysis.code_validator import CodeValidator
from doc_manager_mcp.indexing.analysis.tree_sitter import Symbol, SymbolIndexer
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser


def validate_code_examples(
    content: str,
    file_path: Path,
    project_path: Path,
    docs_path: Path
) -> list[dict[str, Any]]:
    """Validate code examples for semantic correctness.

    Uses TreeSitter to check if code examples are syntactically valid.

    Args:
        content: Markdown content
        file_path: Path to markdown file
        project_path: Project root
        docs_path: Documentation directory path

    Returns:
        List of issues found in code examples
    """
    issues = []
    parser = MarkdownParser()
    validator = CodeValidator()

    # Extract code blocks from markdown
    code_blocks = parser.extract_code_blocks(content)

    for block in code_blocks:
        # Skip code blocks without language tags
        if not block["language"]:
            continue

        # Normalize language names for TreeSitter
        language = block["language"].lower()
        if language == "py":
            language = "python"
        elif language == "js":
            language = "javascript"
        elif language == "ts":
            language = "typescript"

        # Validate syntax using TreeSitter
        result = validator.validate_syntax(language, block["code"])

        # Report syntax errors
        if not result["valid"] and result["errors"]:
            for error in result["errors"]:
                issues.append({
                    "type": "code_syntax_error",
                    "severity": "warning",
                    "file": get_doc_relative_path(file_path, docs_path, project_path),
                    "line": block["line"] + error["line"] - 1,  # Adjust line number
                    "message": f"{language}: {error['message']} at line {error['line']}, column {error['column']}",
                    "language": block["language"],
                    "error_text": error.get("text", "")
                })

    return issues


def validate_documented_symbols(
    content: str,
    file_path: Path,
    project_path: Path,
    symbol_index: dict[str, list[Symbol]] | None = None,
    docs_path: Path | None = None
) -> list[dict[str, Any]]:
    """Validate that documented symbols exist in codebase.

    Extracts symbol references from markdown and checks against TreeSitter index.

    Args:
        content: Markdown content
        file_path: Path to markdown file
        project_path: Project root
        symbol_index: Pre-built symbol index (from SymbolIndexer) or None to build
        docs_path: Documentation directory path (for relative path computation)

    Returns:
        List of issues for documented symbols that don't exist
    """
    issues = []

    # Build symbol index if not provided
    indexer = None
    if symbol_index is None:
        try:
            indexer = SymbolIndexer()
            indexer.index_project(project_path)
            symbol_index = indexer.index
        except Exception:
            # TreeSitter not available or indexing failed
            return []

    # Extract inline code references using MarkdownParser
    parser = MarkdownParser()
    inline_codes = parser.extract_inline_code(content)

    for code_span in inline_codes:
        code_text = code_span["text"]
        line = code_span["line"]

        # Check if it's a function reference
        if match := FUNCTION_PATTERN.match(code_text):
            # Extract function name (without parentheses and namespace)
            func_name = code_text.replace('()', '').split('.')[-1]

            # Look up in symbol index
            symbols = symbol_index.get(func_name, [])

            if not symbols:
                # Use get_doc_relative_path if docs_path provided, otherwise fall back
                file_str = get_doc_relative_path(file_path, docs_path, project_path) if docs_path else str(file_path.relative_to(project_path))
                issues.append({
                    "type": "missing_symbol",
                    "severity": "warning",
                    "file": file_str,
                    "line": line,
                    "message": f"Function '{code_text}' not found in codebase",
                    "symbol": code_text,
                    "symbol_type": "function"
                })

        # Check if it's a class reference
        elif match := CLASS_PATTERN.match(code_text):
            class_name = match.group(1)

            # Exclude common acronyms and short words
            if len(class_name) <= 2 or class_name in CLASS_EXCLUDES:
                continue

            # Look up in symbol index
            symbols = symbol_index.get(class_name, [])

            if not symbols:
                # Use get_doc_relative_path if docs_path provided, otherwise fall back
                file_str = get_doc_relative_path(file_path, docs_path, project_path) if docs_path else str(file_path.relative_to(project_path))
                issues.append({
                    "type": "missing_symbol",
                    "severity": "warning",
                    "file": file_str,
                    "line": line,
                    "message": f"Class '{class_name}' not found in codebase",
                    "symbol": class_name,
                    "symbol_type": "class"
                })

    return issues
