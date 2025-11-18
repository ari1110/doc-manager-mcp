"""Dependency tracking tools for doc-manager."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ..constants import MAX_FILES
from ..indexing import SymbolIndexer
from ..models import TrackDependenciesInput
from ..utils import (
    file_lock,
    find_docs_directory,
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

# Extract command references (literal and code)
COMMAND_PATTERNS = [
    re.compile(r'`([a-z][a-z0-9\-]+(?:\s+[a-z][a-z0-9\-]+)*(?:\s+--?[a-z][a-z0-9\-]*)*)`'),
    re.compile(r'\$\s+([a-z][a-z0-9\-]+(?:\s+[a-z][a-z0-9\-]+)*(?:\s+--?[a-z][a-z0-9\-]*)*)')
]

# Extract semantic command references (phrases like "add command", "the generate subcommand")
SEMANTIC_COMMAND_PATTERNS = [
    # Matches: "add command", "generate command", "list command"
    re.compile(r'\b([a-z][a-z0-9\-]+)\s+(?:command|subcommand|cmd)\b', re.IGNORECASE),
    # Matches: "the add command", "the generate subcommand"
    re.compile(r'\bthe\s+([a-z][a-z0-9\-]+)\s+(?:command|subcommand|cmd)\b', re.IGNORECASE),
    # Matches: "`add` command", "`generate` subcommand"
    re.compile(r'`([a-z][a-z0-9\-]+)`\s+(?:command|subcommand|cmd)\b', re.IGNORECASE),
    # Matches markdown headers: "## add Command", "### The generate Command"
    re.compile(r'^#+\s+(?:the\s+)?([a-z][a-z0-9\-]+)\s+(?:command|subcommand|cmd)', re.IGNORECASE | re.MULTILINE),
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

    # Extract semantic command references (phrases like "add command", "generate subcommand")
    # Stopwords: generic commands that are too common to be useful
    command_stopwords = {'run', 'help', 'version', 'test', 'build', 'install', 'start', 'stop', 'restart'}
    seen_commands = set()  # Track to avoid duplicates

    for pattern in SEMANTIC_COMMAND_PATTERNS:
        for match in pattern.finditer(content):
            command_name = match.group(1).lower()

            # Skip stopwords and duplicates
            if command_name not in command_stopwords and command_name not in seen_commands:
                seen_commands.add(command_name)
                references.append({
                    "type": "semantic_command",
                    "reference": command_name,
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


def _match_references_to_sources(
    references: list[dict[str, Any]],
    source_files: list[Path],
    project_path: Path,
    symbol_index: Any | None = None
) -> dict[str, list[str]]:
    """Match documentation references to actual source files.

    Args:
        references: List of extracted references from documentation
        source_files: List of source file paths
        project_path: Project root path
        symbol_index: Optional SymbolIndexer for validating function/class matches

    Returns:
        Dictionary mapping doc files to matched source files
    """
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

            # Try TreeSitter symbol index first (much more accurate)
            if symbol_index:
                symbols = symbol_index.lookup(identifier)
                if symbols:
                    for symbol in symbols:
                        # Normalize file path
                        dependencies[doc_file].add(symbol.file)
                    continue  # Skip regex fallback if symbol index found matches

            # Fallback to regex-based text search if symbol index unavailable or no matches
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

        # Match semantic command references (e.g., "add command" → cmd/add.go)
        elif ref_type == "semantic_command":
            command_name = reference  # Already normalized to lowercase in extraction
            for source_file in source_files:
                relative_path = str(source_file.relative_to(project_path)).replace('\\', '/')
                # T091: Use precise path matching with path separators
                # Convention-based matching:
                # - cmd/{command}.go (Go CLI pattern)
                # - cmd/{command}.py (Python CLI pattern)
                # - cli/{command}.js (Node.js pattern)
                # Use word boundaries to prevent "add" matching "add_user.go"
                if re.search(rf'\b(cmd|cli|commands?)/{re.escape(command_name)}(/|\.)', relative_path):
                    # If symbol index available, verify the file has symbols (not empty)
                    if symbol_index:
                        file_symbols = symbol_index.get_symbols_in_file(relative_path)
                        if file_symbols:  # Only add if file has actual code
                            dependencies[doc_file].add(relative_path)
                    else:
                        # No symbol index, trust the file path match
                        dependencies[doc_file].add(relative_path)

    # Convert sets to sorted lists
    return {k: sorted(v) for k, v in dependencies.items()}


def _build_reverse_index(dependencies: dict[str, list[str]], all_references: list[dict[str, Any]] | None = None) -> dict[str, list[str]]:
    """Build reverse index: source_file/reference -> [doc_files].

    For matched references (semantic commands, functions, etc.), they are consolidated
    under their source file path. Only unmatched references appear as separate entries.
    """
    reverse_index = {}

    # Add matched source files
    for doc_file, source_files in dependencies.items():
        for source_file in source_files:
            if source_file not in reverse_index:
                reverse_index[source_file] = []
            reverse_index[source_file].append(doc_file)

    # Add only unmatched references as separate entries
    # Matched semantic commands should only appear under their source file
    if all_references:
        # Build set of (doc, reference) pairs that resulted in matches
        matched_ref_pairs = set()

        # Check each reference to see if it matched any source files
        for ref in all_references:
            ref_type = ref["type"]
            reference = ref["reference"]
            doc_file = ref["doc_file"]

            # Skip file_path references - they're always explicit matches
            if ref_type == "file_path":
                matched_ref_pairs.add((doc_file, reference))
                continue

            # For semantic commands and commands, check if any dependency matches this reference
            if ref_type in ["semantic_command", "command"]:
                command_name = reference.split()[0] if ref_type == "command" else reference
                if doc_file in dependencies:
                    for source_file in dependencies[doc_file]:
                        # Check if this source file path matches the command pattern
                        if re.search(rf'\b(cmd|cli|commands?)/{re.escape(command_name)}(/|\.)', source_file):
                            matched_ref_pairs.add((doc_file, reference))
                            break

            # For functions and classes, check if any dependency contains this identifier
            elif ref_type in ["function", "class"]:
                identifier = reference.replace('()', '').split('.')[-1]
                if doc_file in dependencies:
                    for source_file in dependencies[doc_file]:
                        # Simple heuristic: if the identifier appears in the source file path or name
                        if identifier.lower() in source_file.lower():
                            matched_ref_pairs.add((doc_file, reference))
                            break

        # Add unmatched references as separate entries
        for ref in all_references:
            ref_type = ref["type"]
            reference = ref["reference"]
            doc_file = ref["doc_file"]

            # For non-file references that weren't matched, add as separate entries
            if ref_type in ["function", "class", "command", "semantic_command", "config_key"]:
                if (doc_file, reference) not in matched_ref_pairs:
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
                              total_references: int, all_references: list[dict[str, Any]]) -> dict[str, Any]:
    """Format dependency tracking report."""
    return {
        "generated_at": datetime.now().isoformat(),
        "total_references": total_references,
        "total_doc_files": len(dependencies),
        "total_source_files": len(reverse_index),
        "doc_to_code": dependencies,
        "code_to_doc": reverse_index
    }


async def track_dependencies(params: TrackDependenciesInput) -> dict[str, Any]:
    """Track dependencies between documentation and source code.

    Analyzes documentation files to find references to source code,
    building a bidirectional dependency graph.

    Reference Types Detected:
    1. File paths (literal): `cmd/add.go`, `internal/vault/vault.go`
    2. Functions/methods: `SaveVault()`, `LoadConfig()`
    3. Classes/types: `VaultService`, `Config`
    4. Commands (literal): `pass-cli add`, `generate --length 20`
    5. Commands (semantic): "add command", "the generate subcommand"
    6. Config keys: `vault_path`, `platform: hugo`

    Semantic Detection:
    - Detects command phrases like "add command", "generate subcommand"
    - Maps to implementation files using project conventions
    - Supports patterns: cmd/{name}.go, cli/{name}.py, commands/{name}.js
    - Example: "add command" in docs → matches cmd/add.go

    Returns:
        Dependency graph with doc_to_code and code_to_doc mappings
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return {"error": f"Project path does not exist: {project_path}"}

        # Find docs directory (use provided path or auto-detect)
        if params.docs_path:
            docs_path = project_path / params.docs_path
            if not docs_path.exists():
                return {"error": f"Documentation directory not found at {docs_path}"}
        else:
            docs_path = find_docs_directory(project_path)
            if not docs_path:
                return {"error": "Could not find documentation directory. Specify docs_path parameter."}

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

        # Build symbol index with TreeSitter for accurate validation
        symbol_index = None
        try:
            indexer = SymbolIndexer()
            indexer.index_project(project_path)
            symbol_index = indexer
            print(f"Indexed {indexer.get_index_stats()['total_symbols']} symbols from {indexer.get_index_stats()['files_indexed']} files", file=sys.stderr)
        except Exception as e:
            print(f"Warning: TreeSitter indexing failed: {e}. Falling back to file-based matching.", file=sys.stderr)

        # Match references to actual source files (with symbol index validation)
        dependencies = _match_references_to_sources(all_references, source_files, project_path, symbol_index)

        # Build reverse index (source file/reference -> docs)
        # Includes both matched files and unmatched references
        reverse_index = _build_reverse_index(dependencies, all_references)

        # Build reference index (reference text -> docs that mention it)
        reference_index = _build_reference_index(all_references)

        # Save to memory
        _save_dependencies_to_memory(project_path, dependencies, reverse_index, all_references, reference_index)

        return _format_dependency_report(dependencies, reverse_index, len(all_references), all_references)

    except Exception as e:
        return {"error": str(e), "tool": "track_dependencies"}
