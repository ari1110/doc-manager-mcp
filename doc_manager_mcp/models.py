"""Pydantic models for doc-manager MCP server tool inputs."""

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .constants import ChangeDetectionMode, DocumentationPlatform, QualityCriterion
from .indexing.analysis.semantic_diff import SemanticChange


def _validate_project_path(v: str) -> str:
    """Shared validator for project_path fields (FR-001, FR-006).

    This function is reused across all input models to ensure consistent
    path validation and prevent path traversal attacks.

    Args:
        v: Project path string

    Returns:
        Validated absolute path string

    Raises:
        ValueError: If path contains traversal sequences, doesn't exist, or isn't a directory
    """
    if not v:
        raise ValueError("Project path cannot be empty")

    # Check for path traversal sequences
    if '..' in v:
        raise ValueError(
            "Invalid project path: contains path traversal sequence '..'. "
            "Use absolute paths only to prevent directory traversal attacks."
        )

    # Convert to Path and verify it's absolute
    path = Path(v)
    if not path.is_absolute():
        raise ValueError(
            f"Invalid project path: must be absolute path (e.g., '/home/user/project' or 'C:\\\\Users\\\\user\\\\project'). "
            f"Got relative path: '{v}'"
        )

    # Verify path exists
    if not path.exists():
        raise ValueError(f"Project path does not exist: {v}")

    # Verify it's a directory
    if not path.is_dir():
        raise ValueError(f"Project path is not a directory: {v}")

    return str(path.resolve())


def _validate_relative_path(v: str | None, field_name: str = "path") -> str | None:
    """Shared validator for relative path fields (FR-001).

    Args:
        v: Relative path string or None
        field_name: Name of the field for error messages

    Returns:
        Validated relative path string or None

    Raises:
        ValueError: If path contains traversal sequences or is absolute
    """
    if v is None:
        return v

    # Check for path traversal sequences
    if '..' in v:
        raise ValueError(
            f"Invalid {field_name}: contains path traversal sequence '..'. "
            f"Use relative paths within project only"
        )

    # Verify it's not an absolute path
    path = Path(v)
    if path.is_absolute():
        raise ValueError(
            f"Invalid {field_name}: must be relative to project root, not absolute. "
            f"Got: '{v}'"
        )

    # Normalize path separators
    return str(path)


def _validate_glob_pattern(pattern: str, field_name: str = "pattern") -> None:
    """Validate glob pattern to prevent ReDoS and enforce length limits (FR-007, FR-008).

    Args:
        pattern: Glob pattern string
        field_name: Name of the field for error messages

    Raises:
        ValueError: If pattern is dangerous or too long
    """
    # Check pattern length (FR-007)
    max_pattern_length = 512
    if len(pattern) > max_pattern_length:
        raise ValueError(
            f"Invalid {field_name}: pattern too long ({len(pattern)} chars). "
            f"Maximum allowed: {max_pattern_length} characters"
        )

    # Check for ReDoS-vulnerable patterns (FR-008)
    # Detect nested quantifiers like (a+)+ or (a*)*
    redos_patterns = [
        r'\([^)]*[+*][^)]*\)[+*{]',  # Nested quantifiers: (a+)+ or (a*)*
        r'\([^)]*[+*{][^)]*\)[+*{]',  # Nested quantifiers with braces
        r'(\*\*){2,}',  # Multiple consecutive ** (globstar abuse)
    ]

    for redos_pattern in redos_patterns:
        if re.search(redos_pattern, pattern):
            raise ValueError(
                f"Invalid {field_name}: pattern contains potentially dangerous nested quantifiers. "
                f"This could cause Regular Expression Denial of Service (ReDoS). "
                f"Pattern: '{pattern}'"
            )


def _validate_pattern_list(
    patterns: list[str] | None,
    field_name: str = "patterns",
    max_items: int = 50
) -> list[str] | None:
    """Validate list of glob patterns (FR-006, FR-007, FR-008).

    Args:
        patterns: List of glob patterns or None
        field_name: Name of the field for error messages
        max_items: Maximum number of patterns allowed

    Returns:
        Validated pattern list or None

    Raises:
        ValueError: If list exceeds max items or contains invalid patterns
    """
    if patterns is None:
        return None

    # Check list length (FR-006)
    if len(patterns) > max_items:
        raise ValueError(
            f"Invalid {field_name}: too many items ({len(patterns)}). "
            f"Maximum allowed: {max_items}"
        )

    # Validate each pattern
    for i, pattern in enumerate(patterns):
        if not pattern or not isinstance(pattern, str):
            raise ValueError(
                f"Invalid {field_name}[{i}]: pattern must be non-empty string"
            )

        # Validate pattern safety and length
        _validate_glob_pattern(pattern, f"{field_name}[{i}]")

    return patterns


class InitializeConfigInput(BaseModel):
    """Input for initializing .doc-manager.yml configuration."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory (e.g., '/home/user/my-project', 'C:\\Users\\user\\project')",
        min_length=1
    )
    platform: DocumentationPlatform | None = Field(
        default=None,
        description="Documentation platform to use. If not specified, will be auto-detected. Options: hugo, docusaurus, mkdocs, sphinx, vitepress, jekyll, gitbook"
    )
    exclude_patterns: list[str] | None = Field(
        default_factory=list,  # Empty list - tools will merge with DEFAULT_EXCLUDE_PATTERNS
        description="Glob patterns to exclude from documentation analysis",
        max_length=50
    )
    docs_path: str | None = Field(
        default=None,
        description="Path to documentation directory (relative to project root). If not specified, will be auto-detected",
        min_length=1
    )
    sources: list[str] | None = Field(
        default=None,
        description="Source file patterns to track for documentation (e.g., 'src/**/*.py')",
        max_length=50
    )
    include_root_readme: bool = Field(
        default=False,
        description="Include root README.md in documentation operations (validation, quality assessment, change detection)"
    )
    use_gitignore: bool = Field(
        default=False,
        description="Automatically exclude files based on .gitignore patterns (opt-in). Priority: user excludes > gitignore > defaults"
    )
    doc_mappings: dict[str, str] | None = Field(
        default=None,
        description="Map change categories to documentation file paths (e.g., {'cli': 'docs/reference/commands.md', 'api': 'docs/reference/api.md'}). Supports non-standard layouts"
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        """Validate project path using shared validator (FR-001, FR-006)."""
        return _validate_project_path(v)

    @field_validator('docs_path')
    @classmethod
    def validate_docs_path(cls, v: str | None) -> str | None:
        """Validate docs path using shared validator (FR-001)."""
        return _validate_relative_path(v, field_name="docs_path")

    @field_validator('exclude_patterns')
    @classmethod
    def validate_exclude_patterns(cls, v: list[str] | None) -> list[str] | None:
        """Validate exclude patterns (FR-006, FR-007, FR-008) (T036)."""
        return _validate_pattern_list(v, field_name="exclude_patterns", max_items=50)

    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v: list[str] | None) -> list[str] | None:
        """Validate source patterns (FR-006, FR-007, FR-008) (T037)."""
        return _validate_pattern_list(v, field_name="sources", max_items=50)

class InitializeMemoryInput(BaseModel):
    """Input for initializing memory system."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        """Validate project path using shared validator (FR-001, FR-006)."""
        return _validate_project_path(v)

class DetectPlatformInput(BaseModel):
    """Input for platform detection."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )

class AssessQualityInput(BaseModel):
    """Input for quality assessment."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    docs_path: str | None = Field(
        default=None,
        description="Path to documentation directory relative to project root (e.g., 'docs/', 'documentation/'). If not specified, will be auto-detected"
    )
    criteria: list[QualityCriterion] | None = Field(
        default=None,
        description="Specific criteria to assess. If not specified, all 7 criteria will be assessed"
    )
    include_root_readme: bool = Field(
        default=False,
        description="Include root README.md in quality assessment (Bug #4 fix: sync discrepancy)"
    )

class ValidateDocsInput(BaseModel):
    """Input for documentation validation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    docs_path: str | None = Field(
        default=None,
        description="Path to documentation directory relative to project root"
    )
    check_links: bool = Field(
        default=True,
        description="Check for broken internal and external links"
    )
    check_assets: bool = Field(
        default=True,
        description="Validate asset links and alt text"
    )
    check_snippets: bool = Field(
        default=True,
        description="Extract and validate code snippets"
    )
    validate_code_syntax: bool = Field(
        default=False,
        description="Validate code example syntax using TreeSitter (semantic validation)"
    )
    validate_symbols: bool = Field(
        default=False,
        description="Validate that documented symbols (functions/classes) exist in codebase"
    )
    include_root_readme: bool = Field(
        default=False,
        description="Include root README.md in validation (Bug #4 fix: sync discrepancy)"
    )
    incremental: bool = Field(
        default=False,
        description="Only validate files that changed since last baseline (5-10x faster)"
    )

class MapChangesInput(BaseModel):
    """Input for mapping code changes to documentation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    since_commit: str | None = Field(
        default=None,
        description="Git commit hash to compare from. If not specified, uses checksums from memory"
    )
    mode: ChangeDetectionMode = Field(
        default=ChangeDetectionMode.CHECKSUM,
        description="Change detection mode: 'checksum' for file hash comparison or 'git_diff' for git-based diff. Note: use underscore, not hyphen (git_diff, not git-diff)"
    )
    include_semantic: bool = Field(
        default=False,
        description="Enable semantic code change detection (TreeSitter-based). Detects function signature changes, new classes, deleted methods, etc. Warning: May increase processing time for large codebases"
    )

    @field_validator('mode', mode='before')
    @classmethod
    def validate_mode(cls, v: str | ChangeDetectionMode) -> ChangeDetectionMode:
        """Validate change detection mode with helpful error messages.

        Args:
            v: Mode string or enum value

        Returns:
            Validated ChangeDetectionMode enum

        Raises:
            ValueError: If mode is invalid, with suggestions for correction
        """
        if isinstance(v, ChangeDetectionMode):
            return v

        # Common mistakes mapping
        mode_suggestions = {
            'git': 'git_diff',
            'git-diff': 'git_diff',
            'diff': 'git_diff',
            'git diff': 'git_diff',
            'hash': 'checksum',
            'checksums': 'checksum',
        }

        # Try to match against valid modes
        try:
            return ChangeDetectionMode(v)
        except ValueError:
            # Provide helpful suggestion if available
            suggestion = mode_suggestions.get(v.lower() if isinstance(v, str) else v)
            valid_modes = ', '.join([f"'{m.value}'" for m in ChangeDetectionMode])

            if suggestion:
                raise ValueError(
                    f"Invalid mode: '{v}'. Did you mean '{suggestion}'? "
                    f"Valid modes: {valid_modes}"
                ) from None
            else:
                raise ValueError(
                    f"Invalid mode: '{v}'. Valid modes: {valid_modes}"
                ) from None

    @field_validator('since_commit')
    @classmethod
    def validate_commit_hash(cls, v: str | None) -> str | None:
        """Validate git commit hash format to prevent command injection (FR-002).

        Args:
            v: Commit hash string or None

        Returns:
            Validated commit hash or None

        Raises:
            ValueError: If commit hash format is invalid

        Security:
            Prevents command injection by validating git commit hash format.
            Only allows 7-40 hexadecimal characters (standard git hash format).
            Rejects shell metacharacters and special sequences.
        """
        if v is None:
            return v

        # Validate format: 7-40 hexadecimal characters (short or full SHA)
        if not re.match(r'^[0-9a-fA-F]{7,40}$', v):
            raise ValueError(
                f"Invalid git commit hash format: '{v}'. "
                f"Expected 7-40 hexadecimal characters (e.g., 'abc1234' or full SHA). "
                f"Git refs like 'HEAD~3' are not accepted to prevent command injection attacks."
            )

        return v

    @model_validator(mode='after')
    def validate_mode_requirements(self) -> 'MapChangesInput':
        """Validate that mode-specific requirements are met.

        Raises:
            ValueError: If git_diff mode is used without since_commit
        """
        if self.mode == ChangeDetectionMode.GIT_DIFF and self.since_commit is None:
            raise ValueError(
                "since_commit is required when mode='git_diff'. "
                "Provide a git commit SHA (e.g., 'abc1234') to compare from. "
                "Use mode='checksum' if you want to compare against memory baseline instead."
            )

        return self

class MapChangesOutput(BaseModel):
    """Output model for map_changes tool JSON responses.

    This model represents the structured response when map_changes returns
    a dictionary (JSON format). It includes both file-level changes and
    optional semantic changes when include_semantic=True.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    analyzed_at: str = Field(
        ...,
        description="ISO 8601 timestamp when the analysis was performed"
    )
    baseline_commit: str | None = Field(
        default=None,
        description="Git commit SHA used as baseline (null if using checksum mode)"
    )
    baseline_created: str | None = Field(
        default=None,
        description="ISO 8601 timestamp when baseline was created (null if git mode)"
    )
    changes_detected: bool = Field(
        ...,
        description="Whether any changes were detected"
    )
    total_changes: int = Field(
        ...,
        description="Total number of changed files detected"
    )
    changed_files: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of files that changed with their paths and change types"
    )
    affected_documentation: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of documentation files affected by the code changes"
    )
    semantic_changes: list[SemanticChange] = Field(
        default_factory=list,
        description="Code-level semantic changes detected (function signatures, classes, methods). Only populated when include_semantic=True in the request"
    )

class TrackDependenciesInput(BaseModel):
    """Input for tracking code-to-docs dependencies."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    docs_path: str | None = Field(
        default=None,
        description="Path to documentation directory (relative to project root). If not specified, will be auto-detected",
        min_length=1
    )

class BootstrapInput(BaseModel):
    """Input for bootstrapping fresh documentation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    platform: DocumentationPlatform | None = Field(
        default=None,
        description="Documentation platform to use. If not specified, will be auto-detected and recommended"
    )
    docs_path: str = Field(
        default="docs",
        description="Path where documentation should be created (relative to project root)",
        min_length=1
    )

class MigrateInput(BaseModel):
    """Input for migrating existing documentation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    source_path: str = Field(
        ...,
        description="Path to existing documentation directory (relative to project root)",
        min_length=1
    )
    target_path: str = Field(
        default="docs",
        description="Path where migrated documentation should be created (relative to project root)",
        min_length=1
    )
    target_platform: DocumentationPlatform | None = Field(
        default=None,
        description="Target platform for migration. If not specified, will preserve existing platform"
    )
    preserve_history: bool = Field(
        default=True,
        description="Use git mv to preserve file history during migration"
    )
    rewrite_links: bool = Field(
        default=False,
        description="Automatically rewrite internal links when migrating documentation to new structure"
    )
    regenerate_toc: bool = Field(
        default=False,
        description="Regenerate table of contents for each migrated file using <!-- TOC --> markers"
    )
    dry_run: bool = Field(
        default=False,
        description="Preview migration changes without modifying files. Shows what would be changed."
    )

class SyncInput(BaseModel):
    """Input for synchronizing documentation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    mode: str = Field(
        default="check",
        description="Sync mode: 'check' (read-only analysis) or 'resync' (update baselines + analysis)",
        pattern="^(check|resync)$"
    )
    docs_path: str | None = Field(
        default=None,
        description="Path to documentation directory (relative to project root). If not specified, will be auto-detected",
        min_length=1
    )


# ============================================================================
# New Input Models for Refactored Tools (002-tool-architecture-refactor)
# ============================================================================

class DocmgrInitInput(BaseModel):
    """Input for unified initialization tool (docmgr_init).

    Replaces: initialize_config, initialize_memory, bootstrap

    Modes:
    - mode="existing": Initialize config + baselines + dependencies for existing project
    - mode="bootstrap": Same as existing + create doc templates
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    mode: str = Field(
        default="existing",
        description="Init mode: 'existing' (config+baselines+deps) or 'bootstrap' (+ doc templates)",
        pattern="^(existing|bootstrap)$"
    )
    platform: DocumentationPlatform | None = Field(
        default=None,
        description="Documentation platform (mkdocs, docusaurus, etc.)"
    )
    exclude_patterns: list[str] | None = Field(
        default_factory=list,
        description="Glob patterns for files to exclude from documentation tracking",
        max_length=50
    )
    docs_path: str | None = Field(
        default=None,
        description="Path to documentation directory (relative to project root)",
        min_length=1
    )
    sources: list[str] | None = Field(
        default=None,
        description="Source file patterns to track (e.g., ['src/**/*.py'])",
        max_length=50
    )
    include_root_readme: bool = Field(
        default=False,
        description="Include root README.md in documentation operations (validation, quality assessment, change detection)"
    )
    use_gitignore: bool = Field(
        default=False,
        description="Automatically exclude files based on .gitignore patterns (opt-in). Priority: user excludes > gitignore > defaults"
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        return _validate_project_path(v)

    @field_validator('docs_path')
    @classmethod
    def validate_docs_path(cls, v: str | None) -> str | None:
        return _validate_relative_path(v, field_name="docs_path")

    @field_validator('exclude_patterns')
    @classmethod
    def validate_exclude_patterns(cls, v: list[str] | None) -> list[str] | None:
        return _validate_pattern_list(v, field_name="exclude_patterns")

    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v: list[str] | None) -> list[str] | None:
        return _validate_pattern_list(v, field_name="sources")


class DocmgrDetectChangesInput(BaseModel):
    """Input for pure read-only change detection (docmgr_detect_changes).

    Replaces: map_changes (in read-only mode)

    Key difference: NEVER writes to symbol-baseline.json
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    since_commit: str | None = Field(
        default=None,
        description="Git commit SHA to compare from (only for git_diff mode)"
    )
    mode: ChangeDetectionMode = Field(
        default=ChangeDetectionMode.CHECKSUM,
        description="Detection mode: 'checksum' (file checksums) or 'git_diff' (git changes)"
    )
    include_semantic: bool = Field(
        default=False,
        description="Include semantic diff analysis (TreeSitter AST comparison)"
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        return _validate_project_path(v)


class DocmgrUpdateBaselineInput(BaseModel):
    """Input for updating all baseline files atomically (docmgr_update_baseline).

    Updates:
    - repo-baseline.json (file checksums)
    - symbol-baseline.json (TreeSitter code symbols)
    - dependencies.json (code-to-doc mappings)
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    project_path: str = Field(
        ...,
        description="Absolute path to project root directory",
        min_length=1
    )
    docs_path: str | None = Field(
        default=None,
        description="Path to documentation directory (relative to project root)",
        min_length=1
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        return _validate_project_path(v)

    @field_validator('docs_path')
    @classmethod
    def validate_docs_path(cls, v: str | None) -> str | None:
        return _validate_relative_path(v, field_name="docs_path")


# ============================================================================
# Documentation Conventions Models (chore/integrating-doc-conventions)
# ============================================================================

class TerminologyRule(BaseModel):
    """Single terminology rule with optional exceptions and context."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    word: str = Field(
        ...,
        description="Word or phrase to avoid",
        min_length=1
    )
    reason: str | None = Field(
        default=None,
        description="Explanation of why this term should be avoided"
    )
    exceptions: list[str] = Field(
        default_factory=list,
        description="Phrases that should not be flagged (e.g., 'just-in-time' when avoiding 'just')"
    )


class PreferredTerminology(BaseModel):
    """Preferred terminology definition for consistency checking."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    full_form: str = Field(
        ...,
        description="Full form of the term (e.g., 'Model Context Protocol')",
        min_length=1
    )
    abbreviation: str | None = Field(
        default=None,
        description="Abbreviated form (e.g., 'MCP')"
    )
    guidance: str | None = Field(
        default=None,
        description="Usage guidance (e.g., 'Spell out on first use, abbreviate after')"
    )


class StyleConventions(BaseModel):
    """Style-related documentation conventions."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    class HeadingConfig(BaseModel):
        """Heading style configuration."""
        model_config = ConfigDict(extra='forbid')

        case: Literal["sentence_case", "title_case", "lower", "upper"] | None = Field(
            default=None,
            description="Required heading case style"
        )
        consistency_required: bool = Field(
            default=True,
            description="Enforce consistent heading case throughout project"
        )

    class CodeConfig(BaseModel):
        """Code formatting configuration."""
        model_config = ConfigDict(extra='forbid')

        inline_format: Literal["backticks", "html"] = Field(
            default="backticks",
            description="Format for inline code references"
        )
        block_language_required: bool = Field(
            default=True,
            description="Require language specification in code blocks"
        )

    class VoiceConfig(BaseModel):
        """Writing voice configuration."""
        model_config = ConfigDict(extra='forbid')

        person: Literal["first", "second", "third"] = Field(
            default="second",
            description="Grammatical person for documentation"
        )
        active_voice_preferred: bool = Field(
            default=True,
            description="Prefer active voice over passive"
        )

    headings: HeadingConfig = Field(
        default_factory=HeadingConfig,
        description="Heading style rules"
    )
    code: CodeConfig = Field(
        default_factory=CodeConfig,
        description="Code formatting rules"
    )
    voice: VoiceConfig = Field(
        default_factory=VoiceConfig,
        description="Writing voice rules"
    )


class StructureConventions(BaseModel):
    """Structure-related documentation conventions."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    class TocConfig(BaseModel):
        """Table of contents configuration."""
        model_config = ConfigDict(extra='forbid')

        enabled: bool = Field(
            default=True,
            description="Whether to require TOC"
        )
        min_length: int = Field(
            default=500,
            description="Minimum document length (words) to require TOC",
            ge=0
        )

    require_intro: bool = Field(
        default=True,
        description="Require introductory paragraph before first heading"
    )
    require_toc: TocConfig = Field(
        default_factory=TocConfig,
        description="Table of contents requirements"
    )
    max_heading_depth: int | None = Field(
        default=3,
        description="Maximum heading depth (1-6)",
        ge=1,
        le=6
    )
    heading_hierarchy: Literal["strict", "relaxed"] = Field(
        default="strict",
        description="Enforce strict heading hierarchy (no level skipping)"
    )


class QualityConventions(BaseModel):
    """Quality-related documentation conventions."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    class SentenceConfig(BaseModel):
        """Sentence length configuration."""
        model_config = ConfigDict(extra='forbid')

        max_length: int | None = Field(
            default=25,
            description="Maximum sentence length in words",
            ge=1
        )
        min_length: int | None = Field(
            default=3,
            description="Minimum sentence length in words",
            ge=1
        )

    class ParagraphConfig(BaseModel):
        """Paragraph length configuration."""
        model_config = ConfigDict(extra='forbid')

        max_length: int | None = Field(
            default=150,
            description="Maximum paragraph length in words",
            ge=1
        )

    class LinkConfig(BaseModel):
        """Link validation configuration."""
        model_config = ConfigDict(extra='forbid')

        validate_links: bool = Field(
            default=True,
            description="Validate all links are reachable"
        )

    class ImageConfig(BaseModel):
        """Image validation configuration."""
        model_config = ConfigDict(extra='forbid')

        require_alt_text: bool = Field(
            default=True,
            description="All images must have descriptive alt text"
        )

    class CodeQualityConfig(BaseModel):
        """Code quality validation configuration."""
        model_config = ConfigDict(extra='forbid')

        validate_syntax: bool = Field(
            default=False,
            description="Validate code syntax (expensive, requires TreeSitter)"
        )

    sentences: SentenceConfig = Field(
        default_factory=SentenceConfig,
        description="Sentence length rules"
    )
    paragraphs: ParagraphConfig = Field(
        default_factory=ParagraphConfig,
        description="Paragraph length rules"
    )
    links: LinkConfig = Field(
        default_factory=LinkConfig,
        description="Link validation rules"
    )
    images: ImageConfig = Field(
        default_factory=ImageConfig,
        description="Image validation rules"
    )
    code: CodeQualityConfig = Field(
        default_factory=CodeQualityConfig,
        description="Code quality validation rules"
    )


class TerminologyConventions(BaseModel):
    """Terminology-related documentation conventions."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    preferred: dict[str, PreferredTerminology] = Field(
        default_factory=dict,
        description="Preferred terminology for consistency (detection only)"
    )
    avoid: list[TerminologyRule] = Field(
        default_factory=list,
        description="Words/phrases to avoid (flagged as warnings)"
    )


class DocumentationConventions(BaseModel):
    """Complete documentation conventions configuration.

    This model represents the schema for doc-conventions.yml files.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    style: StyleConventions = Field(
        default_factory=StyleConventions,
        description="Style conventions (headings, code, voice)"
    )
    structure: StructureConventions = Field(
        default_factory=StructureConventions,
        description="Structure conventions (intro, TOC, hierarchy)"
    )
    quality: QualityConventions = Field(
        default_factory=QualityConventions,
        description="Quality conventions (sentences, links, images)"
    )
    terminology: TerminologyConventions = Field(
        default_factory=TerminologyConventions,
        description="Terminology conventions (preferred terms, words to avoid)"
    )
