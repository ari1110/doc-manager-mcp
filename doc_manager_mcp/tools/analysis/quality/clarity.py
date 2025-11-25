"""Clarity assessment for documentation quality."""

import re
import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser

from .helpers import check_terminology_compliance


def assess_clarity(
    project_path: Path,
    docs_path: Path,
    markdown_files: list[Path],
    conventions=None,
    markdown_cache: MarkdownCache | None = None
) -> dict[str, Any]:
    """Assess language precision, examples, and navigation."""
    issues = []
    findings = []

    # Check for navigation aids
    files_with_toc = 0
    files_with_links = 0
    total_internal_links = 0

    # Check for clarity indicators
    total_words = 0
    files_with_examples = 0

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Count words (rough estimate)
            word_count = len(content.split())
            total_words += word_count

            # Check for TOC
            if re.search(r'(table of contents|## contents)', content, re.IGNORECASE):
                files_with_toc += 1

            # Extract links and code blocks using cache or parser
            if markdown_cache:
                parsed = markdown_cache.parse(md_file, content)
                links = parsed.links
                code_blocks = parsed.code_blocks
            else:
                parser = MarkdownParser()
                links = parser.extract_links(content)
                code_blocks = parser.extract_code_blocks(content)

            # Check for internal links
            internal_links = [link for link in links if not link["url"].startswith(('http://', 'https://'))]
            if internal_links:
                files_with_links += 1
                total_internal_links += len(internal_links)

            # Check for examples (code blocks or "example" keyword)
            has_example = len(code_blocks) > 0 or re.search(r'\bexample[s]?\b', content, re.IGNORECASE)
            if has_example:
                files_with_examples += 1

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)

    avg_words = total_words // len(markdown_files) if markdown_files else 0

    findings.append(f"Average document length: {avg_words} words")
    findings.append(f"{files_with_examples}/{len(markdown_files)} files contain examples")
    findings.append(f"{files_with_links}/{len(markdown_files)} files have cross-references")

    if files_with_examples < len(markdown_files) * 0.5:
        issues.append({
            "severity": "warning",
            "message": "Less than 50% of files contain examples - add concrete examples for clarity"
        })

    if files_with_links < 3:
        issues.append({
            "severity": "info",
            "message": "Few cross-references between documents - consider linking related topics"
        })

    # Check terminology compliance if conventions exist
    terminology_issues = []
    if conventions:
        terminology_data = check_terminology_compliance(docs_path, conventions)

        # Report avoided terms found
        avoided_terms = terminology_data.get("avoided_terms_found", [])
        if avoided_terms:
            # Group by term
            terms_summary = {}
            for item in avoided_terms:
                term = item["term"]
                if term not in terms_summary:
                    terms_summary[term] = {"count": 0, "reason": item.get("reason")}
                terms_summary[term]["count"] += 1

            for term, data in terms_summary.items():
                reason_text = f" - {data['reason']}" if data['reason'] else ""
                issues.append({
                    "severity": "warning",
                    "message": f"Found {data['count']} use(s) of '{term}'{reason_text}"
                })
                terminology_issues.append(f"'{term}': {data['count']} occurrences")

    score = "good" if files_with_examples >= len(markdown_files) * 0.5 else "fair"

    return {
        "criterion": "clarity",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "avg_words_per_doc": avg_words,
            "files_with_examples": files_with_examples,
            "files_with_toc": files_with_toc,
            "files_with_links": files_with_links,
            "total_internal_links": total_internal_links
        }
    }
