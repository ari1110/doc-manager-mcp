"""Memory system tools for doc-manager."""

import asyncio
import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

from ..constants import DEFAULT_EXCLUDE_PATTERNS, MAX_FILES, OPERATION_TIMEOUT
from ..models import InitializeMemoryInput
from ..utils import (
    calculate_checksum,
    detect_project_language,
    enforce_response_limit,
    file_lock,
    find_docs_directory,
    handle_error,
    load_config,
    matches_exclude_pattern,
    run_git_command,
    validate_path_boundary,
)


def with_timeout(timeout_seconds):
    """Decorator to add timeout enforcement to async functions.

    Args:
        timeout_seconds (int): Maximum execution time in seconds

    Raises:
        TimeoutError: If operation exceeds timeout limit
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Use asyncio.wait_for for async timeout enforcement
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError as err:
                raise TimeoutError(
                    f"Operation exceeded timeout ({timeout_seconds}s)\n"
                    f"→ Consider processing fewer files or increasing timeout limit."
                ) from err
        return wrapper
    return decorator

async def initialize_memory(params: InitializeMemoryInput) -> str | dict[str, Any]:
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
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

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

        # Load config to get user-defined exclude patterns
        config = load_config(project_path)
        user_excludes = config.get("exclude", []) if config else []

        # Merge default excludes with user excludes (defaults always applied)
        # This ensures we skip .git, node_modules, __pycache__, etc. automatically
        exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS) + user_excludes

        # Calculate checksums for all files in project
        # Use os.walk with directory filtering to skip excluded dirs efficiently
        checksums = {}
        file_count = 0

        for root, dirs, files in os.walk(project_path):
            root_path = Path(root)

            # Filter directories IN-PLACE to prevent os.walk from entering them
            # This prevents scanning .git, node_modules, __pycache__, etc. entirely
            # Much faster than scanning everything then filtering
            dirs[:] = [
                d for d in dirs
                if not matches_exclude_pattern(
                    str((root_path / d).relative_to(project_path)).replace('\\', '/'),
                    exclude_patterns
                )
            ]

            # Process files in this directory
            for file_name in files:
                if file_count >= MAX_FILES:
                    raise ValueError(
                        f"File count limit exceeded (maximum: {MAX_FILES:,} files)\n"
                        f"→ Consider processing a smaller directory or increasing the limit."
                    )

                file_path = root_path / file_name

                # Validate path boundary and check for malicious symlinks (T028 - FR-028)
                try:
                    _ = validate_path_boundary(file_path, project_path)
                except ValueError:
                    # Skip files that escape project boundary or malicious symlinks
                    continue

                relative_path_str = str(file_path.relative_to(project_path)).replace('\\', '/')

                # Skip if file matches exclude patterns
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
        # T065: Use file locking to prevent concurrent modification (FR-018)
        with file_lock(baseline_path):
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

        # Return structured data
        return {
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
        }

    except Exception as e:
        return enforce_response_limit(handle_error(e, "initialize_memory"))
