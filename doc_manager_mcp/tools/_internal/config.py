"""Configuration management tools for doc-manager."""

from datetime import datetime
from pathlib import Path
from typing import Any

from doc_manager_mcp.core import (
    detect_platform_quick,
    detect_project_language,
    enforce_response_limit,
    find_docs_directory,
    handle_error,
    save_config,
)
from doc_manager_mcp.models import InitializeConfigInput


def _generate_default_doc_mappings(docs_path: str) -> dict[str, str]:
    """Generate sensible default documentation path mappings.

    Creates mappings from change categories to likely documentation file paths
    based on the docs directory structure.

    Args:
        docs_path: Path to documentation directory (e.g., 'docs', 'documentation', 'wiki')

    Returns:
        Dictionary mapping categories to doc paths
    """
    base = docs_path.rstrip("/")  # Remove trailing slash if present

    return {
        "cli": f"{base}/reference/command-reference.md",
        "api": f"{base}/reference/api.md",
        "config": f"{base}/reference/configuration.md",
        "dependency": f"{base}/getting-started/installation.md",
        "infrastructure": f"{base}/development/ci-cd.md",
    }


async def initialize_config(params: InitializeConfigInput) -> str | dict[str, Any]:
    """Initialize .doc-manager.yml configuration file for the project.

    INTERNAL USE ONLY: This function is not exposed as an MCP tool in v2.0.0.
    Use docmgr_init(mode="existing") instead, which calls this internally.

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
            platform = detect_platform_quick(project_path)

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

        # Generate doc_mappings (use provided or generate defaults)
        if params.doc_mappings:
            doc_mappings = params.doc_mappings
        else:
            doc_mappings = _generate_default_doc_mappings(docs_path)

        # Create configuration
        config = {
            "platform": platform.value,
            "exclude": params.exclude_patterns or [],  # Ensure list, not None
            "sources": sources,
            "docs_path": docs_path,
            "use_gitignore": params.use_gitignore,
            "doc_mappings": doc_mappings,
            "metadata": {
                "language": language,
                "created": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }

        # Save configuration
        if not save_config(project_path, config):
            return enforce_response_limit("Error: Failed to write configuration file")

        # Return structured data
        return {
            "status": "success",
            "message": "Configuration created successfully",
            "config_path": str(config_path),
            "platform": platform.value,
            "docs_path": docs_path,
            "language": language,
            "exclude_patterns": len(params.exclude_patterns or []),
            "sources": len(sources)
        }

    except Exception as e:
        return enforce_response_limit(handle_error(e, "initialize_config"))
