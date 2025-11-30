"""Configuration file management utilities.

This module provides utilities for loading and saving .doc-manager.yml
configuration files with helpful examples and documentation.
"""

from pathlib import Path
from typing import Any

import yaml


def load_config(project_path: Path) -> dict[str, Any] | None:
    """Load .doc-manager.yml configuration.

    Normalizes None values to empty lists for fields that consumers expect to be lists.
    This handles configs where empty lists were saved as 'null' for YAML aesthetics.
    """
    config_path = project_path / ".doc-manager.yml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)

            if config:
                # Normalize None to empty lists for expected list fields
                # Fixes: dict.get("key", []) returns None when key exists with None value
                if config.get('exclude') is None:
                    config['exclude'] = []
                if config.get('sources') is None:
                    config['sources'] = []

                # Normalize api_coverage section
                if config.get('api_coverage'):
                    api_coverage = config['api_coverage']
                    if api_coverage.get('exclude_symbols') is None:
                        api_coverage['exclude_symbols'] = []
                    if api_coverage.get('include_symbols') is None:
                        api_coverage['include_symbols'] = []

            return config
    except Exception:
        return None


def save_config(project_path: Path, config: dict[str, Any]) -> bool:
    """Save .doc-manager.yml configuration with helpful examples."""
    config_path = project_path / ".doc-manager.yml"
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            # Write main configuration with custom formatting for empty lists
            config_copy = config.copy()
            # Replace empty lists with None so they appear as empty lines instead of []
            if not config_copy.get('exclude'):
                config_copy['exclude'] = None
            if not config_copy.get('sources'):
                config_copy['sources'] = None

            # Ensure include_root_readme is saved with default if not set
            if 'include_root_readme' not in config_copy:
                config_copy['include_root_readme'] = False

            # Ensure use_gitignore is saved with default if not set
            if 'use_gitignore' not in config_copy:
                config_copy['use_gitignore'] = False

            # Replace empty dict with None for doc_mappings
            if not config_copy.get('doc_mappings'):
                config_copy['doc_mappings'] = None

            yaml.dump(config_copy, f, default_flow_style=False, sort_keys=False)

            # Add helpful examples and documentation
            f.write("\n")
            f.write("# " + "=" * 76 + "\n")
            f.write("# Configuration Guide & Examples\n")
            f.write("# " + "=" * 76 + "\n")
            f.write("\n")
            f.write("# Exclude Patterns\n")
            f.write("# ----------------\n")
            f.write("# Use glob patterns to exclude files from documentation tracking.\n")
            f.write("# Examples:\n")
            f.write("#   exclude:\n")
            f.write("#     - \"**/node_modules/**\"     # Exclude all node_modules directories\n")
            f.write("#     - \"**/*.pyc\"               # Exclude Python bytecode files\n")
            f.write("#     - \"**/dist/**\"             # Exclude build artifacts\n")
            f.write("#     - \"**/.git/**\"             # Exclude git directory\n")
            f.write("#     - \"**/venv/**\"             # Exclude Python virtual environments\n")
            f.write("#     - \"**/__pycache__/**\"      # Exclude Python cache\n")
            f.write("\n")
            f.write("# Source Files (Glob Patterns)\n")
            f.write("# -----------------------------\n")
            f.write("# Glob patterns to specify which source files to track.\n")
            f.write("# IMPORTANT: Use glob patterns (e.g., 'src/**/*.py'), not just directory names.\n")
            f.write("# Examples:\n")
            f.write("#   sources:\n")
            f.write("#     - \"src/**/*.py\"            # All Python files in src/\n")
            f.write("#     - \"lib/**/*.js\"            # All JavaScript files in lib/\n")
            f.write("#     - \"packages/core/**/*.ts\"  # TypeScript files in packages/core/\n")
            f.write("#     - \"**/*.go\"                # All Go files in project\n")
            f.write("\n")
            f.write("# Documentation Path\n")
            f.write("# -------------------\n")
            f.write("# Path to documentation directory (relative to project root).\n")
            f.write("# Common values: docs, doc, documentation, website/docs\n")
            f.write("\n")
            f.write("# Platform\n")
            f.write("# --------\n")
            f.write("# Documentation platform: mkdocs, sphinx, hugo, docusaurus, etc.\n")
            f.write("# Set to 'unknown' if not using a specific platform.\n")
            f.write("\n")
            f.write("# Include Root README\n")
            f.write("# -------------------\n")
            f.write("# Set to true to include the root README.md in documentation operations.\n")
            f.write("# When enabled, validation, quality assessment, and change detection\n")
            f.write("# will include the root README.md alongside docs in the docs/ directory.\n")
            f.write("# Default: false (backwards compatible)\n")
            f.write("\n")
            f.write("# Use Gitignore\n")
            f.write("# -------------\n")
            f.write("# Set to true to automatically exclude files based on .gitignore patterns.\n")
            f.write("# When enabled, files ignored by git will also be excluded from doc tracking.\n")
            f.write("# Priority: user excludes > .gitignore > built-in defaults\n")
            f.write("# Default: false (opt-in feature)\n")
            f.write("# Example:\n")
            f.write("#   use_gitignore: true\n")
            f.write("#   exclude:              # Additional patterns beyond .gitignore\n")
            f.write("#     - \"specs/**\"\n")
            f.write("\n")
            f.write("# Documentation Path Mappings\n")
            f.write("# ---------------------------\n")
            f.write("# Map change categories to documentation file paths.\n")
            f.write("# Supports non-standard layouts (documentation/, wiki/, _docs/, etc.).\n")
            f.write("# When not configured, falls back to default paths in docs/.\n")
            f.write("# Example:\n")
            f.write("#   doc_mappings:\n")
            f.write("#     cli: 'docs/reference/command-reference.md'\n")
            f.write("#     api: 'docs/reference/api.md'\n")
            f.write("#     config: 'docs/reference/configuration.md'\n")
            f.write("#     dependency: 'docs/getting-started/installation.md'\n")
            f.write("#     infrastructure: 'docs/development/ci-cd.md'\n")
            f.write("# Non-standard layout example:\n")
            f.write("#   doc_mappings:\n")
            f.write("#     cli: 'documentation/commands.md'  # Uses documentation/ instead of docs/\n")
            f.write("#     api: 'wiki/API-Reference.md'      # Uses wiki/ directory\n")
            f.write("\n")
            f.write("# API Coverage Configuration\n")
            f.write("# --------------------------\n")
            f.write("# Configure how public symbols are detected for API coverage metrics.\n")
            f.write("# Follows industry standards from Sphinx autodoc and mkdocstrings.\n")
            f.write("# Example:\n")
            f.write("#   api_coverage:\n")
            f.write("#     strategy: 'all_then_underscore'  # Options: all_then_underscore, all_only, underscore_only\n")
            f.write("#     preset: 'pydantic'               # See preset list below\n")
            f.write("#     exclude_symbols:                 # Additional patterns (fnmatch syntax)\n")
            f.write("#       - 'my_internal_*'\n")
            f.write("#     include_symbols:                 # Force-include these (overrides exclusions)\n")
            f.write("#       - 'MySpecialClass'\n")
            f.write("#\n")
            f.write("# Strategy options:\n")
            f.write("#   - all_then_underscore: Use __all__ if defined, else underscore convention (default)\n")
            f.write("#   - all_only: Only symbols in __all__ are public (strict)\n")
            f.write("#   - underscore_only: Only use underscore convention, ignore __all__\n")
            f.write("#\n")
            f.write("# Available presets by language:\n")
            f.write("#   Python:\n")
            f.write("#     - pydantic: Config, model_config, validators, validate_*\n")
            f.write("#     - django: Meta, DoesNotExist, MultipleObjectsReturned\n")
            f.write("#     - fastapi: Config, model_config\n")
            f.write("#     - pytest: test_*, Test*, fixture, conftest\n")
            f.write("#     - sqlalchemy: metadata, __table__, __mapper__, _sa_*\n")
            f.write("#   JavaScript/TypeScript:\n")
            f.write("#     - jest: describe, it, test, beforeEach, afterEach, expect\n")
            f.write("#     - vitest: same as jest + vi, suite\n")
            f.write("#     - react: _render*, UNSAFE_*, __*, $$typeof\n")
            f.write("#     - vue: $_*, __v*, internal render helpers\n")
            f.write("#   Go:\n")
            f.write("#     - go-test: Test*, Benchmark*, Example*, Fuzz*\n")
            f.write("#   Rust:\n")
            f.write("#     - rust-test: tests, test_*, bench_*\n")
            f.write("#     - serde: Serialize, Deserialize, __serde_*\n")

        return True
    except Exception:
        return False
