"""Code syntax validation for documentation."""

from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    find_markdown_files,
    get_doc_relative_path,
)

from .helpers import validate_code_examples


def validate_code_syntax(
    docs_path: Path,
    project_path: Path,
    include_root_readme: bool = False,
    markdown_files: list[Path] | None = None
) -> list[dict[str, Any]]:
    """Validate code example syntax using TreeSitter (semantic validation)."""
    issues = []
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

            # Use validation_helpers function
            file_issues = validate_code_examples(content, md_file, project_path, docs_path)
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
