"""Memory system tools for doc-manager."""

from pathlib import Path
from datetime import datetime
import json

from ..models import InitializeMemoryInput
from ..constants import ResponseFormat
from ..utils import (
    detect_project_language,
    find_docs_directory,
    run_git_command,
    calculate_checksum,
    handle_error,
    load_config,
    matches_exclude_pattern
)

async def initialize_memory(params: InitializeMemoryInput) -> str:
    """Initialize the documentation memory system for tracking project state.

    This tool creates the `.doc-manager/` directory structure with memory files
    that track repository baseline, documentation conventions, and file checksums.

    Args:
        params (InitializeMemoryInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root

    Returns:
        str: Success message with memory system summary or error message

    Examples:
        - Use when: Setting up memory tracking for the first time
        - Use when: Resetting memory after major changes
        - Don't use when: Memory system already exists (delete `.doc-manager/` first)

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if `.doc-manager/` already exists
        - Returns error if unable to create memory files
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return f"Error: Project path does not exist: {project_path}"

        memory_dir = project_path / ".doc-manager"

        # Create memory directory structure (overwrite if exists)
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "memory").mkdir(exist_ok=True)

        # Get project metadata
        repo_name = project_path.name
        language = detect_project_language(project_path)
        docs_dir = find_docs_directory(project_path)
        docs_exist = docs_dir is not None

        # Get git info
        git_commit = run_git_command(project_path, "rev-parse", "HEAD")
        git_branch = run_git_command(project_path, "rev-parse", "--abbrev-ref", "HEAD")

        # Load config to get exclude patterns
        config = load_config(project_path)
        exclude_patterns = config.get("exclude", []) if config else []
        # Add default excludes if not in config
        if not exclude_patterns:
            exclude_patterns = ["**/node_modules", "**/dist", "**/vendor", "**/*.log", "**/.git"]

        # Calculate checksums for all files in project
        checksums = {}
        file_count = 0
        for file_path in project_path.rglob("*"):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                relative_path = file_path.relative_to(project_path)
                relative_path_str = str(relative_path).replace('\\', '/')

                # Skip if matches exclude patterns
                if matches_exclude_pattern(relative_path_str, exclude_patterns):
                    continue

                checksums[relative_path_str] = calculate_checksum(file_path)
                file_count += 1

        # Create repo baseline
        baseline = {
            "repo_name": repo_name,
            "description": f"Repository for {repo_name}",
            "language": language,
            "docs_exist": docs_exist,
            "docs_path": str(docs_dir.relative_to(project_path)) if docs_dir else None,
            "metadata": {
                "git_commit": git_commit,
                "git_branch": git_branch
            },
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "file_count": file_count,
            "files": checksums
        }

        baseline_path = memory_dir / "memory" / "repo-baseline.json"
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(baseline, f, indent=2)

        # Create doc conventions template
        conventions = """# Documentation Conventions

## Style Guide

### Writing Style
- Use second person ("you") for user-facing documentation
- Use active voice for instructions
- Keep sentences concise and clear

### Formatting
- Use sentence case for headings
- Use backticks for inline code: `code`
- Use triple backticks for code blocks with language specified

### Terminology
- Be consistent with technical terms
- Define acronyms on first use
- Use the project's preferred naming conventions

## Structure

### Document Organization
- Start with a clear introduction
- Use hierarchical headings (H1 → H2 → H3)
- Include a table of contents for long documents

### Code Examples
- Provide complete, runnable examples
- Include expected output
- Add comments for clarity

## Quality Standards

- All images must have descriptive alt text
- All links must be valid and up-to-date
- All code examples must be tested and working
- Documentation must be kept in sync with code changes

---

*This file can be customized to match your project's documentation standards.*
"""

        conventions_path = memory_dir / "memory" / "doc-conventions.md"
        # Only create conventions file if it doesn't already exist
        if not conventions_path.exists():
            with open(conventions_path, 'w', encoding='utf-8') as f:
                f.write(conventions)

        # Create asset manifest (empty initially)
        asset_manifest = {
            "assets": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        asset_path = memory_dir / "asset-manifest.json"
        with open(asset_path, 'w', encoding='utf-8') as f:
            json.dump(asset_manifest, f, indent=2)

        # Return JSON or Markdown based on response_format
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "status": "success",
                "message": "Memory system initialized successfully",
                "baseline_path": str(baseline_path),
                "conventions_path": str(conventions_path),
                "repository": repo_name,
                "language": language,
                "docs_exist": docs_exist,
                "metadata": {
                    "git_commit": git_commit[:8] if git_commit else None,
                    "git_branch": git_branch
                },
                "files_tracked": file_count
            }, indent=2)
        else:
            return f"""✓ Memory system initialized successfully

**Memory System Summary:**
- Repository: {repo_name}
- Language: {language}
- Documentation: {'Found' if docs_exist else 'Not found'}
- Git Commit: {git_commit[:8] if git_commit else 'N/A'}
- Files Tracked: {file_count}

**Created Files:**
- {memory_dir}/memory/repo-baseline.json
- {memory_dir}/memory/doc-conventions.md
- {memory_dir}/asset-manifest.json

Next steps:
1. Customize `doc-conventions.md` to match your project's standards
2. Run `docmgr_bootstrap` or `docmgr_migrate` to set up documentation
3. Run `docmgr_sync` to keep docs in sync with code changes
"""

    except Exception as e:
        return handle_error(e, "initialize_memory")
