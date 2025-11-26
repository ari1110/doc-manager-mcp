"""Migrate workflow for restructuring existing documentation.

This workflow orchestrates documentation migration:
1. Assesses existing documentation quality
2. Detects current and target platforms
3. Creates new documentation structure
4. Moves/copies files preserving git history (if requested)
5. Updates internal links and references
6. Generates migration report with breaking changes
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import enforce_response_limit, handle_error
from doc_manager_mcp.models import MigrateInput
from doc_manager_mcp.tools.analysis.platform import detect_platform
from doc_manager_mcp.tools.analysis.quality.assessment import assess_quality
from doc_manager_mcp.tools.analysis.validation.validator import validate_docs


def is_git_repo(project_path: Path) -> bool:
    """Check if project is a git repository.

    Args:
        project_path: Project root directory

    Returns:
        True if project has a .git directory
    """
    return (project_path / ".git").exists()


async def migrate(params: MigrateInput) -> str | dict[str, Any]:
    """Migrate existing documentation to new structure.

    Orchestrates documentation restructuring:
    1. Assesses existing documentation quality
    2. Detects current and target platforms
    3. Creates new documentation structure
    4. Moves/copies files preserving git history (if requested)
    5. Updates internal links and references
    6. Generates migration report with breaking changes

    Args:
        params (MigrateInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - existing_docs_path (str): Current docs location (relative)
            - new_docs_path (str): New docs location (default: "docs-new")
            - target_platform (Optional[DocumentationPlatform]): Target platform
            - preserve_history (bool): Use git mv to preserve history (default: True)

    Returns:
        str: Migration report with moved files and breaking changes

    Examples:
        - Use when: Restructuring existing documentation
        - Use when: Migrating to a different documentation platform
        - Use when: Consolidating scattered documentation

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if existing_docs_path doesn't exist
        - Returns error if new_docs_path already exists
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Validate existing docs path
        existing_docs = project_path / params.source_path
        if not existing_docs.exists():
            return enforce_response_limit(f"Error: Existing documentation path does not exist: {existing_docs}")

        # Validate new docs path
        new_docs = project_path / params.target_path
        if new_docs.exists():
            return enforce_response_limit(f"Error: New documentation path already exists: {new_docs}. Please choose a different path or remove the existing directory.")

        lines = ["# Documentation Migration Report", ""]
        lines.append(f"**Project:** {project_path.name}")
        lines.append(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Step 1: Assess existing documentation
        lines.append("## Step 1: Existing Documentation Assessment")
        lines.append("")

        from ...models import AssessQualityInput
        quality_result = await assess_quality(AssessQualityInput(
            project_path=str(project_path),
            docs_path=params.source_path
        ))

        quality_data = quality_result if isinstance(quality_result, dict) else json.loads(quality_result)
        existing_score = quality_data.get("overall_score", "unknown")

        lines.append(f"Existing documentation quality: **{existing_score}**")
        lines.append("")

        # Step 2: Detect platforms
        lines.append("## Step 2: Platform Detection")
        lines.append("")

        from ...models import DetectPlatformInput
        platform_result = await detect_platform(DetectPlatformInput(
            project_path=str(project_path)
        ))

        platform_data = platform_result if isinstance(platform_result, dict) else json.loads(platform_result)
        current_platform = platform_data.get("recommendation", "unknown")
        target_platform = params.target_platform.value if params.target_platform else current_platform

        lines.append(f"Current platform: **{current_platform}**")
        lines.append(f"Target platform: **{target_platform}**")
        lines.append("")

        # Step 3: Create new structure
        step_header = "## Step 3: Creating New Structure"
        if params.dry_run:
            step_header += " (DRY RUN - Preview Only)"
        lines.append(step_header)
        lines.append("")

        moved_files = []
        link_updates_needed = []
        broken_links = []
        links_rewritten = 0
        tocs_generated = 0

        # Process files (sequential if using git, parallel otherwise)
        try:
            # Create target directory if not dry run
            if not params.dry_run:
                new_docs.mkdir(parents=True, exist_ok=False)

            # Determine if we should use git for moves
            use_git = params.preserve_history and is_git_repo(project_path) and not params.dry_run

            # Collect all files to process
            files_to_process = [f for f in existing_docs.rglob("*") if f.is_file()]

            # Process files based on git usage
            if use_git:
                # Sequential processing (git mv must be sequential)
                from .migrate_helpers import process_single_file

                for old_file in files_to_process:
                    result = process_single_file(
                        old_file,
                        existing_docs,
                        new_docs,
                        project_path,
                        rewrite_links_enabled=params.rewrite_links,
                        regenerate_toc=params.regenerate_toc,
                        use_git=use_git,
                        dry_run=params.dry_run
                    )

                    # Accumulate results
                    if result["links_rewritten"]:
                        links_rewritten += 1
                    if result["toc_generated"]:
                        tocs_generated += 1

                    moved_files.append({
                        "old": str(result["old_file"].relative_to(project_path)),
                        "new": str(result["new_file"].relative_to(project_path)),
                        "method": result["method"]
                    })
            else:
                # Parallel processing (3-4x faster for large migrations)
                from .migrate_helpers import process_single_file

                # Create partial function with fixed arguments
                process_func = partial(
                    process_single_file,
                    existing_docs=existing_docs,
                    new_docs=new_docs,
                    project_path=project_path,
                    rewrite_links_enabled=params.rewrite_links,
                    regenerate_toc=params.regenerate_toc,
                    use_git=use_git,
                    dry_run=params.dry_run
                )

                # Process files in parallel with 4 workers
                with ThreadPoolExecutor(max_workers=4) as executor:
                    results = executor.map(process_func, files_to_process)

                    # Accumulate results
                    for result in results:
                        if result["links_rewritten"]:
                            links_rewritten += 1
                        if result["toc_generated"]:
                            tocs_generated += 1

                        moved_files.append({
                            "old": str(result["old_file"].relative_to(project_path)),
                            "new": str(result["new_file"].relative_to(project_path)),
                            "method": result["method"]
                        })

        except Exception as e:
            return enforce_response_limit(f"Error: Failed to migrate documentation: {e}")

        if params.dry_run:
            lines.append(f"Would migrate {len(moved_files)} documentation files (DRY RUN)")
        else:
            lines.append(f"Migrated {len(moved_files)} documentation files")

        if params.rewrite_links:
            lines.append(f"  - Links rewritten in {links_rewritten} markdown files")
        if params.regenerate_toc:
            lines.append(f"  - TOC regenerated in {tocs_generated} markdown files")
        lines.append("")

        # Step 4: Update internal links
        if not params.dry_run:
            lines.append("## Step 4: Link Updates")
            lines.append("")

            # Scan for broken links in new structure
            from ...models import ValidateDocsInput
            validation_result = await validate_docs(ValidateDocsInput(
                project_path=str(project_path),
                docs_path=params.target_path,
                check_links=True,
                check_assets=False,
                check_snippets=False
            ))

            validation_data = validation_result if isinstance(validation_result, dict) else json.loads(validation_result)
            broken_links = [issue for issue in validation_data.get("issues", []) if issue.get("type") == "broken_link"]

            if broken_links:
                lines.append(f"Warning:  Found {len(broken_links)} broken links that need updating")
                link_updates_needed = broken_links[:10]  # Show first 10
                for link in link_updates_needed:
                    lines.append(f"  - {link.get('file')}:{link.get('line')} - {link.get('link_url')}")
                if len(broken_links) > 10:
                    lines.append(f"  ... and {len(broken_links) - 10} more")
            else:
                lines.append("No broken links detected")
            lines.append("")

            # Step 5: Quality assessment of migrated docs
            lines.append("## Step 5: Post-Migration Quality Assessment")
            lines.append("")

            new_quality_result = await assess_quality(AssessQualityInput(
                project_path=str(project_path),
                docs_path=params.target_path
            ))

            new_quality_data = new_quality_result if isinstance(new_quality_result, dict) else json.loads(new_quality_result)
            new_score = new_quality_data.get("overall_score", "unknown")

            lines.append(f"Migrated documentation quality: **{new_score}**")

            if existing_score != new_score:
                lines.append(f"  (Changed from {existing_score})")

            lines.append("")
        else:
            lines.append("## Dry Run Complete")
            lines.append("")
            lines.append("No files were actually modified. Re-run without dry_run to apply changes.")
            lines.append("")

        # Summary
        lines.append("## Migration Summary")
        lines.append("")
        lines.append("**Migration completed successfully!**")
        lines.append("")
        lines.append("**Files Migrated:**")
        lines.append(f"- Total files: {len(moved_files)}")

        git_mv_count = len([f for f in moved_files if f["method"] == "git mv"])
        copy_count = len([f for f in moved_files if f["method"] == "copy"])

        if git_mv_count > 0:
            lines.append(f"- Git history preserved: {git_mv_count} files")
        if copy_count > 0:
            lines.append(f"- Copied: {copy_count} files")

        lines.append("")
        lines.append("**Breaking Changes:**")

        if broken_links:
            lines.append(f"- {len(broken_links)} broken links need manual updates")
        lines.append("")

        # Next steps
        lines.append("## Next Steps")
        lines.append("")
        lines.append("1. **Review migrated content**: Check that all files moved correctly")

        if broken_links:
            lines.append("2. **Update broken links**: Fix internal links to match new structure")

        lines.append("3. **Update references**: Update any external references to old doc paths")
        lines.append("4. **Test new structure**: Ensure documentation builds correctly")
        lines.append(f"5. **Remove old docs**: After verification, remove `{params.source_path}/`")
        lines.append("6. **Update configuration**: Update `.doc-manager.yml` if needed")
        lines.append("")

        lines.append("**Migration Files:**")
        lines.append(f"- Old location: `{params.source_path}/`")
        lines.append(f"- New location: `{params.target_path}/`")

        return {
            "status": "success",
            "message": "Documentation migrated successfully",
            "report": "\n".join(lines),
            "source_path": params.source_path,
            "target_path": params.target_path,
            "target_platform": params.target_platform.value if params.target_platform else target_platform,
            "files_migrated": len(moved_files),
            "broken_links": len(broken_links) if broken_links else 0,
            "steps": {
                "assessment": "completed",
                "platform_detection": "completed",
                "copy": "completed",
                "link_detection": "completed",
                "quality_check": "completed"
            },
            "migrated_files": moved_files
        }
    except Exception as e:
        return enforce_response_limit(handle_error(e, "migrate"))
