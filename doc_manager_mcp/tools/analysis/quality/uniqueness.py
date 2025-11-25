"""Uniqueness assessment for documentation quality."""

import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import get_doc_relative_path
from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser


def assess_uniqueness(
    project_path: Path,
    docs_path: Path,
    markdown_files: list[Path],
    markdown_cache: MarkdownCache | None = None
) -> dict[str, Any]:
    """Assess if there's redundant or duplicate information."""
    issues = []
    findings = []

    # Extract all H1 and H2 headers to check for duplicates
    headers = {}

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Extract headers using cache or parser
            if markdown_cache:
                parsed = markdown_cache.parse(md_file, content)
                all_headers = parsed.headings
            else:
                parser = MarkdownParser()
                all_headers = parser.extract_headers(content)

            # Filter for H1 and H2 only
            for header in all_headers:
                if header["level"] in [1, 2]:
                    header_text = header["text"].strip().lower()
                    if header_text not in headers:
                        headers[header_text] = []
                    headers[header_text].append(get_doc_relative_path(md_file, docs_path, project_path))

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)

    # Find duplicate headers (same header text in multiple files)
    duplicate_headers = {k: v for k, v in headers.items() if len(v) > 1}

    if duplicate_headers:
        findings.append(f"Found {len(duplicate_headers)} duplicate header topics across files")
        for header, files in list(duplicate_headers.items())[:5]:  # Show first 5
            issues.append({
                "severity": "info",
                "message": f"Duplicate topic '{header}' found in: {', '.join(files[:3])}"
            })
    else:
        findings.append("No duplicate headers detected - good information architecture")

    score = "good" if len(duplicate_headers) < 5 else "fair"

    return {
        "criterion": "uniqueness",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "total_headers": len(headers),
            "duplicate_headers": len(duplicate_headers)
        }
    }
