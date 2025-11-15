"""Quality assessment tools for doc-manager."""

from pathlib import Path
import re
import sys
from typing import List, Dict, Any, Set
from datetime import datetime

from ..models import AssessQualityInput
from ..constants import ResponseFormat, QualityCriterion
from ..utils import find_docs_directory, handle_error, enforce_response_limit, safe_json_dumps


def _find_markdown_files(docs_path: Path) -> List[Path]:
    """Find all markdown files in documentation directory."""
    markdown_files = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        markdown_files.extend(docs_path.glob(pattern))
    return sorted(markdown_files)


def _assess_relevance(docs_path: Path, markdown_files: List[Path]) -> Dict[str, Any]:
    """Assess if documentation addresses current user needs and use cases."""
    issues = []
    findings = []

    # Check for deprecated/outdated markers
    deprecated_patterns = [
        r'\b(deprecated|obsolete|outdated|legacy|old)\b',
        r'\b(no longer supported|not supported)\b',
        r'\b(removed in|deprecated in)\b'
    ]

    deprecated_count = 0
    files_with_deprecated = []

    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for deprecated markers
            for pattern in deprecated_patterns:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                if matches:
                    deprecated_count += len(matches)
                    if str(md_file) not in files_with_deprecated:
                        files_with_deprecated.append(str(md_file.relative_to(docs_path)))

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)
            pass

    if deprecated_count > 0:
        findings.append(f"Found {deprecated_count} references to deprecated/outdated content across {len(files_with_deprecated)} files")

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
            "message": f"High number of deprecated references ({deprecated_count}) - consider removing or updating outdated content"
        })
    elif deprecated_count > 5:
        findings.append("Some deprecated content found - ensure it's clearly marked with migration guidance")

    return {
        "criterion": "relevance",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "deprecated_references": deprecated_count,
            "files_with_deprecated": len(files_with_deprecated),
            "has_readme": has_readme
        }
    }


def _assess_accuracy(docs_path: Path, markdown_files: List[Path]) -> Dict[str, Any]:
    """Assess if documentation reflects actual codebase and system behavior."""
    issues = []
    findings = []

    # Extract code blocks and check for common issues
    total_code_blocks = 0
    code_blocks_by_lang = {}
    files_with_code = 0

    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find code blocks
            code_block_pattern = r'```(\w+)?\n(.*?)\n```'
            matches = list(re.finditer(code_block_pattern, content, re.DOTALL))

            if matches:
                files_with_code += 1
                total_code_blocks += len(matches)

                for match in matches:
                    lang = match.group(1) or "plaintext"
                    code_blocks_by_lang[lang] = code_blocks_by_lang.get(lang, 0) + 1

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)
            pass

    if total_code_blocks > 0:
        findings.append(f"Found {total_code_blocks} code blocks across {files_with_code} files")
        findings.append(f"Languages: {', '.join([f'{k} ({v})' for k, v in sorted(code_blocks_by_lang.items())])}")
    else:
        issues.append({
            "severity": "warning",
            "message": "No code examples found - consider adding concrete examples"
        })

    # Note: Full accuracy validation requires running code examples
    # This is a simplified assessment
    score = "good" if total_code_blocks > 0 else "fair"

    return {
        "criterion": "accuracy",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "total_code_blocks": total_code_blocks,
            "files_with_code": files_with_code,
            "languages": list(code_blocks_by_lang.keys())
        },
        "note": "Full accuracy assessment requires executing code examples and validating outputs"
    }


def _assess_purposefulness(docs_path: Path, markdown_files: List[Path]) -> Dict[str, Any]:
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
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for H1 header
            if re.search(r'^# .+', content, re.MULTILINE):
                files_with_headers += 1

            # Check for table of contents
            if re.search(r'(table of contents|toc)', content, re.IGNORECASE):
                files_with_toc += 1

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)
            pass

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


def _assess_uniqueness(docs_path: Path, markdown_files: List[Path]) -> Dict[str, Any]:
    """Assess if there's redundant or duplicate information."""
    issues = []
    findings = []

    # Extract all H1 and H2 headers to check for duplicates
    headers = {}

    for md_file in markdown_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find H1 and H2 headers
            h1_pattern = r'^# (.+)$'
            h2_pattern = r'^## (.+)$'

            for match in re.finditer(h1_pattern, content, re.MULTILINE):
                header_text = match.group(1).strip().lower()
                if header_text not in headers:
                    headers[header_text] = []
                headers[header_text].append(str(md_file.relative_to(docs_path)))

            for match in re.finditer(h2_pattern, content, re.MULTILINE):
                header_text = match.group(1).strip().lower()
                if header_text not in headers:
                    headers[header_text] = []
                headers[header_text].append(str(md_file.relative_to(docs_path)))

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)
            pass

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


def _assess_consistency(docs_path: Path, markdown_files: List[Path]) -> Dict[str, Any]:
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
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check code block language tags
            code_block_pattern = r'```(\w+)?'
            for match in re.finditer(code_block_pattern, content):
                lang = match.group(1)
                if lang:
                    code_langs_with_backticks.add(lang)
                else:
                    code_langs_without_lang += 1

            # Check heading styles
            atx_style_count += len(re.findall(r'^#{1,6} ', content, re.MULTILINE))
            setext_style_count += len(re.findall(r'^.+\n[=\-]+$', content, re.MULTILINE))

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)
            pass

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


def _assess_clarity(docs_path: Path, markdown_files: List[Path]) -> Dict[str, Any]:
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
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Count words (rough estimate)
            word_count = len(content.split())
            total_words += word_count

            # Check for TOC
            if re.search(r'(table of contents|## contents)', content, re.IGNORECASE):
                files_with_toc += 1

            # Check for internal links
            link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
            links = re.findall(link_pattern, content)
            internal_links = [l for l in links if not l[1].startswith(('http://', 'https://'))]
            if internal_links:
                files_with_links += 1
                total_internal_links += len(internal_links)

            # Check for examples (code blocks or "example" keyword)
            has_example = '```' in content or re.search(r'\bexample[s]?\b', content, re.IGNORECASE)
            if has_example:
                files_with_examples += 1

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)
            pass

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


def _assess_structure(docs_path: Path, markdown_files: List[Path]) -> Dict[str, Any]:
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
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract all headings with their levels
            heading_pattern = r'^(#{1,6}) (.+)$'
            headings = []
            for match in re.finditer(heading_pattern, content, re.MULTILINE):
                level = len(match.group(1))
                headings.append(level)
                max_heading_depth = max(max_heading_depth, level)

            # Check for heading hierarchy issues (skipping levels)
            for i in range(len(headings) - 1):
                if headings[i+1] > headings[i] + 1:
                    heading_issues += 1
                    break  # Count once per file

        except Exception as e:
            print(f"Warning: Failed to read file {md_file}: {e}", file=sys.stderr)
            pass

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

    findings.append(f"Maximum heading depth: H{max_heading_depth}")
    findings.append(f"Files organized in {len(subdirs)} subdirectories")

    score = "good" if heading_issues < 3 and max_heading_depth <= 4 else "fair"

    return {
        "criterion": "structure",
        "score": score,
        "findings": findings,
        "issues": issues,
        "metrics": {
            "subdirectories": len(subdirs),
            "max_heading_depth": max_heading_depth,
            "files_with_hierarchy_issues": heading_issues
        }
    }


def _format_quality_report(results: List[Dict[str, Any]], response_format: ResponseFormat) -> str:
    """Format quality assessment report."""
    if response_format == ResponseFormat.JSON:
        return enforce_response_limit(safe_json_dumps({
            "assessed_at": datetime.now().isoformat(),
            "overall_score": _calculate_overall_score(results),
            "criteria": results
        }, indent=2))
    else:
        lines = ["# Documentation Quality Assessment Report", ""]
        lines.append(f"**Assessed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Overall Score:** {_calculate_overall_score(results)}")
        lines.append("")

        # Summary by score
        scores = {}
        for result in results:
            score = result['score']
            scores[score] = scores.get(score, 0) + 1

        lines.append("## Score Summary")
        for score in ['excellent', 'good', 'fair', 'poor']:
            if score in scores:
                lines.append(f"- **{score.capitalize()}**: {scores[score]} criteria")
        lines.append("")

        # Detailed results per criterion
        for result in results:
            lines.append(f"## {result['criterion'].capitalize()}")
            lines.append(f"**Score:** {result['score'].upper()}")
            lines.append("")

            if result.get('findings'):
                lines.append("**Findings:**")
                for finding in result['findings']:
                    lines.append(f"- {finding}")
                lines.append("")

            if result.get('issues'):
                lines.append("**Issues:**")
                for issue in result['issues']:
                    severity_emoji = "⚠️" if issue['severity'] == 'warning' else "ℹ️"
                    lines.append(f"- {severity_emoji} {issue['message']}")
                lines.append("")

            if result.get('note'):
                lines.append(f"*Note: {result['note']}*")
                lines.append("")

        return enforce_response_limit("\n".join(lines))


def _calculate_overall_score(results: List[Dict[str, Any]]) -> str:
    """Calculate overall quality score from individual criteria."""
    score_values = {'excellent': 4, 'good': 3, 'fair': 2, 'poor': 1}
    total = sum(score_values.get(r['score'], 2) for r in results)
    avg = total / len(results) if results else 2

    if avg >= 3.5:
        return "excellent"
    elif avg >= 2.5:
        return "good"
    elif avg >= 1.5:
        return "fair"
    else:
        return "poor"


async def assess_quality(params: AssessQualityInput) -> str:
    """Assess documentation quality against 7 criteria.

    Evaluates documentation against:
    1. Relevance - Addresses current user needs and use cases
    2. Accuracy - Reflects actual codebase state
    3. Purposefulness - Clear goals and target audience
    4. Uniqueness - No redundant or conflicting information
    5. Consistency - Aligned terminology, formatting, and style
    6. Clarity - Precise language and intuitive navigation
    7. Structure - Logical organization with appropriate depth

    Args:
        params (AssessQualityInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - docs_path (Optional[str]): Relative path to docs directory
            - criteria (Optional[List[QualityCriterion]]): Specific criteria to assess
            - response_format (ResponseFormat): Output format (markdown or json)

    Returns:
        str: Quality assessment report with scores and findings

    Examples:
        - Use when: Auditing documentation quality
        - Use when: Before major releases
        - Use when: After significant documentation changes

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if docs_path specified but not found
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Determine docs directory
        if params.docs_path:
            docs_path = project_path / params.docs_path
            if not docs_path.exists():
                return enforce_response_limit(f"Error: Documentation path does not exist: {docs_path}")
        else:
            docs_path = find_docs_directory(project_path)
            if not docs_path:
                return enforce_response_limit("Error: Could not find documentation directory. Please specify docs_path parameter.")

        if not docs_path.is_dir():
            return enforce_response_limit(f"Error: Documentation path is not a directory: {docs_path}")

        # Find all markdown files
        markdown_files = _find_markdown_files(docs_path)
        if not markdown_files:
            return enforce_response_limit(f"Error: No markdown files found in {docs_path}")

        # Determine which criteria to assess
        criteria_to_assess = params.criteria or [
            QualityCriterion.RELEVANCE,
            QualityCriterion.ACCURACY,
            QualityCriterion.PURPOSEFULNESS,
            QualityCriterion.UNIQUENESS,
            QualityCriterion.CONSISTENCY,
            QualityCriterion.CLARITY,
            QualityCriterion.STRUCTURE
        ]

        # Run assessments
        results = []

        for criterion in criteria_to_assess:
            if criterion == QualityCriterion.RELEVANCE:
                results.append(_assess_relevance(docs_path, markdown_files))
            elif criterion == QualityCriterion.ACCURACY:
                results.append(_assess_accuracy(docs_path, markdown_files))
            elif criterion == QualityCriterion.PURPOSEFULNESS:
                results.append(_assess_purposefulness(docs_path, markdown_files))
            elif criterion == QualityCriterion.UNIQUENESS:
                results.append(_assess_uniqueness(docs_path, markdown_files))
            elif criterion == QualityCriterion.CONSISTENCY:
                results.append(_assess_consistency(docs_path, markdown_files))
            elif criterion == QualityCriterion.CLARITY:
                results.append(_assess_clarity(docs_path, markdown_files))
            elif criterion == QualityCriterion.STRUCTURE:
                results.append(_assess_structure(docs_path, markdown_files))

        return enforce_response_limit(_format_quality_report(results, params.response_format))

    except Exception as e:
        return enforce_response_limit(handle_error(e, "assess_quality"))
