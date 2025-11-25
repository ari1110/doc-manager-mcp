"""Structure assessment for documentation quality."""

import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser

from .helpers import detect_multiple_h1s


def assess_structure(
    project_path: Path,
    docs_path: Path,
    markdown_files: list[Path],
    markdown_cache: MarkdownCache | None = None
) -> dict[str, Any]:
    """Assess logical organization and hierarchy."""
    issues = []
    findings = []

    # Check directory structure
    subdirs = [d for d in docs_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    findings.append(f"Documentation has {len(subdirs)} subdirectories")

    # Check heading hierarchy
    heading_issues = 0
    max_heading_depth = 0

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Extract all headings using cache or parser
            if markdown_cache:
                parsed = markdown_cache.parse(md_file, content)
                headers = parsed.headings
            else:
                parser = MarkdownParser()
                headers = parser.extract_headers(content)
            heading_levels = [h["level"] for h in headers]

            for level in heading_levels:
                max_heading_depth = max(max_heading_depth, level)

            # Check for heading hierarchy issues (skipping levels)
            for i in range(len(heading_levels) - 1):
                if heading_levels[i+1] > heading_levels[i] + 1:
                    heading_issues += 1
                    break  # Count once per file

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)

    # Check for multiple H1s using helper function
    multiple_h1_issues = detect_multiple_h1s(docs_path)

    if heading_issues > 0:
        issues.append({
            "severity": "warning",
            "message": f"{heading_issues} files have heading hierarchy issues (skipped levels)"
        })

    if max_heading_depth > 4:
        issues.append({
            "severity": "info",
            "message": f"Maximum heading depth is H{max_heading_depth} - consider restructuring deeply nested content"
        })

    if multiple_h1_issues:
        issues.append({
            "severity": "warning",
            "message": f"{len(multiple_h1_issues)} files have incorrect number of H1 headers (should be exactly 1)"
        })

    findings.append(f"Maximum heading depth: H{max_heading_depth}")
    findings.append(f"Files organized in {len(subdirs)} subdirectories")

    # Adjust score based on H1 issues
    score_penalty = len(multiple_h1_issues) > 0
    score = "good" if heading_issues < 3 and max_heading_depth <= 4 and not score_penalty else "fair"

    return {
        "criterion": "structure",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "subdirectories": len(subdirs),
            "max_heading_depth": max_heading_depth,
            "files_with_hierarchy_issues": heading_issues
        },
        "multiple_h1_issues": multiple_h1_issues
    }
