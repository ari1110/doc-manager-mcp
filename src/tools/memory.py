"""Memory system tools for doc-manager."""

import asyncio
import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

async def scandir_async(path: Path):
    """Asynchronously scan a directory."""
    try:
        for entry in os.scandir(path):
            yield entry
    except (FileNotFoundError, PermissionError):
        # Skip directories that can't be accessed
        pass

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
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "memory").mkdir(exist_ok=True)

        repo_name = project_path.name
        language = detect_project_language(project_path)
        docs_dir = find_docs_directory(project_path)
        docs_exist = docs_dir is not None

        git_commit_task = asyncio.create_task(run_git_command(project_path, "rev-parse", "HEAD"))
        git_branch_task = asyncio.create_task(run_git_command(project_path, "rev-parse", "--abbrev-ref", "HEAD"))

        config = load_config(project_path)
        user_excludes = config.get("exclude", []) if config else []
        exclude_patterns = list(DEFAULT_EXCLUDE_PATTERNS) + user_excludes

        checksums = {}
        file_count = 0
        
        async def process_directory(current_path: Path):
            nonlocal file_count
            async for entry in scandir_async(current_path):
                if file_count >= MAX_FILES:
                    break

                entry_path = Path(entry.path)
                relative_path_str = str(entry_path.relative_to(project_path)).replace('\\', '/')

                if matches_exclude_pattern(relative_path_str, exclude_patterns):
                    continue

                if entry.is_dir():
                    await process_directory(entry_path)
                elif entry.is_file():
                    try:
                        validate_path_boundary(entry_path, project_path)
                        checksums[relative_path_str] = calculate_checksum(entry_path)
                        file_count += 1
                    except ValueError:
                        continue
        
        await process_directory(project_path)

        if file_count >= MAX_FILES:
            raise ValueError(
                f"File count limit exceeded (maximum: {MAX_FILES:,} files)\n"
                f"→ Consider processing a smaller directory or increasing the limit."
            )

        git_commit, git_branch = await asyncio.gather(git_commit_task, git_branch_task)

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
        with file_lock(baseline_path):
            with open(baseline_path, 'w', encoding='utf-8') as f:
                json.dump(baseline, f, indent=2)

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
        if not conventions_path.exists():
            with open(conventions_path, 'w', encoding='utf-8') as f:
                f.write(conventions)

        asset_manifest = {
            "assets": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

        asset_path = memory_dir / "asset-manifest.json"
        with open(asset_path, 'w', encoding='utf-8') as f:
            json.dump(asset_manifest, f, indent=2)

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
