#!/usr/bin/env python3
"""
Documentation Manager MCP Server

An MCP server for comprehensive documentation lifecycle management including:
- Documentation generation (bootstrap)
- Migration and restructuring
- Incremental synchronization
- Quality assessment (7 criteria)
- Validation (links, assets, code snippets)
- Monorepo support
- Testing change detection
"""

# Fix Windows asyncio event loop for subprocess support
# Windows requires ProactorEventLoop for asyncio.create_subprocess_exec
# Uvicorn defaults to SelectorEventLoop which doesn't support subprocess
import asyncio
import platform
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

# Import constants for enum conversions
from .constants import (
    ChangeDetectionMode,
    DocumentationPlatform,
    QualityCriterion,
)

# Import models
from .models import (
    AssessQualityInput,
    DetectPlatformInput,
    DocmgrDetectChangesInput,
    DocmgrInitInput,
    DocmgrUpdateBaselineInput,
    MigrateInput,
    SyncInput,
    ValidateDocsInput,
)

# Import tool implementations
from .tools.analysis.detect_changes import docmgr_detect_changes
from .tools.analysis.platform import detect_platform
from .tools.analysis.quality.assessment import assess_quality
from .tools.analysis.validation.validator import validate_docs
from .tools.state.init import docmgr_init
from .tools.state.update_baseline import docmgr_update_baseline
from .tools.workflows import migrate, sync

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Initialize the MCP server
mcp = FastMCP("doc_manager_mcp")

# ============================================================================
# Register Tools
# ============================================================================

# ----------------------------------------------------------------------------
# Tier 1: Setup & Initialization
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_init",
    annotations=ToolAnnotations(
        title="Initialize Documentation Manager",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def tool_docmgr_init(
    project_path: str,
    mode: str = "existing",
    platform: str | None = None,
    exclude_patterns: list[str] | None = None,
    docs_path: str | None = None,
    sources: list[str] | None = None,
    use_gitignore: bool = False,
    ctx: Context | None = None
) -> dict[str, Any]:
    """Initialize doc-manager for a project (existing docs or create new).

    Use when: Setting up doc-manager for the first time in a project
    Result: Creates .doc-manager.yml, baselines (repo, symbols, dependencies), and optionally bootstraps documentation structure
    Mode: State-modifying (creates files and directories)

    Modes:
    - mode="existing": For projects with existing documentation - creates config and baselines only
    - mode="bootstrap": For new projects - creates documentation structure from templates plus config and baselines

    Typical workflow: Run once at project setup, before any other doc-manager tools
    """
    params = DocmgrInitInput(
        project_path=project_path,
        mode=mode,
        platform=DocumentationPlatform(platform) if platform else None,
        exclude_patterns=exclude_patterns,
        docs_path=docs_path,
        sources=sources,
        use_gitignore=use_gitignore
    )
    return await docmgr_init(params, ctx)

# ----------------------------------------------------------------------------
# Tier 2: Analysis & Read-Only Operations
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_detect_changes",
    annotations=ToolAnnotations(
        title="Detect Code Changes (Read-Only)",
        readOnlyHint=True,  # NEVER writes to baselines
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def tool_docmgr_detect_changes(
    project_path: str,
    since_commit: str | None = None,
    mode: str = "checksum",
    include_semantic: bool = False
) -> dict[str, Any]:
    """Detect code changes without modifying baselines (pure read-only).

    Use when: Checking if documentation is out of sync after code changes
    Result: Lists changed files (categorized as code/docs/assets/etc.), affected documentation, and optional semantic changes
    Mode: Read-only (never modifies any files)

    Modes:
    - mode="checksum": Compare current file checksums against repo-baseline.json
    - mode="git_diff": Compare current files against a specific git commit

    Set include_semantic=true to detect symbol-level changes (functions/classes added/modified/deleted).

    Typical workflow: Run after code changes to identify which docs may need updates, before deciding whether to update documentation or baselines
    """
    params = DocmgrDetectChangesInput(
        project_path=project_path,
        since_commit=since_commit,
        mode=ChangeDetectionMode(mode),
        include_semantic=include_semantic
    )
    return await docmgr_detect_changes(params)

# ----------------------------------------------------------------------------
# Tier 3: State Management
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_update_baseline",
    annotations=ToolAnnotations(
        title="Update All Baselines",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def tool_docmgr_update_baseline(
    project_path: str,
    docs_path: str | None = None,
    ctx: Context | None = None
) -> dict[str, Any]:
    """Update all baseline files to reflect current project state.

    Use when: After updating documentation to match code changes, resetting the "clean" baseline
    Result: Atomically updates three baseline files: repo-baseline.json (checksums), symbol-baseline.json (code symbols), dependencies.json (code-doc mappings)
    Mode: State-modifying (rewrites baseline files)

    This resets change detection to current state - run this when documentation is in sync with code.

    Typical workflow: After writing/updating docs → run this to update baselines → future change detection starts from new baseline
    """
    params = DocmgrUpdateBaselineInput(
        project_path=project_path,
        docs_path=docs_path
    )
    return await docmgr_update_baseline(params, ctx)

# ----------------------------------------------------------------------------
# Tier 2: Analysis & Read-Only Operations (continued)
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_detect_platform",
    annotations=ToolAnnotations(
        title="Detect Documentation Platform",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_detect_platform(
    project_path: str
) -> str | dict[str, Any]:
    """Auto-detect documentation platform (MkDocs, Sphinx, Hugo, etc.) or recommend one.

    Use when: Setting up doc-manager for first time and unsure which platform is in use
    Result: Returns detected platform or recommendations based on project language and structure
    Mode: Read-only (analyzes project files only)

    Detects by checking for platform-specific config files (mkdocs.yml, conf.py, config.toml, docusaurus.config.js).

    Typical workflow: Run before docmgr_init to determine correct platform value for configuration
    """
    params = DetectPlatformInput(
        project_path=project_path
    )
    return await detect_platform(params)

@mcp.tool(
    name="docmgr_validate_docs",
    annotations=ToolAnnotations(
        title="Validate Documentation",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_validate_docs(
    project_path: str,
    docs_path: str | None = None,
    check_links: bool = True,
    check_assets: bool = True,
    check_snippets: bool = True,
    validate_code_syntax: bool = False,
    validate_symbols: bool = False
) -> str | dict[str, Any]:
    """Validate documentation for broken links, missing assets, code snippet syntax, and convention compliance.

    Use when: Before releases, after major doc updates, or as part of CI/CD to catch documentation issues
    Result: Returns list of validation issues categorized by type (broken links, missing assets, syntax errors, convention violations) with file/line numbers
    Mode: Read-only (only analyzes documentation)

    Optional checks:
    - check_links: Validate internal links point to existing files
    - check_assets: Verify images/assets exist and have alt text
    - check_snippets: Validate code block syntax
    - validate_code_syntax: Deep syntax validation with TreeSitter (slower)
    - validate_symbols: Check documented symbols exist in codebase

    Typical workflow: Run regularly to maintain documentation quality, fix reported issues, re-run until clean
    """
    params = ValidateDocsInput(
        project_path=project_path,
        docs_path=docs_path,
        check_links=check_links,
        check_assets=check_assets,
        check_snippets=check_snippets,
        validate_code_syntax=validate_code_syntax,
        validate_symbols=validate_symbols
    )
    return await validate_docs(params)

@mcp.tool(
    name="docmgr_assess_quality",
    annotations=ToolAnnotations(
        title="Assess Documentation Quality",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_assess_quality(
    project_path: str,
    docs_path: str | None = None,
    criteria: list[str] | None = None
) -> str | dict[str, Any]:
    """Assess documentation quality against 7 criteria with scores and actionable findings.

    Use when: Auditing documentation health, before major releases, or tracking quality improvements over time
    Result: Returns quality scores (good/fair/poor) for each criterion plus specific findings, issues, and metrics
    Mode: Read-only (analyzes documentation only)

    7 Quality criteria evaluated:
    - Relevance: Addresses current user needs (not outdated)
    - Accuracy: Reflects actual codebase state
    - Purposefulness: Clear goals and target audience
    - Uniqueness: No redundant or conflicting information
    - Consistency: Aligned terminology, formatting, style
    - Clarity: Precise language and navigation
    - Structure: Logical organization and hierarchy

    Typical workflow: Run periodically to track quality trends, use findings to prioritize documentation improvements
    """
    params = AssessQualityInput(
        project_path=project_path,
        docs_path=docs_path,
        criteria=[QualityCriterion(c) for c in criteria] if criteria else None
    )
    return await assess_quality(params)

# ----------------------------------------------------------------------------
# Tier 4: Workflows & Orchestration
# ----------------------------------------------------------------------------

@mcp.tool(
    name="docmgr_migrate",
    annotations=ToolAnnotations(
        title="Migrate Documentation Structure",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False
    )
)
async def docmgr_migrate(
    project_path: str,
    source_path: str,
    target_path: str = "docs",
    target_platform: str | None = None,
    preserve_history: bool = True,
    rewrite_links: bool = False,
    regenerate_toc: bool = False,
    dry_run: bool = False
) -> str | dict[str, Any]:
    """Migrate or restructure documentation while optionally preserving git history.

    Use when: Moving docs to new location, changing documentation platform, or reorganizing documentation structure
    Result: Moves/restructures documentation files, optionally rewrites internal links, regenerates TOC, preserves git history
    Mode: State-modifying (moves files, modifies content)

    Options:
    - preserve_history=true: Uses git mv to maintain file history
    - rewrite_links=true: Updates internal links to match new structure
    - regenerate_toc=true: Rebuilds table of contents
    - dry_run=true: Shows what would be done without making changes

    Typical workflow: Set dry_run=true first to preview changes → review plan → run with dry_run=false to execute migration
    """
    params = MigrateInput(
        project_path=project_path,
        source_path=source_path,
        target_path=target_path,
        target_platform=DocumentationPlatform(target_platform) if target_platform else None,
        preserve_history=preserve_history,
        rewrite_links=rewrite_links,
        regenerate_toc=regenerate_toc,
        dry_run=dry_run
    )
    return await migrate(params)

@mcp.tool(
    name="docmgr_sync",
    annotations=ToolAnnotations(
        title="Sync Documentation with Code Changes",
        readOnlyHint=False,  # mode="resync" updates baselines
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False
    )
)
async def docmgr_sync(
    project_path: str,
    mode: str = "check",
    docs_path: str | None = None
) -> str | dict[str, Any]:
    """Orchestrate complete documentation sync: detect changes, validate, assess quality, optionally update baselines.

    Use when: After code changes to get complete documentation health report, or after doc updates to reset baselines
    Result: Comprehensive sync report with changed files, affected docs, validation issues, quality scores, and baseline status
    Mode: Depends on mode parameter - "check" is read-only, "resync" modifies baselines

    Modes:
    - mode="check": Read-only analysis - detects changes, validates docs, assesses quality (no baseline updates)
    - mode="resync": Full sync - runs all checks PLUS updates all baselines atomically

    This tool orchestrates: change detection → affected doc mapping → validation → quality assessment → optional baseline update.

    Typical workflow: Use mode="check" after code changes to see documentation impact → fix identified issues → use mode="resync" to update baselines
    """
    params = SyncInput(
        project_path=project_path,
        mode=mode,
        docs_path=docs_path
    )
    return await sync(params)

def main():
    """Entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
