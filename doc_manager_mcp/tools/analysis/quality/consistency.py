"""Consistency assessment for documentation quality."""

import re
import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser


def assess_consistency(
    project_path: Path,
    docs_path: Path,
    markdown_files: list[Path],
    conventions=None,
    markdown_cache: MarkdownCache | None = None
) -> dict[str, Any]:
    """Assess terminology, formatting, and style consistency."""
    issues = []
    findings = []

    # Check code block language consistency
    code_langs_with_backticks = set()
    code_langs_without_lang = 0

    # Check heading style consistency
    atx_style_count = 0  # # Header
    setext_style_count = 0  # Header\n=====

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Check code block language tags using cache or parser
            # This correctly counts only actual code blocks (not closing fences)
            if markdown_cache:
                parsed = markdown_cache.parse(md_file, content)
                code_blocks = parsed.code_blocks
            else:
                parser = MarkdownParser()
                code_blocks = parser.extract_code_blocks(content)
            for block in code_blocks:
                lang = block['language']
                # Filter out "plaintext" from language count (Bug #3 fix)
                if lang and lang != "plaintext":
                    code_langs_with_backticks.add(lang)
                else:
                    code_langs_without_lang += 1

            # Check heading styles
            atx_style_count += len(re.findall(r'^#{1,6} ', content, re.MULTILINE))
            setext_style_count += len(re.findall(r'^.+\n[=\-]+$', content, re.MULTILINE))

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)

    if code_langs_without_lang > 0:
        issues.append({
            "severity": "warning",
            "message": f"{code_langs_without_lang} code blocks missing language tags - add language for syntax highlighting"
        })

    if atx_style_count > 0 and setext_style_count > 0:
        issues.append({
            "severity": "info",
            "message": f"Mixed heading styles: {atx_style_count} ATX-style (#), {setext_style_count} Setext-style (===). Consider standardizing on ATX-style."
        })

    findings.append(f"Code block languages used: {', '.join(sorted(code_langs_with_backticks))}")
    findings.append(f"Heading style: {atx_style_count} ATX, {setext_style_count} Setext")

    score = "good" if code_langs_without_lang < 5 and setext_style_count == 0 else "fair"

    return {
        "criterion": "consistency",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "code_blocks_without_lang": code_langs_without_lang,
            "languages_used": len(code_langs_with_backticks),
            "atx_headings": atx_style_count,
            "setext_headings": setext_style_count
        }
    }
