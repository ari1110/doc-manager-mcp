"""Quality assessment tools for doc-manager."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from doc_manager_mcp.constants import QualityCriterion
from doc_manager_mcp.core import (
    enforce_response_limit,
    find_docs_directory,
    find_markdown_files,
    handle_error,
    load_config,
    load_conventions,
)
from doc_manager_mcp.core.markdown_cache import MarkdownCache
from doc_manager_mcp.models import AssessQualityInput
from doc_manager_mcp.tools._internal.baselines import load_repo_baseline

from .accuracy import assess_accuracy
from .clarity import assess_clarity
from .consistency import assess_consistency
from .helpers import (
    calculate_docstring_coverage,
    calculate_documentation_coverage,
    check_heading_case_consistency,
    check_list_formatting_consistency,
    detect_undocumented_apis,
)
from .purposefulness import assess_purposefulness
from .relevance import assess_relevance
from .structure import assess_structure
from .uniqueness import assess_uniqueness


def _format_quality_report(
    results: list[dict[str, Any]],
    undocumented_apis: list[dict[str, Any]] | None = None,
    coverage_data: dict[str, Any] | None = None,
    list_formatting: dict[str, Any] | None = None,
    heading_case: dict[str, Any] | None = None,
    project_context: dict[str, Any] | None = None,  # Task 1.3: Include project context
    docstring_coverage: dict[str, Any] | None = None,  # Task 3.3: Include docstring coverage
) -> dict[str, Any]:
    """Format quality assessment report."""
    report = {
        "assessed_at": datetime.now().isoformat(),
        "overall_score": _calculate_overall_score(results, coverage_data),
        "criteria": results
    }

    # Task 1.3: Add project context (repo_name, description, language) to report
    if project_context:
        report["project"] = project_context

    # Task 3.3: Add docstring coverage metric
    if docstring_coverage:
        report["docstring_coverage"] = docstring_coverage

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

        # Create markdown cache for performance (eliminates redundant parsing)
        markdown_cache = MarkdownCache()

        # Run assessments in parallel (2-3x faster)
        analyzers = []

        for criterion in criteria_to_assess:
            if criterion == QualityCriterion.RELEVANCE:
                analyzers.append(
                    asyncio.to_thread(assess_relevance, project_path, docs_path, markdown_files)
                )
            elif criterion == QualityCriterion.ACCURACY:
                analyzers.append(
                    asyncio.to_thread(assess_accuracy, project_path, docs_path, markdown_files, markdown_cache)
                )
            elif criterion == QualityCriterion.PURPOSEFULNESS:
                analyzers.append(
                    asyncio.to_thread(assess_purposefulness, project_path, docs_path, markdown_files)
                )
            elif criterion == QualityCriterion.UNIQUENESS:
                analyzers.append(
                    asyncio.to_thread(assess_uniqueness, project_path, docs_path, markdown_files, markdown_cache)
                )
            elif criterion == QualityCriterion.CONSISTENCY:
                analyzers.append(
                    asyncio.to_thread(assess_consistency, project_path, docs_path, markdown_files, conventions, markdown_cache)
                )
            elif criterion == QualityCriterion.CLARITY:
                analyzers.append(
                    asyncio.to_thread(assess_clarity, project_path, docs_path, markdown_files, conventions, markdown_cache)
                )
            elif criterion == QualityCriterion.STRUCTURE:
                analyzers.append(
                    asyncio.to_thread(assess_structure, project_path, docs_path, markdown_files, markdown_cache)
                )

        # Run all analyzers concurrently
        results = await asyncio.gather(*analyzers) if analyzers else []

        # Calculate documentation coverage and other metadata
        coverage_data = calculate_documentation_coverage(project_path, docs_path)
        undocumented_apis = detect_undocumented_apis(project_path, docs_path)
        list_formatting = check_list_formatting_consistency(docs_path)
        heading_case = check_heading_case_consistency(docs_path)

        # Task 3.3: Calculate docstring coverage from symbol baseline
        docstring_coverage = calculate_docstring_coverage(project_path)

        # Task 1.3: Load project context from repo baseline
        project_context = None
        repo_baseline_data = load_repo_baseline(project_path, validate=False)
        if isinstance(repo_baseline_data, dict):
            project_context = {
                "repo_name": repo_baseline_data.get("repo_name"),
                "description": repo_baseline_data.get("description"),
                "language": repo_baseline_data.get("language"),
            }

        return enforce_response_limit(_format_quality_report(
            results,
            undocumented_apis,
            coverage_data,
            list_formatting,
            heading_case,
            project_context,
            docstring_coverage,
        ))

    except Exception as e:
        return enforce_response_limit(handle_error(e, "assess_quality"))
