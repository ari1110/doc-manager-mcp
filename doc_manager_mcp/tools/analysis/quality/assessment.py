"""Quality assessment tools for doc-manager."""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from doc_manager_mcp.constants import QualityCriterion
from doc_manager_mcp.core import (
    enforce_response_limit,
    find_docs_directory,
    find_markdown_files,
    get_doc_relative_path,
    handle_error,
    load_config,
    load_conventions,
)
from doc_manager_mcp.indexing.parsers.markdown import MarkdownParser
from doc_manager_mcp.models import AssessQualityInput

from .helpers import (
    calculate_documentation_coverage,
    check_heading_case_consistency,
    check_list_formatting_consistency,
    check_terminology_compliance,
    detect_multiple_h1s,
    detect_undocumented_apis,
)


def _assess_relevance(project_path: Path, docs_path: Path, markdown_files: list[Path]) -> dict[str, Any]:
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
            content_without_code = _remove_code_blocks(content)

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
        findings.append(f"Found {int(round(deprecated_count))} references to deprecated/outdated content across {len(files_with_deprecated)} files")

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
            "message": f"High number of deprecated references ({int(round(deprecated_count))}) - consider removing or updating outdated content"
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
            "deprecated_references": int(round(deprecated_count)),
            "files_with_deprecated": len(files_with_deprecated),
            "has_readme": has_readme
        }
    }


def _assess_accuracy(project_path: Path, docs_path: Path, markdown_files: list[Path]) -> dict[str, Any]:
    """Assess if documentation reflects actual codebase and system behavior."""
    issues = []
    findings = []
    parser = MarkdownParser()

    # Extract code blocks and check for common issues
    total_code_blocks = 0
    code_blocks_by_lang = {}
    files_with_code = 0

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Find code blocks using MarkdownParser
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


def _assess_purposefulness(project_path: Path, docs_path: Path, markdown_files: list[Path]) -> dict[str, Any]:
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


def _remove_code_blocks(content: str) -> str:
    """Remove fenced code blocks from content to avoid false positives."""
    # Simple regex removal is fine for this use case (no need for line numbers)
    code_block_pattern = r'^```.*?^```'
    return re.sub(code_block_pattern, '', content, flags=re.MULTILINE | re.DOTALL)


def _assess_uniqueness(project_path: Path, docs_path: Path, markdown_files: list[Path]) -> dict[str, Any]:
    """Assess if there's redundant or duplicate information."""
    issues = []
    findings = []
    parser = MarkdownParser()

    # Extract all H1 and H2 headers to check for duplicates
    headers = {}

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Extract headers using MarkdownParser
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


def _assess_consistency(project_path: Path, docs_path: Path, markdown_files: list[Path], conventions=None) -> dict[str, Any]:
    """Assess terminology, formatting, and style consistency."""
    issues = []
    findings = []
    parser = MarkdownParser()

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

            # Check code block language tags using MarkdownParser
            # This correctly counts only actual code blocks (not closing fences)
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


def _assess_clarity(project_path: Path, docs_path: Path, markdown_files: list[Path], conventions=None) -> dict[str, Any]:
    """Assess language precision, examples, and navigation."""
    issues = []
    findings = []
    parser = MarkdownParser()

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

            # Check for internal links using MarkdownParser
            links = parser.extract_links(content)
            internal_links = [link for link in links if not link["url"].startswith(('http://', 'https://'))]
            if internal_links:
                files_with_links += 1
                total_internal_links += len(internal_links)

            # Check for examples (code blocks or "example" keyword)
            code_blocks = parser.extract_code_blocks(content)
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


def _assess_structure(project_path: Path, docs_path: Path, markdown_files: list[Path]) -> dict[str, Any]:
    """Assess logical organization and hierarchy."""
    issues = []
    findings = []
    parser = MarkdownParser()

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

            # Extract all headings using MarkdownParser
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


def _format_quality_report(
    results: list[dict[str, Any]],
    undocumented_apis: list[dict[str, Any]] | None = None,
    coverage_data: dict[str, Any] | None = None,
    list_formatting: dict[str, Any] | None = None,
    heading_case: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Format quality assessment report."""
    report = {
        "assessed_at": datetime.now().isoformat(),
        "overall_score": _calculate_overall_score(results, coverage_data),
        "criteria": results
    }

    # Add documentation coverage if provided
    if coverage_data is not None:
        report["coverage"] = coverage_data

    # Add undocumented APIs if provided
    if undocumented_apis is not None:
        report["undocumented_apis"] = {
            "count": len(undocumented_apis),
            "symbols": undocumented_apis[:50]  # Limit to first 50 for readability
        }

    # Add list formatting consistency if provided
    if list_formatting is not None:
        report["list_formatting"] = list_formatting

    # Add heading case consistency if provided
    if heading_case is not None:
        report["heading_case"] = heading_case

    return report

def _calculate_overall_score(results: list[dict[str, Any]], coverage_data: dict[str, Any] | None = None) -> str:
    """Calculate overall quality score from individual criteria and coverage."""
    score_values = {'excellent': 4, 'good': 3, 'fair': 2, 'poor': 1}

    # Validate and sum scores with explicit logging for invalid values
    total = 0
    count = 0
    for r in results:
        score = r.get('score', '')
        if score not in score_values:
            criterion = r.get('criterion', 'unknown')
            print(f"Warning: Invalid quality score '{score}' for {criterion}, using default 2 (fair)", file=sys.stderr)
            total += 2
        else:
            total += score_values[score]
        count += 1

    # Factor in coverage percentage if available
    if coverage_data and 'coverage_percentage' in coverage_data:
        coverage_pct = coverage_data['coverage_percentage']
        # Map coverage percentage to score (0-100% -> 1-4)
        # <30%: poor (1), 30-50%: fair (2), 50-75%: good (3), >75%: excellent (4)
        if coverage_pct >= 75:
            coverage_score = 4
        elif coverage_pct >= 50:
            coverage_score = 3
        elif coverage_pct >= 30:
            coverage_score = 2
        else:
            coverage_score = 1

        total += coverage_score
        count += 1

    avg = total / count if count > 0 else 2

    if avg >= 3.5:
        return "excellent"
    elif avg >= 2.5:
        return "good"
    elif avg >= 1.5:
        return "fair"
    else:
        return "poor"


async def assess_quality(params: AssessQualityInput) -> str | dict[str, Any]:
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

        # Load config and get include_root_readme setting
        config = load_config(project_path)
        include_root_readme = config.get('include_root_readme', False) if config else False

        # Find all markdown files
        markdown_files = find_markdown_files(
            docs_path,
            project_path=project_path,
            validate_boundaries=False,
            include_root_readme=include_root_readme
        )
        if not markdown_files:
            return enforce_response_limit(f"Error: No markdown files found in {docs_path}")

        # Load documentation conventions (if they exist)
        conventions = load_conventions(project_path)

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
                results.append(_assess_relevance(project_path, docs_path, markdown_files))
            elif criterion == QualityCriterion.ACCURACY:
                results.append(_assess_accuracy(project_path, docs_path, markdown_files))
            elif criterion == QualityCriterion.PURPOSEFULNESS:
                results.append(_assess_purposefulness(project_path, docs_path, markdown_files))
            elif criterion == QualityCriterion.UNIQUENESS:
                results.append(_assess_uniqueness(project_path, docs_path, markdown_files))
            elif criterion == QualityCriterion.CONSISTENCY:
                results.append(_assess_consistency(project_path, docs_path, markdown_files, conventions))
            elif criterion == QualityCriterion.CLARITY:
                results.append(_assess_clarity(project_path, docs_path, markdown_files, conventions))
            elif criterion == QualityCriterion.STRUCTURE:
                results.append(_assess_structure(project_path, docs_path, markdown_files))

        # Calculate documentation coverage
        coverage_data = calculate_documentation_coverage(project_path, docs_path)

        # Detect undocumented APIs
        undocumented_apis = detect_undocumented_apis(project_path, docs_path)

        # Check formatting consistency
        list_formatting = check_list_formatting_consistency(docs_path)
        heading_case = check_heading_case_consistency(docs_path)

        return enforce_response_limit(_format_quality_report(
            results,
            undocumented_apis,
            coverage_data,
            list_formatting,
            heading_case
        ))

    except Exception as e:
        return enforce_response_limit(handle_error(e, "assess_quality"))
