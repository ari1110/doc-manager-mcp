"""Configuration file management utilities.

This module provides utilities for loading and saving .doc-manager.yml
configuration files with helpful examples and documentation.
"""

from pathlib import Path
from typing import Any

import yaml


def load_config(project_path: Path) -> dict[str, Any] | None:
    """Load .doc-manager.yml configuration."""
    config_path = project_path / ".doc-manager.yml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding='utf-8') as f:
            return yaml.safe_load(f)
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

        return True
    except Exception:
        return False
