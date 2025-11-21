"""Core utilities for doc-manager MCP server.

This package contains focused modules for different utility categories:
- checksums: File checksum calculations
- git: Git command execution
- paths: Path resolution and validation
- patterns: Pattern matching utilities
- project: Project detection and analysis
- config: Configuration file management
- errors: Error handling and formatting
- resources: Resource limits and timeouts
- responses: Response formatting and limits
- security: Security utilities (file locking)
"""

# Checksums
from .checksums import calculate_checksum

# Configuration
from .config import load_config, save_config

# Conventions
from .conventions import (
    get_convention_summary,
    load_conventions,
    validate_against_conventions,
)

# Error handling
from .errors import handle_error

# Git operations
from .git import run_git_command

# Path utilities
from .paths import safe_resolve, validate_path_boundary

# Pattern matching
from .patterns import matches_exclude_pattern

# Project detection
from .project import (
    detect_platform_quick,
    detect_project_language,
    find_docs_directory,
    find_markdown_files,
    get_doc_relative_path,
    is_public_symbol,
)

# Resource management
from .resources import ResourceLimits, operation_timeout

# Response utilities
from .responses import enforce_response_limit, safe_json_dumps

# Security
from .security import file_lock

__all__ = [
    "ResourceLimits",
    "calculate_checksum",
    "detect_platform_quick",
    "detect_project_language",
    "enforce_response_limit",
    "file_lock",
    "find_docs_directory",
    "find_markdown_files",
    "get_convention_summary",
    "get_doc_relative_path",
    "handle_error",
    "is_public_symbol",
    "load_config",
    "load_conventions",
    "matches_exclude_pattern",
    "operation_timeout",
    "run_git_command",
    "safe_json_dumps",
    "safe_resolve",
    "save_config",
    "validate_against_conventions",
    "validate_path_boundary",
]
