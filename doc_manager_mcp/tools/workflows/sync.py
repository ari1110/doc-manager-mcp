"""Sync workflow for keeping documentation aligned with code changes.

This workflow orchestrates documentation synchronization with two modes:
- mode="check": Read-only analysis (detects changes, no baseline updates)
- mode="resync": Full sync (detects changes + updates baselines atomically)

Steps performed:
1. Maps code changes to affected documentation
2. Identifies documentation that needs updates
3. Validates current documentation state
4. Assesses documentation quality
5. Updates baselines (only if mode="resync")
6. Generates sync report with actionable recommendations
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    enforce_response_limit,
    get_convention_summary,
    handle_error,
    load_config,
    load_conventions,
)
from doc_manager_mcp.models import SyncInput
from doc_manager_mcp.tools.analysis.detect_changes import docmgr_detect_changes
from doc_manager_mcp.tools.analysis.quality.assessment import assess_quality
from doc_manager_mcp.tools.analysis.validation.validator import validate_docs


async def sync(params: SyncInput) -> dict[str, Any] | str:
    """Sync documentation with code changes.

    Orchestrates documentation synchronization with two modes:
    - mode="check": Read-only analysis (detects changes, no baseline updates)
    - mode="resync": Full sync (detects changes + updates baselines atomically)

    Steps performed:
    1. Maps code changes to affected documentation
    2. Identifies documentation that needs updates
    3. Validates current documentation state
    4. Assesses documentation quality
    5. Updates baselines (only if mode="resync")
    6. Generates sync report with actionable recommendations

    Args:
        params (SyncInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - mode (str): "check" (read-only) or "resync" (update baselines)
            - docs_path (str): Documentation directory path
            - response_format (ResponseFormat): Output format

    Returns:
        dict: Sync report with affected docs, recommendations, and baseline status

    Examples:
        - Use when: After making code changes (mode="check" to analyze impact)
        - Use when: After updating docs (mode="resync" to update baselines)
        - Use when: Running in CI/CD to detect doc staleness (mode="check")

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if memory baseline not found
        - Returns info if no changes detected
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Load conventions and config if they exist
        conventions = load_conventions(project_path)
        config = load_config(project_path)
        include_root_readme = config.get('include_root_readme', False) if config else False

        lines = ["# Documentation Sync Report", ""]
        lines.append(f"**Project:** {project_path.name}")
        lines.append(f"**Mode:** {params.mode} ({'read-only analysis' if params.mode == 'check' else 'baseline update + analysis'})")
        lines.append(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Add conventions summary if they exist
        if conventions:
            lines.append("")
            lines.append("**Documentation Conventions:**")
            convention_summary = get_convention_summary(conventions)
            for line in convention_summary.split("\n"):
                lines.append(line)

        lines.append("")

        # Check if baseline exists
        baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"
        if not baseline_path.exists():
            return enforce_response_limit("Error: No baseline found. Please run docmgr_init first to establish a baseline for change detection.")

        # Step 1: Update baselines FIRST if mode="resync"
        baseline_updated = False
        step_offset = 0
        if params.mode == "resync":
            lines.append("## Step 1: Updating Baselines")
            lines.append("")

            from doc_manager_mcp.models import DocmgrUpdateBaselineInput
            from doc_manager_mcp.tools.state.update_baseline import docmgr_update_baseline

            baseline_result = await docmgr_update_baseline(
                DocmgrUpdateBaselineInput(
                    project_path=str(project_path),
                    docs_path=params.docs_path
                )
            )

            if baseline_result.get("status") == "success":
                updated_files = baseline_result.get("updated_files", [])
                lines.append(f"Successfully updated {len(updated_files)} baseline files:")
                for file in updated_files:
                    lines.append(f"  - {file}")
                baseline_updated = True
            else:
                lines.append(f"Warning: Baseline update failed: {baseline_result.get('message', 'Unknown error')}")

            lines.append("")
            step_offset = 1

        # Step 1/2: Change detection (against fresh baseline if resync)
        lines.append(f"## Step {1 + step_offset}: Change Detection")
        lines.append("")

        from doc_manager_mcp.constants import ChangeDetectionMode
        from doc_manager_mcp.models import DocmgrDetectChangesInput
        changes_result = await docmgr_detect_changes(DocmgrDetectChangesInput(
            project_path=str(project_path),
            mode=ChangeDetectionMode.CHECKSUM
        ))

        changes_data = changes_result if isinstance(changes_result, dict) else json.loads(changes_result)
        changes_detected = changes_data.get("changes_detected", False)
        total_changes = changes_data.get("total_changes", 0)
        affected_docs = changes_data.get("affected_documentation", [])

        if not changes_detected:
            lines.append("No changes detected")
            lines.append("  (Baseline is current with codebase)")
        else:
            lines.append(f"Warning:  Detected {total_changes} code changes")
        lines.append("")

        # Step 2/3: Identify affected documentation
        lines.append(f"## Step {2 + step_offset}: Affected Documentation")
        lines.append("")

        if not affected_docs:
            lines.append("No documentation impacts detected")
            lines.append("  (Changes only affected tests, infrastructure, or docs themselves)")
            lines.append("")

        from doc_manager_mcp.core import find_docs_directory
        from doc_manager_mcp.models import AssessQualityInput, ValidateDocsInput

        # Use provided docs_path or auto-detect
        if params.docs_path:
            docs_path = project_path / params.docs_path
        else:
            docs_path = find_docs_directory(project_path)

        # Initialize metrics
        total_issues: int | None = None
        overall_score: str | None = None

        # Step 3/4: Run validation and quality assessment in parallel
        if docs_path and docs_path.exists():
            # Create tasks for parallel execution
            validation_task = validate_docs(ValidateDocsInput(
                project_path=str(project_path),
                docs_path=str(docs_path.relative_to(project_path)),
                include_root_readme=include_root_readme
            ))

            quality_task = assess_quality(AssessQualityInput(
                project_path=str(project_path),
                docs_path=str(docs_path.relative_to(project_path)),
                include_root_readme=include_root_readme
            ))

            # Run both tasks concurrently
            validation_result, quality_result = await asyncio.gather(
                validation_task,
                quality_task
            )

            # Process validation results
            lines.append(f"## Step {3 + step_offset}: Current Documentation Status")
            lines.append("")

            validation_data = validation_result if isinstance(validation_result, dict) else json.loads(validation_result)
            total_issues = validation_data.get("total_issues", 0)
            errors = validation_data.get("errors", 0)
            warnings = validation_data.get("warnings", 0)

            if total_issues == 0:
                lines.append("No validation issues found")
            else:
                lines.append(f"Warning:  Found {total_issues} validation issues:")
                lines.append(f"  - Errors: {errors}")
                lines.append(f"  - Warnings: {warnings}")
            lines.append("")

            # Process quality results
            lines.append(f"## Step {4 + step_offset}: Quality Assessment")
            lines.append("")

            quality_data = quality_result if isinstance(quality_result, dict) else json.loads(quality_result)
            overall_score = quality_data.get("overall_score", "unknown")

            lines.append(f"**Overall Quality:** {overall_score}")

            # Show specific criteria that need attention
            criteria = quality_data.get("criteria", [])
            low_scores = [c for c in criteria if c.get("score") in ["fair", "poor"]]

            if low_scores:
                lines.append("")
                lines.append("**Areas Needing Attention:**")
                for criterion in low_scores:
                    lines.append(f"- {criterion['criterion'].capitalize()}: {criterion['score']}")

            lines.append("")
        else:
            # No docs found - report separately for validation and quality
            lines.append(f"## Step {3 + step_offset}: Current Documentation Status")
            lines.append("")
            lines.append("No documentation directory found")
            lines.append("")

            lines.append(f"## Step {4 + step_offset}: Quality Assessment")
            lines.append("")
            lines.append("No documentation directory found")
            lines.append("")

        # Step 5/6: Recommendations
        lines.append(f"## Step {5 + step_offset}: Recommendations")
        lines.append("")

        if affected_docs:
            lines.append("**Affected Documentation:**")
            lines.append("")
            for doc in affected_docs[:10]:
                lines.append(f"- {doc['file']} (Priority: {doc.get('priority', 'medium')})")

            if len(affected_docs) > 10:
                lines.append(f"  ... and {len(affected_docs) - 10} more")

            lines.append("")
            lines.append("**Recommended Actions:**")
            lines.append("1. Review and update affected documentation")
            lines.append("2. Check that examples still work")
            lines.append("3. Update screenshots if UI changed")
            lines.append("4. Verify configuration examples")
            lines.append("")

        if params.mode == "check":
            lines.append("**Next Steps:**")
            lines.append("- After updating docs, run sync with mode='resync' to update baselines")
            lines.append("- Or use docmgr_update_baseline to explicitly update baselines")
        elif params.mode == "resync" and baseline_updated:
            lines.append("**Baseline Status:**")
            lines.append("- All baselines updated successfully")
            lines.append("- Documentation is now in sync with current codebase")

        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"**Code Changes:** {total_changes} files modified")
        lines.append(f"**Documentation Impact:** {len(affected_docs)} files affected")

        if docs_path:
            lines.append(f"**Validation Issues:** {total_issues if total_issues is not None else 'N/A'}")
            lines.append(f"**Quality Score:** {overall_score if overall_score is not None else 'N/A'}")

        if params.mode == "resync":
            lines.append(f"**Baselines Updated:** {'Yes' if baseline_updated else 'No'}")

        return {
            "status": "success",
            "message": f"Sync {'analysis' if params.mode == 'check' else 'and baseline update'} completed",
            "mode": params.mode,
            "report": "\n".join(lines),
            "changes": total_changes,
            "affected_docs": len(affected_docs),
            "recommendations": [doc["file"] for doc in affected_docs[:10]],
            "validation_issues": total_issues,
            "quality_score": overall_score,
            "baseline_updated": baseline_updated if params.mode == "resync" else None
        }
    except Exception as e:
        return enforce_response_limit(handle_error(e, "sync"))
