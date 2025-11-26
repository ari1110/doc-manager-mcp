"""Memory system tools for doc-manager."""

import asyncio
import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from doc_manager_mcp.constants import MAX_FILES
from doc_manager_mcp.core import (
    calculate_checksum,
    detect_project_language,
    enforce_response_limit,
    file_lock,
    find_docs_directory,
    handle_error,
    matches_exclude_pattern,
    run_git_command,
    validate_path_boundary,
)
from doc_manager_mcp.models import InitializeMemoryInput


async def scandir_async(path: Path):
    """Asynchronously scan a directory."""
    try:
        for entry in os.scandir(path):
            yield entry
    except (FileNotFoundError, PermissionError):
        # Skip directories that can't be accessed
        pass


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

async def initialize_memory(params: InitializeMemoryInput, ctx=None) -> str | dict[str, Any]:
    """Initialize the documentation memory system for tracking project state.

    INTERNAL USE ONLY: This function is not exposed as an MCP tool in v2.0.0.
    Use docmgr_init(mode="existing") instead, which calls this internally.

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

        if ctx:
            await ctx.report_progress(progress=10, total=100)
            await ctx.info("Initializing memory system...")

        # Build exclude patterns using shared logic
        from doc_manager_mcp.core.patterns import build_exclude_patterns
        exclude_patterns, gitignore_spec = build_exclude_patterns(project_path)

        if ctx:
            await ctx.report_progress(progress=20, total=100)
            await ctx.info("Scanning project files...")

        checksums = {}
        file_count = 0

        async def process_directory(current_path: Path):
            nonlocal file_count
            async for entry in scandir_async(current_path):
                if file_count >= MAX_FILES:
                    break

                entry_path = Path(entry.path)
                relative_path_str = str(entry_path.relative_to(project_path)).replace('\\', '/')

                # Check exclude patterns (user + defaults)
                if matches_exclude_pattern(relative_path_str, exclude_patterns):
                    continue

                # Check gitignore patterns (if enabled)
                if gitignore_spec and gitignore_spec.match_file(relative_path_str):
                    continue

                if entry.is_dir():
                    await process_directory(entry_path)
                elif entry.is_file():
                    try:
                        validate_path_boundary(entry_path, project_path)
                        checksums[relative_path_str] = calculate_checksum(entry_path)
                        file_count += 1

                        # Report progress every 10 files (20-80% range)
                        if ctx and file_count % 10 == 0:
                            progress = 20 + min(60, (file_count / MAX_FILES) * 60)
                            await ctx.report_progress(progress=int(progress), total=100)
                    except ValueError:
                        continue

        await process_directory(project_path)

        if file_count >= MAX_FILES:
            raise ValueError(
                f"File count limit exceeded (maximum: {MAX_FILES:,} files)\n"
                f"→ Consider processing a smaller directory or increasing the limit."
            )

        if ctx:
            await ctx.report_progress(progress=80, total=100)
            await ctx.info(f"Scanned {file_count} files, creating baseline...")

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

        # Generate documentation conventions YAML with opinionated defaults
        conventions_yaml = """# Documentation Conventions Configuration
# Generated by doc-manager
#
# This file defines documentation standards for your project.
# Edit these values to match your team's preferences.

style:
  headings:
    # Heading case style: sentence_case | title_case | lower | upper
    # Examples:
    #   sentence_case: "This is a heading"
    #   title_case: "This Is A Heading"
    case: sentence_case

    # Enforce consistent heading case throughout project
    consistency_required: true

  code:
    # Format for inline code references: backticks | html
    inline_format: backticks

    # Require language specification in code blocks (```python vs ```)
    block_language_required: true

  voice:
    # Grammatical person for documentation: first | second | third
    # first: "We recommend...", second: "You should...", third: "Users should..."
    person: second

    # Prefer active voice ("Click the button") over passive ("The button should be clicked")
    active_voice_preferred: true

structure:
  # Require introductory paragraph before first heading
  require_intro: true

  # Table of contents requirements
  require_toc:
    # Whether to require TOC
    enabled: true

    # Generate TOC for docs longer than N words
    min_length: 500

  # Maximum heading depth (1-6, where 1 is #, 6 is ######)
  max_heading_depth: 3

  # Enforce strict heading hierarchy (no skipping levels: H1→H3 is invalid)
  # Options: strict | relaxed
  heading_hierarchy: strict

quality:
  sentences:
    # Sentence length limits (in words)
    max_length: 25
    min_length: 3

  paragraphs:
    # Maximum paragraph length (in words)
    max_length: 150

  links:
    # Validate all links are reachable
    validate_links: true

  images:
    # All images must have descriptive alt text
    require_alt_text: true

  code:
    # Validate code syntax (expensive, requires TreeSitter)
    validate_syntax: false

# Project-specific terminology
terminology:
  # Preferred terms (enforce consistent usage)
  # Format: abbreviation_key:
  #           full_form: "Full Term Name"
  #           abbreviation: "ABBR"
  #           guidance: "Usage guidance"
  preferred: {}
    # Example:
    # mcp:
    #   full_form: "Model Context Protocol"
    #   abbreviation: "MCP"
    #   guidance: "Spell out on first use, abbreviate after"

  # Words/phrases to avoid (flagged as warnings)
  # Note: May produce false positives - review warnings manually
  avoid:
    - word: simply
      reason: "Use specific descriptions instead"
      exceptions: []

    - word: just
      reason: "Be precise about what you mean"
      exceptions: ["just-in-time", "justify"]

    - word: easy
      reason: "Describe specific effort required"
      exceptions: []

    - word: obviously
      reason: "What's obvious to you may not be to readers"
      exceptions: []

# Future enhancement: semantic_checking: true  # Requires spaCy (optional)
"""

        conventions_path = memory_dir / "memory" / "doc-conventions.yml"
        if not conventions_path.exists():
            with open(conventions_path, 'w', encoding='utf-8') as f:
                f.write(conventions_yaml)

        # NOTE: Asset-manifest.json has been deprecated.
        # Assets are now tracked in two places:
        # 1. repo-baseline.json (checksums for all files including images)
        # 2. dependencies.json (asset_to_docs mapping for doc references)

        if ctx:
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"Memory system initialized! Tracked {file_count} files.")

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
