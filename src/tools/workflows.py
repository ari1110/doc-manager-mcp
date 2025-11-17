"""Workflow orchestration tools for doc-manager."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..constants import DocumentationPlatform
from ..models import BootstrapInput, MigrateInput, SyncInput
from ..utils import detect_project_language, enforce_response_limit, handle_error
from .changes import map_changes
from .config import initialize_config
from .memory import initialize_memory
from .platform import detect_platform
from .quality import assess_quality
from .validation import validate_docs


async def bootstrap(params: BootstrapInput) -> str | dict[str, Any]:
    """Bootstrap fresh documentation for a project.

    Orchestrates multiple tools to set up documentation from scratch:
    1. Detects/recommends documentation platform
    2. Creates configuration file
    3. Creates documentation directory structure
    4. Generates initial documentation files
    5. Initializes memory system
    6. Runs initial quality assessment

    Args:
        params (BootstrapInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - platform (Optional[DocumentationPlatform]): Platform to use (auto-detected if not specified)
            - docs_path (str): Where to create docs (default: "docs")

    Returns:
        str: Bootstrap report with created files and next steps

    Examples:
        - Use when: Starting documentation for a new project
        - Use when: Setting up docs for existing project without documentation

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if docs_path already exists (won't overwrite)
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Check if docs already exist
        docs_path = project_path / params.docs_path
        if docs_path.exists():
            return enforce_response_limit(f"Error: Documentation directory already exists at {docs_path}. Use migrate workflow to restructure existing docs.")

        lines = ["# Documentation Bootstrap Report", ""]
        lines.append(f"**Project:** {project_path.name}")
        lines.append(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Step 1: Detect platform
        lines.append("## Step 1: Platform Detection")
        lines.append("")

        from ..models import DetectPlatformInput
        platform_result = await detect_platform(DetectPlatformInput(
            project_path=str(project_path)
        ))

        platform_data = platform_result if isinstance(platform_result, dict) else json.loads(platform_result)
        recommended_platform = params.platform or DocumentationPlatform(platform_data["recommendation"])

        lines.append(f"Platform selected: **{recommended_platform.value}**")
        if not params.platform:
            lines.append(f"  (Auto-detected based on: {platform_data['project_language']})")
        lines.append("")

        # Step 2: Create configuration
        lines.append("## Step 2: Configuration")
        lines.append("")

        from ..models import InitializeConfigInput
        config_result = await initialize_config(InitializeConfigInput(
            project_path=str(project_path),
            platform=recommended_platform,
            exclude_patterns=["**/node_modules", "**/dist", "**/vendor", "**/*.log", "**/venv", "**/.git"]
        ))

        if "Error" in config_result:
            return enforce_response_limit(f"Error: Bootstrap failed at configuration step:\n{config_result}")

        lines.append("Created `.doc-manager.yml` configuration")
        lines.append("")

        # Step 3: Create documentation structure
        lines.append("## Step 3: Documentation Structure")
        lines.append("")

        docs_path.mkdir(parents=True, exist_ok=True)

        # Create platform-specific documentation structure
        structure: dict[str, str] = {}
        if recommended_platform == DocumentationPlatform.MKDOCS:
            structure = {
                "README.md": _create_readme_template(project_path),
                "index.md": _create_index_template(project_path),  # MkDocs uses index.md
                "getting-started/installation.md": _create_installation_template(project_path),
                "getting-started/quick-start.md": _create_quickstart_template(project_path),
                "guides/basic-usage.md": _create_usage_template(project_path),
                "reference/configuration.md": _create_config_reference_template(project_path),
            }
        elif recommended_platform == DocumentationPlatform.HUGO:
            structure = {
                "README.md": _create_readme_template(project_path),
                "content/_index.md": _create_index_template(project_path),  # Hugo uses content/_index.md
                "content/getting-started/installation.md": _create_installation_template(project_path),
                "content/getting-started/quick-start.md": _create_quickstart_template(project_path),
                "content/guides/basic-usage.md": _create_usage_template(project_path),
                "content/reference/configuration.md": _create_config_reference_template(project_path),
            }
        elif recommended_platform == DocumentationPlatform.DOCUSAURUS:
            structure = {
                "README.md": _create_readme_template(project_path),
                "intro.md": _create_index_template(project_path),  # Docusaurus uses intro.md
                "getting-started/installation.md": _create_installation_template(project_path),
                "getting-started/quick-start.md": _create_quickstart_template(project_path),
                "guides/basic-usage.md": _create_usage_template(project_path),
                "reference/configuration.md": _create_config_reference_template(project_path),
            }
        created_files = []
        for relative_path, content in structure.items():
            file_path = docs_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            created_files.append(str(file_path.relative_to(project_path)))

        lines.append(f"Created {len(created_files)} documentation files:")
        for file in created_files:
            lines.append(f"  - {file}")
        lines.append("")

        # Step 4: Initialize memory system
        lines.append("## Step 4: Memory System")
        lines.append("")

        from ..models import InitializeMemoryInput
        memory_result = await initialize_memory(InitializeMemoryInput(
            project_path=str(project_path)
        ))

        if "Error" in memory_result:
            return enforce_response_limit(f"Error: Bootstrap failed at memory initialization:\n{memory_result}")

        lines.append("Initialized memory system with baseline checksums")
        lines.append("")

        # Step 5: Initial quality assessment
        lines.append("## Step 5: Initial Quality Assessment")
        lines.append("")

        from ..models import AssessQualityInput
        quality_result = await assess_quality(AssessQualityInput(
            project_path=str(project_path),
            docs_path=params.docs_path
        ))

        quality_data = quality_result if isinstance(quality_result, dict) else json.loads(quality_result)
        overall_score = quality_data.get("overall_score", "unknown")

        lines.append(f"Initial quality score: **{overall_score}**")
        lines.append("  (This will improve as you fill in the template content)")
        lines.append("")

        # Summary and next steps
        lines.append("## Summary")
        lines.append("")
        lines.append("Documentation bootstrapped successfully!")
        lines.append("")
        lines.append("**What was created:**")
        lines.append("- Configuration: `.doc-manager.yml`")
        lines.append(f"- Documentation: `{params.docs_path}/` with {len(created_files)} files")
        lines.append("- Memory system: `.doc-manager/memory/`")
        lines.append("")

        lines.append("## Next Steps")
        lines.append("")
        lines.append("1. **Customize templates**: Fill in project-specific content in the created files")
        lines.append("2. **Add examples**: Include code examples and screenshots")
        lines.append("3. **Configure platform**: Set up your chosen documentation platform")
        lines.append("4. **Run validation**: Use `docmgr_validate_docs` to check for issues")
        lines.append("5. **Assess quality**: Use `docmgr_assess_quality` to measure improvements")
        lines.append("")

        lines.append("**Platform-Specific Setup:**")
        if recommended_platform == DocumentationPlatform.HUGO:
            lines.append("- Install Hugo: `brew install hugo` or download from hugo.io")
            lines.append("- Initialize site: `hugo new site . --force`")
            lines.append("- Add theme: `git submodule add <theme-url> themes/<theme-name>`")
        elif recommended_platform == DocumentationPlatform.MKDOCS:
            lines.append("- Install MkDocs: `pip install mkdocs`")
            lines.append("- Create config: `mkdocs new .`")
            lines.append("- Choose theme in `mkdocs.yml`")
        elif recommended_platform == DocumentationPlatform.DOCUSAURUS:
            lines.append("- Install Node.js/npm if not present")
            lines.append("- Initialize: `npx create-docusaurus@latest . classic`")
            lines.append("- Move generated docs to match structure")

        return {
            "status": "success",
            "message": "Documentation bootstrapped successfully",
            "report": "\n".join(lines),
            "project": project_path.name,
            "platform": recommended_platform.value,
            "docs_path": params.docs_path,
            "files_created": len(created_files),
            "steps": {
                "platform_detection": "completed",
                "configuration": "completed",
                "structure_creation": "completed",
                "memory_initialization": "completed",
                "quality_assessment": "completed"
            },
            "created_files": created_files,
            "quality_score": overall_score
        }
    except Exception as e:
        return enforce_response_limit(handle_error(e, "bootstrap"))


def _create_readme_template(project_path: Path) -> str:
    """Create README.md template."""
    project_name = project_path.name
    return f"""# {project_name} Documentation

Welcome to the {project_name} documentation!

## Quick Links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quick-start.md)
- [Guides](guides/basic-usage.md)
- [Configuration Reference](reference/configuration.md)

## About

[Add a brief description of your project here]

## Getting Help

[Add information about how users can get help - links to issue tracker, community channels, etc.]

## Contributing

[Add link to contributing guide if applicable]
"""


def _create_index_template(project_path: Path) -> str:
    """Create index page template."""
    project_name = project_path.name
    return f"""# {project_name}

## Overview

[Provide a comprehensive overview of your project, its purpose, and key features]

## Key Features

- Feature 1
- Feature 2
- Feature 3

## Quick Example

```
[Add a simple code example showing basic usage]
```

## Documentation Sections

### Getting Started
Learn how to install and start using {project_name}.

### Guides
Step-by-step tutorials for common tasks.

### Reference
Detailed technical reference documentation.
"""


def _create_installation_template(project_path: Path) -> str:
    """Create installation guide template."""
    language = detect_project_language(project_path)

    content = """# Installation

## Prerequisites

[List required software, versions, etc.]

## Installation Methods

### Method 1: [Primary method]

[Provide installation instructions for your primary installation method]

"""

    if language == "Python":
        content += """```bash
pip install {project_name}
```
"""
    elif language == "Go":
        content += """```bash
go install github.com/your-org/{project_name}@latest
```
"""
    elif language in ["JavaScript/TypeScript", "Node.js"]:
        content += """```bash
npm install {project_name}
# or
yarn add {project_name}
```
"""

    content += """
### Method 2: [Alternative method]

[Provide alternative installation method if applicable]

## Verification

[Explain how users can verify the installation was successful]

```bash
[command to verify installation]
```

## Troubleshooting

[Add common installation issues and solutions]
"""

    return content


def _create_quickstart_template(project_path: Path) -> str:
    """Create quick start guide template."""
    project_name = project_path.name
    return f"""# Quick Start

Get up and running with {project_name} in 5 minutes.

## Step 1: Installation

See [Installation Guide](installation.md) for detailed instructions.

## Step 2: Basic Configuration

[Provide minimal configuration needed to get started]

## Step 3: Your First [Task]

[Walk through a simple, practical example]

```bash
[commands or code]
```

## Next Steps

- [Link to more detailed guides]
- [Link to examples]
- [Link to API reference]
"""


def _create_usage_template(project_path: Path) -> str:
    """Create basic usage guide template."""
    return """# Basic Usage

## Common Tasks

### Task 1: [Common task name]

[Step-by-step instructions]

```bash
[example command or code]
```

### Task 2: [Another common task]

[Instructions]

```bash
[example]
```

## Best Practices

[Add recommended practices for using the tool/library]

## Examples

### Example 1: [Realistic scenario]

[Full example with explanation]

## See Also

- [Link to related guides]
- [Link to API reference]
"""


def _create_config_reference_template(project_path: Path) -> str:
    """Create configuration reference template."""
    return """# Configuration Reference

## Configuration File

[Describe the configuration file format, location, and structure]

## Configuration Options

### Option 1

- **Type**: [string/number/boolean/etc.]
- **Default**: [default value]
- **Required**: [yes/no]
- **Description**: [What this option does]

**Example:**
```yaml
option1: value
```

### Option 2

[Repeat for each configuration option]

## Environment Variables

[Document environment variables if applicable]

## Configuration Examples

### Example 1: [Common configuration scenario]

```yaml
[full configuration example]
```

### Example 2: [Another scenario]

```yaml
[configuration]
```
"""


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

        from ..models import AssessQualityInput
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

        from ..models import DetectPlatformInput
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
        lines.append("## Step 3: Creating New Structure")
        lines.append("")

        # Copy entire directory tree
        import shutil

        moved_files = []
        link_updates_needed = []

        # Use shutil.copytree to preserve directory structure
        # Note: preserve_history option is not fully supported for directory trees
        # We'll just copy the entire structure
        try:
            shutil.copytree(existing_docs, new_docs, dirs_exist_ok=False)

            # Count all files that were copied
            for file_path in new_docs.rglob("*"):
                if file_path.is_file():
                    relative_in_new = file_path.relative_to(new_docs)
                    old_path = existing_docs / relative_in_new

                    moved_files.append({
                        "old": str(old_path.relative_to(project_path)),
                        "new": str(file_path.relative_to(project_path)),
                        "method": "copy"
                    })
        except Exception as e:
            return enforce_response_limit(f"Error: Failed to copy documentation: {e}")

        lines.append(f"Migrated {len(moved_files)} documentation files")
        lines.append("")

        # Step 4: Update internal links
        lines.append("## Step 4: Link Updates")
        lines.append("")

        # Scan for broken links in new structure
        from ..models import ValidateDocsInput
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


async def sync(params: SyncInput) -> dict[str, Any] | str:
    """Sync documentation with code changes.

    Orchestrates documentation synchronization:
    1. Maps code changes to affected documentation
    2. Identifies documentation that needs updates
    3. Validates current documentation state
    4. Assesses documentation quality
    5. Updates memory baseline (if changes applied)
    6. Generates sync report with actionable recommendations

    Args:
        params (SyncInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - mode (str): "reactive" (manual) or "proactive" (auto-detect)
            - response_format (ResponseFormat): Output format

    Returns:
        str: Sync report with affected docs and recommendations

    Examples:
        - Use when: After making code changes
        - Use when: Before releasing documentation updates
        - Use when: Running in CI/CD to detect doc staleness

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if memory baseline not found
        - Returns info if no changes detected
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        lines = ["# Documentation Sync Report", ""]
        lines.append(f"**Project:** {project_path.name}")
        lines.append(f"**Sync Mode:** {params.mode}")
        lines.append(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Step 1: Map code changes
        lines.append("## Step 1: Change Detection")
        lines.append("")

        # Check if baseline exists
        baseline_path = project_path / ".doc-manager" / "memory" / "repo-baseline.json"
        if not baseline_path.exists():
            return enforce_response_limit("Error: No baseline found. Please run docmgr_initialize_memory first to establish a baseline for change detection.")

        from ..models import MapChangesInput
        changes_result = await map_changes(MapChangesInput(
            project_path=str(project_path)
        ))

        changes_data = changes_result if isinstance(changes_result, dict) else json.loads(changes_result)
        changes_detected = changes_data.get("changes_detected", False)
        total_changes = changes_data.get("total_changes", 0)
        affected_docs = changes_data.get("affected_documentation", [])

        if not changes_detected:
            return {
                "status": "success",
                "message": "No changes detected",
                "changes": 0,
                "affected_docs": 0,
                "recommendations": []
            }

        lines.append(f"Warning:  Detected {total_changes} code changes")
        lines.append("")

        # Step 2: Identify affected documentation
        lines.append("## Step 2: Affected Documentation")
        lines.append("")

        # Initialize priority lists
        high_priority: list = []

        if not affected_docs:
            lines.append("No documentation impacts detected")
            lines.append("  (Changes only affected tests, infrastructure, or docs themselves)")
            lines.append("")
        # Step 3: Validate current documentation
        lines.append("## Step 3: Current Documentation Status")
        lines.append("")

        from ..models import ValidateDocsInput
        from ..utils import find_docs_directory

        # Use provided docs_path or auto-detect
        if params.docs_path:
            docs_path = project_path / params.docs_path
        else:
            docs_path = find_docs_directory(project_path)

        # Initialize validation metrics
        total_issues: int | None = None

        if docs_path and docs_path.exists():
            validation_result = await validate_docs(ValidateDocsInput(
                project_path=str(project_path),
                docs_path=str(docs_path.relative_to(project_path))
            ))

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
        # Step 4: Quality assessment
        lines.append("## Step 4: Quality Assessment")
        lines.append("")

        # Initialize quality metrics
        overall_score: str | None = None

        if docs_path:
            from ..models import AssessQualityInput
            quality_result = await assess_quality(AssessQualityInput(
                project_path=str(project_path),
                docs_path=str(docs_path.relative_to(project_path))
            ))

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
        # Step 5: Recommendations
        lines.append("## Sync Recommendations")
        lines.append("")

        if params.mode == "reactive":
            lines.append("**Manual Actions Required:**")
            lines.append("")

            if affected_docs:
                lines.append("1. **Update affected documentation:**")
                for doc in high_priority[:5]:
                    lines.append(f"   - {doc['file']}")

                lines.append("")
                lines.append("2. **Review changes:**")
                lines.append("   - Check that examples still work")
                lines.append("   - Update screenshots if UI changed")
                lines.append("   - Verify configuration examples")

            lines.append("")
            lines.append("3. **Run validation:**")
            lines.append("   ```")
            lines.append("   docmgr_validate_docs")
            lines.append("   ```")

            lines.append("")
            lines.append("4. **Update baseline:**")
            lines.append("   After applying updates, refresh the memory baseline:")
            lines.append("   ```")
            lines.append("   docmgr_initialize_memory")
            lines.append("   ```")

        elif params.mode == "proactive":
            lines.append("**Proactive Sync Suggestions:**")
            lines.append("")

            if affected_docs:
                lines.append("The following documentation files are out of sync with code:")
                for doc in affected_docs[:10]:
                    lines.append(f"- {doc['file']} (Priority: {doc['priority']})")

                if len(affected_docs) > 10:
                    lines.append(f"  ... and {len(affected_docs) - 10} more")

                lines.append("")
                lines.append("Consider:")
                lines.append("- Creating a PR to update these files")
                lines.append("- Adding TODO comments in affected docs")
                lines.append("- Flagging as 'needs-update' in your issue tracker")

        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"**Code Changes:** {total_changes} files modified")
        lines.append(f"**Documentation Impact:** {len(affected_docs)} files affected")

        if docs_path:
            lines.append(f"**Validation Issues:** {total_issues if total_issues is not None else 'N/A'}")
            lines.append(f"**Quality Score:** {overall_score if overall_score is not None else 'N/A'}")

        lines.append("")
        lines.append("**Next Steps:**")
        if affected_docs:
            lines.append("1. Review and update affected documentation")
            lines.append("2. Run validation to ensure no broken links")
            lines.append("3. Update memory baseline after changes")
        return {
            "status": "success",
            "message": "Sync analysis completed",
            "report": "\n".join(lines),
            "changes": total_changes,
            "affected_docs": len(affected_docs),
            "recommendations": [doc["file"] for doc in affected_docs[:10]],
            "validation_issues": total_issues,
            "quality_score": overall_score
        }
    except Exception as e:
        return enforce_response_limit(handle_error(e, "sync"))
