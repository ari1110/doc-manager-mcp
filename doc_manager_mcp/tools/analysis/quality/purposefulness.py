"""Purposefulness assessment for documentation quality."""

import re
import sys
from pathlib import Path
from typing import Any


def assess_purposefulness(project_path: Path, docs_path: Path, markdown_files: list[Path]) -> dict[str, Any]:
    """Assess if documents have clear goals and target audiences."""
    issues = []
    findings = []

    # Check for common document types
    doc_types = {
        "tutorial": 0,
        "guide": 0,
        "reference": 0,
        "api": 0,
        "quickstart": 0,
        "getting-started": 0
    }

    for md_file in markdown_files:
        file_name = md_file.name.lower()
        for doc_type in doc_types.keys():
            if doc_type in file_name or doc_type in str(md_file.parent).lower():
                doc_types[doc_type] += 1

    # Check for clear document structure indicators
    files_with_headers = 0
    files_with_toc = 0

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Check for H1 header
            if re.search(r'^# .+', content, re.MULTILINE):
                files_with_headers += 1

            # Check for table of contents
            if re.search(r'(table of contents|toc)', content, re.IGNORECASE):
                files_with_toc += 1

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)

    findings.append(f"Document types found: {', '.join([f'{k}: {v}' for k, v in doc_types.items() if v > 0])}")
    findings.append(f"{files_with_headers}/{len(markdown_files)} files have clear H1 headers")

    if files_with_headers < len(markdown_files) * 0.8:
        issues.append({
            "severity": "warning",
            "message": "Some files missing clear H1 headers - readers may not understand document purpose"
        })

    score = "good" if files_with_headers >= len(markdown_files) * 0.8 else "fair"

    return {
        "criterion": "purposefulness",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "files_with_headers": files_with_headers,
            "files_with_toc": files_with_toc,
            "doc_types": {k: v for k, v in doc_types.items() if v > 0}
        }
    }
