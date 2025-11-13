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
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path
import json
import yaml
import hashlib
import subprocess
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("doc_manager_mcp")

# Constants
CHARACTER_LIMIT = 25000  # Maximum response size in characters
SUPPORTED_PLATFORMS = ["hugo", "docusaurus", "mkdocs", "sphinx", "vitepress", "jekyll", "gitbook"]
QUALITY_CRITERIA = ["relevance", "accuracy", "purposefulness", "uniqueness", "consistency", "clarity", "structure"]

# Enums
class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"

class DocumentationPlatform(str, Enum):
    """Supported documentation platforms."""
    HUGO = "hugo"
    DOCUSAURUS = "docusaurus"
    MKDOCS = "mkdocs"
    SPHINX = "sphinx"
    VITEPRESS = "vitepress"
    JEKYLL = "jekyll"
    GITBOOK = "gitbook"
    UNKNOWN = "unknown"

class QualityCriterion(str, Enum):
    """Quality assessment criteria."""
    RELEVANCE = "relevance"
    ACCURACY = "accuracy"
    PURPOSEFULNESS = "purposefulness"
    UNIQUENESS = "uniqueness"
    CONSISTENCY = "consistency"
    CLARITY = "clarity"
    STRUCTURE = "structure"

# ============================================================================
# Pydantic Models for Input Validation
# ============================================================================

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
        default_factory=lambda: ["**/node_modules", "**/dist", "**/vendor", "**/*.log"],
        description="Glob patterns to exclude from documentation analysis",
        max_items=50
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
    existing_docs_path: str = Field(
        ...,
        description="Path to existing documentation directory (relative to project root)",
        min_length=1
    )
    new_docs_path: str = Field(
        default="docs-new",
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
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format"
    )

# ============================================================================
# Utility Functions
# ============================================================================

def _calculate_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""

def _run_git_command(cwd: Path, *args) -> Optional[str]:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None

def _detect_project_language(project_path: Path) -> str:
    """Detect primary programming language of project."""
    language_indicators = {
        "go.mod": "Go",
        "package.json": "JavaScript/TypeScript",
        "Cargo.toml": "Rust",
        "requirements.txt": "Python",
        "setup.py": "Python",
        "pom.xml": "Java",
        "build.gradle": "Java",
        "Gemfile": "Ruby",
        "composer.json": "PHP"
    }

    for file, language in language_indicators.items():
        if (project_path / file).exists():
            return language

    return "Unknown"

def _find_docs_directory(project_path: Path) -> Optional[Path]:
    """Find documentation directory in project."""
    common_doc_dirs = ["docs", "doc", "documentation", "docsite", "website/docs"]

    for dir_name in common_doc_dirs:
        doc_path = project_path / dir_name
        if doc_path.exists() and doc_path.is_dir():
            return doc_path

    return None

def _load_config(project_path: Path) -> Optional[Dict[str, Any]]:
    """Load .doc-manager.yml configuration."""
    config_path = project_path / ".doc-manager.yml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None

def _save_config(project_path: Path, config: Dict[str, Any]) -> bool:
    """Save .doc-manager.yml configuration."""
    config_path = project_path / ".doc-manager.yml"
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception:
        return False

def _handle_error(e: Exception, context: str = "") -> str:
    """Consistent error formatting across all tools."""
    error_msg = f"Error: {type(e).__name__}"
    if context:
        error_msg += f" in {context}"
    error_msg += f": {str(e)}"
    return error_msg

# ============================================================================
# Tool Implementations
# ============================================================================

@mcp.tool(
    name="docmgr_initialize_config",
    annotations={
        "title": "Initialize Documentation Manager Configuration",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_initialize_config(params: InitializeConfigInput) -> str:
    """Initialize .doc-manager.yml configuration file for the project.

    This tool creates a new configuration file that defines how the documentation
    manager should operate for this project. It detects project characteristics
    and creates sensible defaults.

    Args:
        params (InitializeConfigInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - platform (Optional[DocumentationPlatform]): Platform to use (auto-detected if not specified)
            - exclude_patterns (Optional[List[str]]): Glob patterns to exclude

    Returns:
        str: Success message with configuration summary or error message

    Examples:
        - Use when: Setting up documentation management for a new project
        - Use when: Reconfiguring documentation settings
        - Don't use when: Configuration already exists and you just want to read it

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if unable to write configuration file
        - Validates all input parameters via Pydantic model
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return f"Error: Project path does not exist: {project_path}"

        if not project_path.is_dir():
            return f"Error: Project path is not a directory: {project_path}"

        # Check if config already exists
        config_path = project_path / ".doc-manager.yml"
        if config_path.exists():
            return f"Configuration already exists at {config_path}. Delete it first to reinitialize."

        # Detect platform if not specified
        platform = params.platform
        if not platform:
            # Try to detect platform
            if (project_path / "docsite" / "hugo.yaml").exists() or (project_path / "hugo.toml").exists():
                platform = DocumentationPlatform.HUGO
            elif (project_path / "docusaurus.config.js").exists():
                platform = DocumentationPlatform.DOCUSAURUS
            elif (project_path / "mkdocs.yml").exists():
                platform = DocumentationPlatform.MKDOCS
            elif (project_path / "conf.py").exists():
                platform = DocumentationPlatform.SPHINX
            else:
                platform = DocumentationPlatform.UNKNOWN

        # Detect project language
        language = _detect_project_language(project_path)

        # Find docs directory
        docs_dir = _find_docs_directory(project_path)
        docs_path = str(docs_dir.relative_to(project_path)) if docs_dir else "docs"

        # Create configuration
        config = {
            "platform": platform.value,
            "exclude": params.exclude_patterns,
            "sources": [],
            "docs_path": docs_path,
            "metadata": {
                "language": language,
                "created": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }

        # Save configuration
        if not _save_config(project_path, config):
            return "Error: Failed to write configuration file"

        return f"""✓ Created .doc-manager.yml configuration

**Configuration Summary:**
- Platform: {platform.value}
- Documentation Path: {docs_path}
- Primary Language: {language}
- Exclude Patterns: {len(params.exclude_patterns)} patterns

Next steps:
1. Run `docmgr_initialize_memory` to set up the memory system
2. Run `docmgr_bootstrap` to generate documentation (if starting fresh)
3. Run `docmgr_migrate` to restructure existing documentation (if docs exist)
"""

    except Exception as e:
        return _handle_error(e, "initialize_config")

@mcp.tool(
    name="docmgr_initialize_memory",
    annotations={
        "title": "Initialize Documentation Memory System",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_initialize_memory(params: InitializeMemoryInput) -> str:
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
        if memory_dir.exists():
            return f"Memory system already exists at {memory_dir}. Delete it first to reinitialize."

        # Create memory directory structure
        memory_dir.mkdir(parents=True, exist_ok=True)
        (memory_dir / "memory").mkdir(exist_ok=True)

        # Get project metadata
        repo_name = project_path.name
        language = _detect_project_language(project_path)
        docs_dir = _find_docs_directory(project_path)
        docs_exist = docs_dir is not None

        # Get git info
        git_commit = _run_git_command(project_path, "rev-parse", "HEAD")
        git_branch = _run_git_command(project_path, "rev-parse", "--abbrev-ref", "HEAD")

        # Calculate checksums for all files in project
        checksums = {}
        file_count = 0
        for file_path in project_path.rglob("*"):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                relative_path = file_path.relative_to(project_path)
                checksums[str(relative_path)] = _calculate_checksum(file_path)
                file_count += 1

        # Create repo baseline
        baseline = {
            "repo_name": repo_name,
            "description": f"Repository for {repo_name}",
            "language": language,
            "docs_exist": docs_exist,
            "docs_path": str(docs_dir.relative_to(project_path)) if docs_dir else None,
            "git_commit": git_commit,
            "git_branch": git_branch,
            "created_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "file_count": file_count,
            "checksums": checksums
        }

        baseline_path = memory_dir / "memory" / "repo-baseline.json"
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(baseline, f, indent=2)

        # Create doc conventions template
        conventions = """# Documentation Conventions

## Style Guide

### Voice and Tone
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

        return f"""✓ Initialized documentation memory system

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
        return _handle_error(e, "initialize_memory")

@mcp.tool(
    name="docmgr_detect_platform",
    annotations={
        "title": "Detect Documentation Platform",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_detect_platform(params: DetectPlatformInput) -> str:
    """Detect and recommend documentation platform for the project.

    This tool analyzes the project structure to detect existing documentation
    platforms or recommend the most suitable platform based on project characteristics.

    Args:
        params (DetectPlatformInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - response_format (ResponseFormat): Output format (markdown or json)

    Returns:
        str: Platform detection results with recommendation and rationale

    Examples:
        - Use when: Choosing a documentation platform for a new project
        - Use when: Migrating from one platform to another
        - Use when: Verifying current platform detection

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns "unknown" platform if no platform detected
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return f"Error: Project path does not exist: {project_path}"

        # Platform detection logic
        detected_platforms = []

        # Hugo detection
        if (project_path / "hugo.toml").exists() or (project_path / "hugo.yaml").exists() or (project_path / "config.toml").exists():
            detected_platforms.append({
                "platform": "hugo",
                "confidence": "high",
                "evidence": ["Found Hugo configuration file"]
            })

        # Docusaurus detection
        if (project_path / "docusaurus.config.js").exists() or (project_path / "docusaurus.config.ts").exists():
            detected_platforms.append({
                "platform": "docusaurus",
                "confidence": "high",
                "evidence": ["Found Docusaurus configuration file"]
            })

        # MkDocs detection
        if (project_path / "mkdocs.yml").exists():
            detected_platforms.append({
                "platform": "mkdocs",
                "confidence": "high",
                "evidence": ["Found mkdocs.yml configuration"]
            })

        # Sphinx detection
        if (project_path / "docs" / "conf.py").exists() or (project_path / "doc" / "conf.py").exists():
            detected_platforms.append({
                "platform": "sphinx",
                "confidence": "high",
                "evidence": ["Found Sphinx conf.py"]
            })

        # VitePress detection
        if (project_path / ".vitepress" / "config.js").exists() or (project_path / ".vitepress" / "config.ts").exists():
            detected_platforms.append({
                "platform": "vitepress",
                "confidence": "high",
                "evidence": ["Found VitePress configuration"]
            })

        # Determine recommendation
        language = _detect_project_language(project_path)
        recommendation = None
        rationale = []

        if detected_platforms:
            # Use detected platform
            recommendation = detected_platforms[0]["platform"]
            rationale.append(f"Detected existing {recommendation} platform")
        else:
            # Recommend based on project characteristics
            if language == "Go":
                recommendation = "hugo"
                rationale.append("Hugo is written in Go and popular in Go ecosystem")
            elif language in ["JavaScript/TypeScript", "Node.js"]:
                recommendation = "docusaurus"
                rationale.append("Docusaurus is React-based and popular in JavaScript ecosystem")
            elif language == "Python":
                recommendation = "mkdocs"
                rationale.append("MkDocs is Python-based and popular in Python ecosystem")
            else:
                recommendation = "hugo"
                rationale.append("Hugo is fast, language-agnostic, and widely adopted")

        # Format response
        if params.response_format == ResponseFormat.JSON:
            result = {
                "detected_platforms": detected_platforms,
                "recommendation": recommendation,
                "rationale": rationale,
                "project_language": language
            }
            return json.dumps(result, indent=2)
        else:
            lines = ["# Documentation Platform Detection", ""]

            if detected_platforms:
                lines.append("## Detected Platforms")
                for platform in detected_platforms:
                    lines.append(f"- **{platform['platform'].upper()}** ({platform['confidence']} confidence)")
                    for evidence in platform['evidence']:
                        lines.append(f"  - {evidence}")
                lines.append("")

            lines.append("## Recommendation")
            lines.append(f"**{recommendation.upper()}**")
            lines.append("")
            lines.append("### Rationale:")
            for reason in rationale:
                lines.append(f"- {reason}")
            lines.append("")
            lines.append(f"### Project Context:")
            lines.append(f"- Primary Language: {language}")

            return "\n".join(lines)

    except Exception as e:
        return _handle_error(e, "detect_platform")

if __name__ == "__main__":
    mcp.run()
