"""Dependency tracking tools for doc-manager."""

import asyncio
import json
import re
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

from ..constants import MAX_FILES, OPERATION_TIMEOUT, ResponseFormat
from ..models import TrackDependenciesInput
from ..utils import (
    enforce_response_limit,
    file_lock,
    find_docs_directory,
    handle_error,
    safe_json_dumps,
    validate_path_boundary,
)

# ============================================================================
# T082: Compiled regex patterns for performance (FR-023)
# ============================================================================

# Extract file path references (common patterns)
FILE_PATH_PATTERN = re.compile(r'`([a-zA-Z0-9_\-/.]+\.(go|py|js|ts|tsx|jsx|java|rs|rb|php|c|cpp|h|hpp|cs|swift|kt|yaml|yml|json|cfg))`')

# Extract function/method references
FUNCTION_PATTERN = re.compile(r'`([A-Z][a-zA-Z0-9]*\.)?([a-z_][a-zA-Z0-9_]*)\(\)`')

# Match markdown headings with function signatures
HEADING_FUNCTION_PATTERN = re.compile(r'^#+\s+([a-z_][a-zA-Z0-9_]*)\s*\([^)]*\)', re.MULTILINE)

# Extract class/type references
CLASS_PATTERN = re.compile(r'`([A-Z][a-zA-Z0-9]+)(?!\()`')

# Extract command references
COMMAND_PATTERNS = [
    re.compile(r'`([a-z][a-z0-9\-]+(?:\s+[a-z][a-z0-9\-]+)*(?:\s+--?[a-z][a-z0-9\-]*)*)`'),
    re.compile(r'\$\s+([a-z][a-z0-9\-]+(?:\s+[a-z][a-z0-9\-]+)*(?:\s+--?[a-z][a-z0-9\-]*)*)')
]


def _find_markdown_files(docs_path: Path, project_path: Path) -> list[Path]:
    """Find all markdown files in documentation directory.

    Args:
        docs_path: Documentation directory path
        project_path: Project root path (for boundary validation)

    Returns:
        List of validated markdown file paths
    """
    markdown_files = []
    file_count = 0
    for pattern in ["**/*.md", "**/*.markdown"]:
        for file_path in docs_path.glob(pattern):
            if file_count >= MAX_FILES:
                raise ValueError(
                    f"File count limit exceeded (maximum: {MAX_FILES:,} files)\n"
                    f"→ Consider processing a smaller directory or increasing the limit."
                )
            # Validate path boundary and check for malicious symlinks (T030 - FR-028)
            try:
                _ = validate_path_boundary(file_path, project_path)
                markdown_files.append(file_path)
                file_count += 1
            except ValueError:
                # Skip files that escape project boundary or malicious symlinks
                continue
    return sorted(markdown_files)


def _extract_code_references(content: str, doc_file: Path) -> list[dict[str, Any]]:
    """Extract code references from documentation content (T082 - FR-023)."""
    references = []

    # Extract file path references using compiled pattern
    for match in FILE_PATH_PATTERN.finditer(content):
        file_path = match.group(1)
        references.append({
            "type": "file_path",
            "reference": file_path,
            "doc_file": str(doc_file)
        })

    # Extract function/method references using compiled pattern
    for match in FUNCTION_PATTERN.finditer(content):
        func_name = match.group(0).strip('`')
        references.append({
            "type": "function",
            "reference": func_name,
            "doc_file": str(doc_file)
        })

    # Match markdown headings with function signatures using compiled pattern
    for match in HEADING_FUNCTION_PATTERN.finditer(content):
        func_name = match.group(1) + "()"
        references.append({
            "type": "function",
            "reference": func_name,
            "doc_file": str(doc_file)
        })

    # Extract class/type references using compiled pattern
    for match in CLASS_PATTERN.finditer(content):
        class_name = match.group(1)
        # Exclude common words and single letters
        if len(class_name) > 2 and class_name not in ['API', 'CLI', 'HTTP', 'HTTPS', 'URL', 'JSON', 'XML']:
            references.append({
                "type": "class",
                "reference": class_name,
                "doc_file": str(doc_file)
            })

    # Extract command references using compiled patterns
    for pattern in COMMAND_PATTERNS:
        for match in pattern.finditer(content):
            command = match.group(1)
            # Filter out common words and single-word commands that are likely prose
            first_word = command.split()[0]
            if first_word not in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'your', 'you', 'a', 'an', 'in', 'on', 'at', 'to', 'of']:
                references.append({
                    "type": "command",
                    "reference": command,
                    "doc_file": str(doc_file)
                })

    # Extract configuration keys
    # Pattern: config keys like `platform`, `docs_path`, or `server.port` (single words or dotted paths in backticks)
    # Also match keys followed by a colon like `platform: value` or `docs_path: "value"`
    # Match lowercase/underscore keys that look like config (avoid matching prose)
    config_patterns = [
        r'`([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+)`',  # Dotted paths: `server.port`
        r'`([a-z_][a-z0-9_]{2,}):[^`]+`',  # Config keys with colon inside backticks: `platform: hugo`, `docs_path: "docs"`
        r'`([a-z_][a-z0-9_]{2,})`'  # Single words at least 3 chars: `platform`, `exclude`, `docs_path`
    ]

    for pattern in config_patterns:
        for match in re.finditer(pattern, content):
            config_key = match.group(1)
            # Exclude common words that aren't config keys
            if config_key not in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'your', 'you', 'file', 'path', 'name', 'type']:
                references.append({
                    "type": "config_key",
                    "reference": config_key,
                    "doc_file": str(doc_file)
                })

    return references


def _find_source_files(project_path: Path, docs_path: Path) -> list[Path]:
    """Find all source code and configuration files in the project."""
    source_files = []
    file_count = 0

    # Common source file extensions (code + config files)
    extensions = [
        # Source code
        '.go', '.py', '.js', '.ts', '.jsx', '.tsx',
        '.java', '.rs', '.rb', '.php', '.c', '.cpp',
        '.h', '.hpp', '.cs', '.swift', '.kt',
        # Configuration files
        '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini'
    ]

    for ext in extensions:
        pattern = f"**/*{ext}"
        for file_path in project_path.glob(pattern):
            if file_count >= MAX_FILES:
                raise ValueError(
                    f"File count limit exceeded (maximum: {MAX_FILES:,} files)\n"
                    f"→ Consider processing a smaller directory or increasing the limit."
                )
            # Validate path boundary and check for malicious symlinks (T030 - FR-028)
            try:
                _ = validate_path_boundary(file_path, project_path)
            except ValueError:
                # Skip files that escape project boundary or malicious symlinks
                continue

            # Exclude docs, tests, vendor, node_modules, etc.
            path_str = str(file_path)
            if any(x in path_str for x in ['node_modules', 'vendor', 'venv', '.git', 'dist', 'build']):
                continue
            if file_path.is_relative_to(docs_path):
                continue
            source_files.append(file_path)
            file_count += 1

    return source_files


def _match_references_to_sources(references: list[dict[str, Any]], source_files: list[Path],
                                 project_path: Path) -> dict[str, list[str]]:
    """Match documentation references to actual source files."""
    dependencies = {}  # doc_file -> [source_files]

    for ref in references:
        doc_file = ref["doc_file"]
        reference = ref["reference"]
        ref_type = ref["type"]

        if doc_file not in dependencies:
            dependencies[doc_file] = set()

        # Match file path references
        if ref_type == "file_path":
            for source_file in source_files:
                relative_path = str(source_file.relative_to(project_path)).replace('\\', '/')
                # Normalize reference path separators too
                ref_normalized = reference.replace('\\', '/')
                # T091: Use precise path matching with path separators to avoid false positives (FR-026)
                # Match exact path or path ending with separator (e.g., "save.py" won't match "autosave.py")
                if relative_path == ref_normalized or relative_path.endswith('/' + ref_normalized):
                    dependencies[doc_file].add(relative_path)

        # Match function/class references by searching in source files
        elif ref_type in ["function", "class"]:
            # Extract the identifier (without parentheses or namespace)
            identifier = reference.replace('()', '').split('.')[-1]

            for source_file in source_files:
                try:
                    with open(source_file, encoding='utf-8') as f:
                        content = f.read()

                    # Look for function/class definitions
                    patterns = [
                        rf'\bfunc\s+{identifier}\b',  # Go
                        rf'\bdef\s+{identifier}\b',   # Python
                        rf'\bfunction\s+{identifier}\b',  # JavaScript
                        rf'\bclass\s+{identifier}\b',  # Most languages
                        rf'\b{identifier}\s*\(',      # Function call/definition
                    ]

                    for pattern in patterns:
                        if re.search(pattern, content):
                            relative_path = str(source_file.relative_to(project_path)).replace('\\', '/')
                            dependencies[doc_file].add(relative_path)
                            break

                except Exception as e:
                    print(f"Warning: Failed to read source file {source_file}: {e}", file=sys.stderr)
                    continue

        # Match command references to CLI source files
        elif ref_type == "command":
            command_name = reference.split()[0]
            for source_file in source_files:
                relative_path = str(source_file.relative_to(project_path)).replace('\\', '/')
                # T091: Use precise path matching with path separators to avoid false positives (FR-026)
                # Look for command files (e.g., cmd/add.go for "add" command)
                # Match with path separators to prevent "add" matching "add_user" or "badder"
                if re.search(rf'\b(cmd|cli)/{re.escape(command_name)}(/|\.)', relative_path):
                    dependencies[doc_file].add(relative_path)

    # Convert sets to sorted lists
    return {k: sorted(v) for k, v in dependencies.items()}


def _build_reverse_index(dependencies: dict[str, list[str]], all_references: list[dict[str, Any]] | None = None) -> dict[str, list[str]]:
    """Build reverse index: source_file/reference -> [doc_files].

    Includes both matched source files and unmatched references (functions, classes, etc.)
    """
    reverse_index = {}

    # Add matched source files
    for doc_file, source_files in dependencies.items():
        for source_file in source_files:
            if source_file not in reverse_index:
                reverse_index[source_file] = []
            reverse_index[source_file].append(doc_file)

    # Add unmatched references (functions, classes, commands, config keys)
    # These won't have matched source files but should still be trackable
    if all_references:
        # Find which references were NOT matched to source files
        matched_refs = set()
        for _doc_file, source_files in dependencies.items():
            for source_file in source_files:
                matched_refs.add(source_file)

        # Add unmatched references with a type prefix
        for ref in all_references:
            ref_type = ref["type"]
            reference = ref["reference"]
            doc_file = ref["doc_file"]

            # For non-file references (functions, classes, etc.), add them to the index
            if ref_type in ["function", "class", "command", "config_key"]:
                if reference not in reverse_index:
                    reverse_index[reference] = []
                if doc_file not in reverse_index[reference]:
                    reverse_index[reference].append(doc_file)

    return reverse_index


def _build_reference_index(all_references: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build index of references to docs that mention them: reference -> [doc_files]."""
    ref_index = {}

    for ref in all_references:
        reference = ref["reference"]
        doc_file = ref["doc_file"]

        if reference not in ref_index:
            ref_index[reference] = []
        if doc_file not in ref_index[reference]:
            ref_index[reference].append(doc_file)

    return ref_index


def _save_dependencies_to_memory(project_path: Path, dependencies: dict[str, list[str]],
                                 reverse_index: dict[str, list[str]], all_references: list[dict[str, Any]] | None = None,
                                 reference_index: dict[str, list[str]] | None = None):
    """Save dependency graph to memory directory."""
    memory_dir = project_path / ".doc-manager"

    # Create memory directory if it doesn't exist
    try:
        memory_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Failed to create memory directory {memory_dir}: {e}", file=sys.stderr)
        return

    dependency_file = memory_dir / "dependencies.json"

    data = {
        "generated_at": datetime.now().isoformat(),
        "doc_to_code": dependencies,
        "code_to_doc": reverse_index
    }

    # Add reference index (reference -> docs that mention it)
    if reference_index:
        data["reference_to_doc"] = reference_index

    # Add all references grouped by type if provided
    if all_references:
        refs_by_type = {}
        for ref in all_references:
            ref_type = ref["type"]
            if ref_type not in refs_by_type:
                refs_by_type[ref_type] = []
            refs_by_type[ref_type].append({
                "reference": ref["reference"],
                "doc_file": ref["doc_file"]
            })
        data["all_references"] = refs_by_type

    try:
        # T066: Use file locking to prevent concurrent modification (FR-018)
        with file_lock(dependency_file):
            with open(dependency_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save dependencies to {dependency_file}: {e}", file=sys.stderr)


def _format_dependency_report(dependencies: dict[str, list[str]], reverse_index: dict[str, list[str]],
                              total_references: int, all_references: list[dict[str, Any]],
                              response_format: ResponseFormat) -> str:
    """Format dependency tracking report."""
    if response_format == ResponseFormat.JSON:
        return enforce_response_limit({
            "generated_at": datetime.now().isoformat(),
            "total_references": total_references,
            "total_doc_files": len(dependencies),
            "total_source_files": len(reverse_index),
            "doc_to_code": dependencies,
            "code_to_doc": reverse_index
        }})
    else:
        lines = ["# Code-to-Documentation Dependency Graph", ""]
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if total_references == 0:
            lines.append("**Total References:** 0 (no references found)")
        else:
            lines.append(f"**Total References:** {total_references}")
        lines.append(f"**Documentation Files:** {len(dependencies)}")
        lines.append(f"**Source Files Referenced:** {len(reverse_index)}")
        lines.append("")

        # Documentation → Code Dependencies
        lines.append("## Documentation → Code Dependencies")
        lines.append("")
        lines.append("Shows which source files each documentation file depends on.")
        lines.append("")

        if not dependencies:
            lines.append("No dependencies detected.")
        else:
            for doc_file in sorted(dependencies.keys()):
                source_files = dependencies[doc_file]
                if source_files:
                    lines.append(f"### {doc_file}")
                    lines.append(f"**Depends on {len(source_files)} source file(s):**")
                    for source_file in source_files:
                        lines.append(f"- `{source_file}`")
                    lines.append("")

        # Code → Documentation Reverse Index
        lines.append("## Code → Documentation Reverse Index")
        lines.append("")
        lines.append("Shows which documentation files reference each source file.")
        lines.append("")

        if not reverse_index:
            lines.append("No reverse dependencies detected.")
        else:
            # Show most-referenced files first
            sorted_sources = sorted(reverse_index.items(), key=lambda x: len(x[1]), reverse=True)

            for source_file, doc_files in sorted_sources[:20]:  # Top 20
                lines.append(f"### {source_file}")
                lines.append(f"**Referenced by {len(doc_files)} doc file(s):**")
                for doc_file in doc_files:
                    lines.append(f"- `{doc_file}`")
                lines.append("")

            if len(sorted_sources) > 20:
                lines.append(f"*... and {len(sorted_sources) - 20} more source files*")
                lines.append("")

        # Show all extracted references grouped by type
        if total_references > 0:
            lines.append("## Extracted References by Type")
            lines.append("")
            lines.append("All code references found in documentation:")
            lines.append("")

            # Group references by type
            refs_by_type = {}
            for ref in all_references:
                ref_type = ref["type"]
                if ref_type not in refs_by_type:
                    refs_by_type[ref_type] = set()
                refs_by_type[ref_type].add(ref["reference"])

            for ref_type in sorted(refs_by_type.keys()):
                refs = sorted(refs_by_type[ref_type])
                lines.append(f"**{ref_type.replace('_', ' ').title()}s ({len(refs)}):**")
                for ref in refs[:20]:  # Limit to 20 per type
                    lines.append(f"- `{ref}`")
                if len(refs) > 20:
                    lines.append(f"  *... and {len(refs) - 20} more*")
                lines.append("")

        lines.append("## Impact Analysis")
        lines.append("")
        lines.append("Use this dependency graph to:")
        lines.append("- Identify which docs need updates when code changes")
        lines.append("- Find orphaned documentation (no code references)")
        lines.append("- Detect missing documentation for important source files")
        lines.append("")

        # Find docs with no dependencies
        orphaned_docs = [doc for doc, sources in dependencies.items() if not sources]
        if orphaned_docs:
            lines.append(f"**Orphaned Documentation ({len(orphaned_docs)} files):**")
            lines.append("These docs have no detected code references:")
            for doc in orphaned_docs[:10]:
                lines.append(f"- {doc}")
            if len(orphaned_docs) > 10:
                lines.append(f"  ... and {len(orphaned_docs) - 10} more")

        return enforce_response_limit("\n".join(lines))


def with_timeout(timeout_seconds):
    """Decorator to add timeout enforcement to async functions.

    Args:
        timeout_seconds (int): Maximum execution time in seconds

    Raises:
        TimeoutError: If operation exceeds timeout limit
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Use asyncio.wait_for for async timeout enforcement
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError as err:
                raise TimeoutError(
                    f"Operation exceeded timeout ({timeout_seconds}s)\n"
                    f"→ Consider processing fewer files or increasing timeout limit."
                ) from err
        return wrapper
    return decorator


@with_timeout(OPERATION_TIMEOUT)
async def track_dependencies(params: TrackDependenciesInput) -> str | dict[str, any]:
    """Track code-to-docs dependencies by analyzing references in documentation.

    Builds a bidirectional dependency graph:
    - Doc → Code: Which source files each doc depends on
    - Code → Doc: Which docs reference each source file

    Extracts references for:
    - File paths (e.g., `src/main.go`)
    - Functions/methods (e.g., `initialize()`, `User.save()`)
    - Classes/types (e.g., `Customer`, `HttpClient`)
    - Commands (e.g., `pass add`, `git commit`)
    - Configuration keys (e.g., `server.port`)

    Args:
        params (TrackDependenciesInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - response_format (ResponseFormat): Output format (markdown or json)

    Returns:
        str: Dependency graph report

    Examples:
        - Use when: Analyzing documentation coverage
        - Use when: Planning code refactoring (see impact on docs)
        - Use when: Finding orphaned documentation

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if docs_path not found
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Find docs directory (use provided path or auto-detect)
        if params.docs_path:
            docs_path = project_path / params.docs_path
            if not docs_path.exists():
                return enforce_response_limit(f"Error: Documentation directory not found at {docs_path}")
        else:
            docs_path = find_docs_directory(project_path)
            if not docs_path:
                return enforce_response_limit("Error: Could not find documentation directory. Specify docs_path parameter.")

        # Find all markdown files
        markdown_files = _find_markdown_files(docs_path, project_path)
        all_references = []

        if markdown_files:
            # Extract references from all docs
            for md_file in markdown_files:
                try:
                    with open(md_file, encoding='utf-8') as f:
                        content = f.read()

                    references = _extract_code_references(content, md_file.relative_to(docs_path))
                    all_references.extend(references)
                except Exception as e:
                    print(f"Warning: Failed to read markdown file {md_file}: {e}", file=sys.stderr)
                    continue

        # Find source files
        source_files = _find_source_files(project_path, docs_path)

        # Match references to actual source files
        dependencies = _match_references_to_sources(all_references, source_files, project_path)

        # Build reverse index (source file/reference -> docs)
        # Includes both matched files and unmatched references
        reverse_index = _build_reverse_index(dependencies, all_references)

        # Build reference index (reference text -> docs that mention it)
        reference_index = _build_reference_index(all_references)

        # Save to memory
        _save_dependencies_to_memory(project_path, dependencies, reverse_index, all_references, reference_index)

        return enforce_response_limit(_format_dependency_report(dependencies, reverse_index, len(all_references), all_references, params.response_format))

    except Exception as e:
        return enforce_response_limit(handle_error(e, "track_dependencies"))
