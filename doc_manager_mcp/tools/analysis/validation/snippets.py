"""Code snippet validation for documentation."""

from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    find_markdown_files,
    get_doc_relative_path,
)
from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.analysis.code_validator import CodeValidator
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser


def extract_code_blocks(
    content: str,
    file_path: Path,
    markdown_cache: MarkdownCache | None = None
) -> list[dict[str, Any]]:
    """Extract code blocks from markdown content."""
    code_blocks = []

    # Extract fenced code blocks using cache or parser
    if markdown_cache:
        parsed = markdown_cache.parse(file_path, content)
        blocks = parsed.code_blocks
    else:
        parser = MarkdownParser()
        blocks = parser.extract_code_blocks(content)

    for block in blocks:
        code_blocks.append({
            "language": block["language"] or "plaintext",
            "code": block["code"],
            "line": block["line"],
            "file": str(file_path)
        })

    return code_blocks


def validate_code_snippets(
    docs_path: Path,
    project_path: Path,
    include_root_readme: bool = False,
    markdown_cache: MarkdownCache | None = None,
    markdown_files: list[Path] | None = None
) -> list[dict[str, Any]]:
    """Extract and validate code snippets using TreeSitter."""
    issues = []
    validator = CodeValidator()
    if markdown_files is None:
        markdown_files = find_markdown_files(
            docs_path,
            project_path=project_path,
            validate_boundaries=False,
            include_root_readme=include_root_readme
        )

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            code_blocks = extract_code_blocks(content, md_file, markdown_cache)

            for block in code_blocks:
                # Normalize language names for TreeSitter
                language = block['language'].lower()
                if language == 'py':
                    language = 'python'
                elif language == 'js':
                    language = 'javascript'
                elif language == 'ts':
                    language = 'typescript'

                # Validate syntax using TreeSitter
                result = validator.validate_syntax(language, block['code'])

                if not result['valid'] and result['errors']:
                    for error in result['errors']:
                        issues.append({
                            "type": "syntax_error",
                            "severity": "warning",
                            "file": get_doc_relative_path(md_file, docs_path, project_path),
                            "line": block['line'] + error['line'] - 1,  # Adjust line number
                            "message": f"{error['message']} at line {error['line']}, column {error['column']}",
                            "language": block['language']
                        })

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": get_doc_relative_path(md_file, docs_path, project_path),
                "line": 1,
                "message": f"Failed to read file: {e!s}"
            })

    return issues
