"""Stale reference validation for documentation.

Task 2.2: Use unmatched_references from dependencies.json to detect
references in documentation that couldn't be matched to actual code.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from doc_manager_mcp.schemas.baselines import DependenciesBaseline


def validate_stale_references(
    project_path: Path,
    dependencies: "dict[str, Any] | DependenciesBaseline | None" = None,
) -> list[dict[str, Any]]:
    """Validate documentation for stale/unmatched code references.

    Uses the unmatched_references section from dependencies.json to identify
    references in documentation that couldn't be matched to actual source files.

    Args:
        project_path: Path to project root
        dependencies: Pre-loaded dependencies.json data (optional, will load if not provided)

    Returns:
        List of validation issues for stale references
    """
    issues = []

    # Load dependencies if not provided
    if dependencies is None:
        from doc_manager_mcp.tools._internal.dependencies import load_dependencies
        dependencies = load_dependencies(project_path, validate=False)

    if not dependencies:
        return issues

    # Get unmatched_references from dependencies
    unmatched_refs = dependencies.get("unmatched_references", {}) if isinstance(dependencies, dict) else getattr(dependencies, "unmatched_references", {})

    for reference, doc_files in unmatched_refs.items():
        for doc_file in doc_files:
            issues.append({
                "type": "stale_reference",
                "severity": "warning",
                "file": doc_file,
                "line": 1,  # Line number not available from dependencies.json
                "message": f"Reference `{reference}` could not be matched to any source file",
                "reference": reference,
            })

    return issues


def get_doc_code_coverage(
    project_path: Path,
    dependencies: "dict[str, Any] | DependenciesBaseline | None" = None,
) -> dict[str, Any]:
    """Get code reference coverage metrics for documentation.

    Task 2.1: Use doc_to_code section to analyze code reference density.

    Args:
        project_path: Path to project root
        dependencies: Pre-loaded dependencies.json data (optional)

    Returns:
        Dict with coverage metrics including:
        - total_docs: Number of doc files with code references
        - total_code_refs: Total code file references
        - avg_refs_per_doc: Average code references per doc
        - docs_by_ref_count: Breakdown of docs by reference count
    """
    # Load dependencies if not provided
    if dependencies is None:
        from doc_manager_mcp.tools._internal.dependencies import load_dependencies
        dependencies = load_dependencies(project_path, validate=False)

    if not dependencies:
        return {
            "total_docs": 0,
            "total_code_refs": 0,
            "avg_refs_per_doc": 0.0,
            "docs_by_ref_count": {},
        }

    doc_to_code = dependencies.get("doc_to_code", {}) if isinstance(dependencies, dict) else getattr(dependencies, "doc_to_code", {})

    # Calculate metrics
    total_docs = len(doc_to_code)
    total_code_refs = sum(len(refs) for refs in doc_to_code.values())
    avg_refs = total_code_refs / total_docs if total_docs > 0 else 0.0

    # Breakdown by reference count
    ref_counts = {}
    for doc_file, code_files in doc_to_code.items():
        count = len(code_files)
        bucket = "0" if count == 0 else "1-5" if count <= 5 else "6-10" if count <= 10 else "11+"
        ref_counts[bucket] = ref_counts.get(bucket, 0) + 1

    return {
        "total_docs": total_docs,
        "total_code_refs": total_code_refs,
        "avg_refs_per_doc": round(avg_refs, 1),
        "docs_by_ref_count": ref_counts,
    }
