"""Accuracy assessment for documentation quality."""

import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser

from .helpers import calculate_documentation_coverage


def assess_accuracy(
    project_path: Path,
    docs_path: Path,
    markdown_files: list[Path],
    markdown_cache: MarkdownCache | None = None
) -> dict[str, Any]:
    """Assess if documentation reflects actual codebase and system behavior."""
    issues = []
    findings = []

    # Extract code blocks and check for common issues
    total_code_blocks = 0
    code_blocks_by_lang = {}
    files_with_code = 0

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Find code blocks using cache or parser
            if markdown_cache:
                parsed = markdown_cache.parse(md_file, content)
                code_blocks = parsed.code_blocks
            else:
                parser = MarkdownParser()
                code_blocks = parser.extract_code_blocks(content)

            if code_blocks:
                files_with_code += 1
                total_code_blocks += len(code_blocks)

                for block in code_blocks:
                    lang = block["language"] or "plaintext"
                    code_blocks_by_lang[lang] = code_blocks_by_lang.get(lang, 0) + 1

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)

    if total_code_blocks > 0:
        findings.append(f"Found {total_code_blocks} code blocks across {files_with_code} files")
        findings.append(f"Languages: {', '.join([f'{k} ({v})' for k, v in sorted(code_blocks_by_lang.items())])}")
    else:
        issues.append({
            "severity": "warning",
            "message": "No code examples found - consider adding concrete examples"
        })

    # Calculate documentation coverage
    coverage_data = calculate_documentation_coverage(project_path, docs_path)
    coverage_pct = coverage_data.get("coverage_percentage", 0.0)

    if coverage_pct > 0:
        findings.append(f"API documentation coverage: {coverage_pct}% ({coverage_data['documented_symbols']}/{coverage_data['total_symbols']} public symbols)")

        if coverage_pct < 50:
            issues.append({
                "severity": "warning",
                "message": f"Low API documentation coverage ({coverage_pct}%) - many public symbols are undocumented"
            })
        elif coverage_pct < 80:
            findings.append("API documentation coverage could be improved")

    # Calculate score based on both code examples and API coverage
    score = "good"
    if total_code_blocks == 0 or coverage_pct < 50:
        score = "fair"
    elif coverage_pct >= 80 and total_code_blocks > 10:
        score = "excellent"

    return {
        "criterion": "accuracy",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "total_code_blocks": total_code_blocks,
            "files_with_code": files_with_code,
            "languages": list(code_blocks_by_lang.keys()),
            "api_coverage": coverage_data
        },
        "note": "Full accuracy assessment requires executing code examples and validating outputs"
    }
