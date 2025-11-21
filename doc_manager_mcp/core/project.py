"""Project detection and analysis utilities.

This module provides utilities for detecting project languages, documentation
directories, markdown files, and documentation platforms.
"""

from pathlib import Path
from typing import Any

from ..constants import MAX_FILES, DocumentationPlatform


def detect_project_language(project_path: Path) -> str:
    """Detect primary programming language of project.

    Returns the detected language based on project files.
    """
    language_indicators = {
        # Go
        "go.mod": "Go",
        # JavaScript/TypeScript
        "package.json": "JavaScript/TypeScript",
        # Rust
        "Cargo.toml": "Rust",
        # Python (check pyproject.toml first as it's the modern standard)
        "pyproject.toml": "Python",
        "Pipfile": "Python",
        "requirements.txt": "Python",
        "setup.py": "Python",
        # Java/Kotlin
        "pom.xml": "Java",
        "build.gradle": "Java",
        "build.gradle.kts": "Kotlin",
        # Ruby
        "Gemfile": "Ruby",
        # PHP
        "composer.json": "PHP",
        # C/C++
        "CMakeLists.txt": "C/C++",
        # Scala
        "build.sbt": "Scala",
        # Elixir
        "mix.exs": "Elixir",
        # Swift
        "Package.swift": "Swift",
    }

    for file, language in language_indicators.items():
        if (project_path / file).exists():
            return language

    return "Unknown"


def find_docs_directory(project_path: Path) -> Path | None:
    """Find documentation directory in project."""
    common_doc_dirs = ["docs", "doc", "documentation", "docsite", "website/docs"]

    for dir_name in common_doc_dirs:
        doc_path = project_path / dir_name
        if doc_path.exists() and doc_path.is_dir():
            return doc_path

    return None


def get_doc_relative_path(file_path: Path, docs_path: Path, project_path: Path) -> str:
    """Get documentation-relative path for a file.

    Handles both documentation files inside docs/ and root README.md.

    Args:
        file_path: Absolute path to the file
        docs_path: Absolute path to docs directory
        project_path: Absolute path to project root

    Returns:
        - For files in docs/: path relative to docs/ (e.g., "guides/setup.md")
        - For root README.md: "README.md" (special identifier)

    Examples:
        >>> get_doc_relative_path(Path("/proj/docs/guide.md"), Path("/proj/docs"), Path("/proj"))
        "guide.md"
        >>> get_doc_relative_path(Path("/proj/README.md"), Path("/proj/docs"), Path("/proj"))
        "README.md"
    """
    file_path = file_path.resolve()
    docs_path = docs_path.resolve()
    project_path = project_path.resolve()

    # Check if file is root README.md
    if file_path == project_path / "README.md":
        return "README.md"

    # Otherwise compute relative path from docs/
    try:
        return str(file_path.relative_to(docs_path))
    except ValueError:
        # File is outside docs/ directory, return relative to project root
        return str(file_path.relative_to(project_path))


def find_markdown_files(
    docs_path: Path,
    project_path: Path | None = None,
    validate_boundaries: bool = True,
    max_files: int | None = None,
    include_root_readme: bool = False
) -> list[Path]:
    """Find all markdown files in documentation directory.

    Args:
        docs_path: Documentation directory path
        project_path: Project root path (for boundary validation). Required if validate_boundaries=True.
        validate_boundaries: Whether to validate paths don't escape project boundary (default: True)
        max_files: Maximum number of files to process. Defaults to MAX_FILES constant if None.
        include_root_readme: Whether to include root README.md in the file list (default: False)

    Returns:
        List of validated markdown file paths, sorted alphabetically.
        If include_root_readme=True and root README.md exists, it's included in the list.

    Raises:
        ValueError: If file count exceeds max_files limit
        ValueError: If validate_boundaries=True but project_path is None
    """
    from .paths import validate_path_boundary

    if validate_boundaries and project_path is None:
        raise ValueError("project_path is required when validate_boundaries=True")

    markdown_files = []
    file_count = 0
    limit = max_files if max_files is not None else MAX_FILES

    for pattern in ["**/*.md", "**/*.markdown"]:
        for file_path in docs_path.glob(pattern):
            if file_count >= limit:
                raise ValueError(
                    f"File count limit exceeded (maximum: {limit:,} files)\n"
                    f"→ Consider processing a smaller directory or increasing the limit."
                )

            # Optionally validate path boundary and check for malicious symlinks
            if validate_boundaries:
                try:
                    _ = validate_path_boundary(file_path, project_path)  # type: ignore
                    markdown_files.append(file_path)
                    file_count += 1
                except ValueError:
                    # Skip files that escape project boundary or malicious symlinks
                    continue
            else:
                markdown_files.append(file_path)
                file_count += 1

    # Optionally include root README.md
    if include_root_readme and project_path is not None:
        root_readme = project_path / "README.md"
        if root_readme.exists() and root_readme.is_file():
            if file_count >= limit:
                raise ValueError(
                    f"File count limit exceeded (maximum: {limit:,} files)\n"
                    f"→ Consider processing a smaller directory or increasing the limit."
                )
            # Validate root README if boundaries are being checked
            if validate_boundaries:
                try:
                    from .paths import validate_path_boundary
                    _ = validate_path_boundary(root_readme, project_path)
                    markdown_files.append(root_readme)
                except ValueError:
                    # Skip if validation fails
                    pass
            else:
                markdown_files.append(root_readme)

    return sorted(markdown_files)


def is_public_symbol(symbol: Any) -> bool:
    """Determine if a symbol is public based on language-specific conventions.

    Args:
        symbol: Symbol object with 'name' and 'file' attributes

    Returns:
        True if symbol is public, False otherwise

    Language-specific rules:
        - Go: exported names start with uppercase
        - Python: public if no leading underscore
        - JavaScript/TypeScript: public if no leading underscore
    """
    if not symbol.name:
        return False

    # Language-specific public conventions
    if symbol.file.endswith('.go'):
        # Go: exported names start with uppercase
        return symbol.name[0].isupper()
    elif symbol.file.endswith('.py'):
        # Python: public if no leading underscore
        return not symbol.name.startswith('_')
    elif symbol.file.endswith(('.js', '.ts', '.jsx', '.tsx')):
        # JavaScript/TypeScript: public if no leading underscore
        return not symbol.name.startswith('_')

    # Default: consider public for unknown languages
    return True


def detect_platform_quick(project_path: Path) -> DocumentationPlatform:
    """Quick platform detection by checking for common config files.

    This is a fast, simple check for initialization purposes. For comprehensive
    detection with confidence scores, use the docmgr_detect_platform MCP tool.

    Args:
        project_path: Project root directory

    Returns:
        DocumentationPlatform enum value
    """
    if (project_path / "docsite" / "hugo.yaml").exists() or (project_path / "hugo.toml").exists():
        return DocumentationPlatform.HUGO
    elif (project_path / "docusaurus.config.js").exists():
        return DocumentationPlatform.DOCUSAURUS
    elif (project_path / "mkdocs.yml").exists():
        return DocumentationPlatform.MKDOCS
    elif (project_path / "conf.py").exists():
        return DocumentationPlatform.SPHINX
    else:
        return DocumentationPlatform.UNKNOWN
