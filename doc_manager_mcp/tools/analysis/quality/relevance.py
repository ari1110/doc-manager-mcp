"""Relevance assessment for documentation quality."""

import re
import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import get_doc_relative_path

from .utils import remove_code_blocks


def assess_relevance(project_path: Path, docs_path: Path, markdown_files: list[Path]) -> dict[str, Any]:
    """Assess if documentation addresses current user needs and use cases."""
    issues = []
    findings = []

    # Check for deprecated/outdated markers
    deprecated_patterns = [
        r'\b(deprecated|obsolete|outdated|legacy|old)\b',
        r'\b(no longer supported|not supported)\b',
        r'\b(removed in|deprecated in)\b'
    ]

    # Context indicators that suggest documentation ABOUT deprecations (not deprecated docs)
    migration_context_patterns = [
        r'\b(migration|migrating|upgrade|upgrading)\b',
        r'\b(how to|guide to|documentation for)\b',
        r'\b(breaking changes?|changelog|release notes)\b'
    ]

    deprecated_count = 0
    files_with_deprecated = []

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Remove code blocks to avoid counting code comments
            content_without_code = remove_code_blocks(content)

            # Check if this is migration/changelog documentation
            is_migration_doc = any(
                re.search(pattern, content_without_code, re.IGNORECASE)
                for pattern in migration_context_patterns
            ) or 'migration' in md_file.name.lower() or 'changelog' in md_file.name.lower()

            # Check for deprecated markers
            for pattern in deprecated_patterns:
                matches = list(re.finditer(pattern, content_without_code, re.IGNORECASE))
                if matches:
                    # If this is migration/changelog docs, reduce the weight
                    if is_migration_doc:
                        # Only count 10% of matches in migration docs
                        deprecated_count += len(matches) * 0.1
                    else:
                        deprecated_count += len(matches)

                    if str(md_file) not in files_with_deprecated:
                        files_with_deprecated.append(get_doc_relative_path(md_file, docs_path, project_path))

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)

    if deprecated_count > 0:
        # Round at display to avoid floating point precision issues (Bug #2 fix)
        findings.append(f"Found {round(deprecated_count)} references to deprecated/outdated content across {len(files_with_deprecated)} files")

    # Check if README exists (relevance to getting started)
    has_readme = (docs_path / "README.md").exists() or (docs_path.parent / "README.md").exists()
    if not has_readme:
        issues.append({
            "severity": "warning",
            "message": "No README.md found - users may not know where to start"
        })

    # Calculate score
    score = "good"
    if deprecated_count > 10:
        score = "fair"
        issues.append({
            "severity": "warning",
            # Round at display to avoid floating point precision issues (Bug #2 fix)
            "message": f"High number of deprecated references ({round(deprecated_count)}) - consider removing or updating outdated content"
        })
    elif deprecated_count > 5:
        findings.append("Some deprecated content found - ensure it's clearly marked with migration guidance")

    return {
        "criterion": "relevance",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            # Round at display to avoid floating point precision issues (Bug #2 fix)
            "deprecated_references": round(deprecated_count),
            "files_with_deprecated": len(files_with_deprecated),
            "has_readme": has_readme
        }
    }
