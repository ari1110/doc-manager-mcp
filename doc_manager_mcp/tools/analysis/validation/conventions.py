"""Documentation conventions validation."""

import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    find_markdown_files,
    get_doc_relative_path,
    validate_against_conventions,
)


def validate_conventions(
    docs_path: Path,
    project_path: Path,
    conventions,
    include_root_readme: bool = False,
    markdown_files: list[Path] | None = None
) -> list[dict[str, Any]]:
    """Validate documentation files against conventions.

    Args:
        docs_path: Path to documentation directory
        project_path: Path to project root
        conventions: DocumentationConventions object
        include_root_readme: Whether to include root README.md
        markdown_files: Optional pre-filtered list of files (for incremental mode)

    Returns:
        List of convention violations
    """
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

            # Validate against conventions
            violations = validate_against_conventions(
                content,
                conventions,
                get_doc_relative_path(md_file, docs_path, project_path)
            )

            # Convert violations to issue format
            for violation in violations:
                issues.append({
                    "type": "convention",
                    "severity": violation.get("severity", "warning"),
                    "file": violation.get("file", get_doc_relative_path(md_file, docs_path, project_path)),
                    "line": violation.get("line"),
                    "rule": violation.get("rule"),
                    "message": violation.get("message")
                })

        except Exception as e:
            print(f"Warning: Failed to validate conventions in {md_file}: {e}", file=sys.stderr)
            continue

    return issues
