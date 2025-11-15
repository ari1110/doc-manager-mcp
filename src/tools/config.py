"""Configuration management tools for doc-manager."""

from pathlib import Path
from datetime import datetime

from ..models import InitializeConfigInput
from ..constants import DocumentationPlatform, ResponseFormat
from ..utils import detect_project_language, find_docs_directory, save_config, handle_error, enforce_response_limit, safe_json_dumps

async def initialize_config(params: InitializeConfigInput) -> str:
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
            return enforce_response_limit(
                f"Error: Project path does not exist: {project_path}\n"
                f"→ Please verify the path and try again with an existing directory."
            )

        if not project_path.is_dir():
            return enforce_response_limit(
                f"Error: Project path is not a directory: {project_path}\n"
                f"→ Please provide a path to a directory, not a file."
            )

        # Check if config already exists (allow overwrite)
        config_path = project_path / ".doc-manager.yml"

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
        language = detect_project_language(project_path)

        # Find docs directory (use provided path or auto-detect)
        if params.docs_path:
            docs_path = params.docs_path
        else:
            docs_dir = find_docs_directory(project_path)
            docs_path = str(docs_dir.relative_to(project_path)) if docs_dir else "docs"

        # Use provided sources or empty list
        sources = params.sources if params.sources else []

        # Create configuration
        config = {
            "platform": platform.value,
            "exclude": params.exclude_patterns,
            "sources": sources,
            "docs_path": docs_path,
            "metadata": {
                "language": language,
                "created": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }

        # Save configuration
        if not save_config(project_path, config):
            return enforce_response_limit("Error: Failed to write configuration file")

        # Return JSON or Markdown based on response_format
        if params.response_format == ResponseFormat.JSON:
            return enforce_response_limit(safe_json_dumps({
                "status": "success",
                "message": "Configuration created successfully",
                "config_path": str(config_path),
                "platform": platform.value,
                "docs_path": docs_path,
                "language": language,
                "exclude_patterns": len(params.exclude_patterns),
                "sources": len(sources)
            }, indent=2))
        else:
            return enforce_response_limit(f"""✓ Configuration created successfully

**Configuration Summary:**
- Platform: {platform.value}
- Documentation Path: {docs_path}
- Primary Language: {language}
- Exclude Patterns: {len(params.exclude_patterns)} patterns
- Source Patterns: {len(sources)} patterns

Next steps:
1. Run `docmgr_initialize_memory` to set up the memory system
2. Run `docmgr_bootstrap` to generate documentation (if starting fresh)
3. Run `docmgr_migrate` to restructure existing documentation (if docs exist)
""")

    except Exception as e:
        return enforce_response_limit(handle_error(e, "initialize_config"))
