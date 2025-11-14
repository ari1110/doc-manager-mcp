"""Pydantic models for doc-manager MCP server tool inputs."""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from .constants import ResponseFormat, DocumentationPlatform, QualityCriterion, ChangeDetectionMode

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
