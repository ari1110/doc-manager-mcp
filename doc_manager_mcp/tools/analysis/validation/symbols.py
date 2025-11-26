"""Symbol validation for documentation."""

import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    find_markdown_files,
    get_doc_relative_path,
)
from doc_manager_mcp.indexing.analysis.tree_sitter import SymbolIndexer

from .helpers import validate_documented_symbols


def validate_symbols(
    docs_path: Path,
    project_path: Path,
    include_root_readme: bool = False,
    symbol_index=None,
    markdown_files: list[Path] | None = None
) -> list[dict[str, Any]]:
    """Validate that documented symbols exist in codebase."""
    issues = []
    if markdown_files is None:
        markdown_files = find_markdown_files(
            docs_path,
            project_path=project_path,
            validate_boundaries=False,
            include_root_readme=include_root_readme
        )

    # Build symbol index once if not provided
    if symbol_index is None:
        try:
            indexer = SymbolIndexer()
            indexer.index_project(project_path)
            symbol_index = indexer.index
        except Exception as e:
            # TreeSitter not available or indexing failed
            print(f"Warning: Symbol indexing failed: {e}", file=sys.stderr)
            return []

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Use validation_helpers function
            file_issues = validate_documented_symbols(content, md_file, project_path, symbol_index, docs_path)
            issues.extend(file_issues)

        except Exception as e:
            issues.append({
                "type": "read_error",
                "severity": "error",
                "file": get_doc_relative_path(md_file, docs_path, project_path),
                "line": 1,
                "message": f"Failed to read file: {e!s}"
            })

    return issues
