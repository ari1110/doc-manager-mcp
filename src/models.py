"""Pydantic models for doc-manager MCP server tool inputs."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from pathlib import Path

from .constants import ResponseFormat, DocumentationPlatform, QualityCriterion, ChangeDetectionMode


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
            f"Invalid project path: contains path traversal sequence '..'. "
            f"Use absolute paths only to prevent directory traversal attacks."
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


def _validate_relative_path(v: Optional[str], field_name: str = "path") -> Optional[str]:
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
    platform: Optional[DocumentationPlatform] = Field(
        default=None,
        description="Documentation platform to use. If not specified, will be auto-detected. Options: hugo, docusaurus, mkdocs, sphinx, vitepress, jekyll, gitbook"
    )
    exclude_patterns: Optional[List[str]] = Field(
        default_factory=lambda: ["**/node_modules", "**/dist", "**/vendor", "**/*.log", "**/.git"],
        description="Glob patterns to exclude from documentation analysis",
        max_length=50
    )
    docs_path: Optional[str] = Field(
        default=None,
        description="Path to documentation directory (relative to project root). If not specified, will be auto-detected",
        min_length=1
    )
    sources: Optional[List[str]] = Field(
        default=None,
        description="Source file patterns to track for documentation (e.g., 'src/**/*.py')",
        max_length=50
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

    @field_validator('project_path')
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        """Validate project path using shared validator (FR-001, FR-006)."""
        return _validate_project_path(v)

    @field_validator('docs_path')
    @classmethod
    def validate_docs_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate docs path using shared validator (FR-001)."""
        return _validate_relative_path(v, field_name="docs_path")

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
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
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
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
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
    docs_path: Optional[str] = Field(
        default=None,
        description="Path to documentation directory relative to project root (e.g., 'docs/', 'documentation/'). If not specified, will be auto-detected"
    )
    criteria: Optional[List[QualityCriterion]] = Field(
        default=None,
        description="Specific criteria to assess. If not specified, all 7 criteria will be assessed"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
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
    docs_path: Optional[str] = Field(
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
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
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
    since_commit: Optional[str] = Field(
        default=None,
        description="Git commit hash to compare from. If not specified, uses checksums from memory"
    )
    mode: ChangeDetectionMode = Field(
        default=ChangeDetectionMode.CHECKSUM,
        description="Change detection mode: 'checksum' for file hash comparison or 'git_diff' for git-based diff"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )

    @field_validator('since_commit')
    @classmethod
    def validate_commit_hash(cls, v: Optional[str]) -> Optional[str]:
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
                f"This prevents command injection attacks."
            )

        return v

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
    docs_path: Optional[str] = Field(
        default=None,
        description="Path to documentation directory (relative to project root). If not specified, will be auto-detected",
        min_length=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
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
    platform: Optional[DocumentationPlatform] = Field(
        default=None,
        description="Documentation platform to use. If not specified, will be auto-detected and recommended"
    )
    docs_path: str = Field(
        default="docs",
        description="Path where documentation should be created (relative to project root)",
        min_length=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
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
    target_platform: Optional[DocumentationPlatform] = Field(
        default=None,
        description="Target platform for migration. If not specified, will preserve existing platform"
    )
    preserve_history: bool = Field(
        default=True,
        description="Use git mv to preserve file history during migration"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
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
        default="reactive",
        description="Sync mode: 'reactive' (manual trigger) or 'proactive' (auto-detect changes)",
        pattern="^(reactive|proactive)$"
    )
    docs_path: Optional[str] = Field(
        default=None,
        description="Path to documentation directory (relative to project root). If not specified, will be auto-detected",
        min_length=1
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )
