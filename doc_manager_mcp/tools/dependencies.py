"""Dependency tracking tools for doc-manager."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from ..constants import CLASS_PATTERN, FUNCTION_PATTERN, MAX_FILES
from ..indexing import SymbolIndexer
from ..indexing.markdown_parser import MarkdownParser
from ..models import TrackDependenciesInput
from ..utils import (
    file_lock,
    find_docs_directory,
    find_markdown_files,
    validate_path_boundary,
)

# ============================================================================
# T082: Compiled regex patterns for performance (FR-023)
# REFACTORED: Patterns now match content WITHOUT backticks (for use with MarkdownParser)
# NOTE: FUNCTION_PATTERN and CLASS_PATTERN imported from constants.py
# ============================================================================

# Extract file path references - matches content only (no backticks)
FILE_PATH_PATTERN = re.compile(r'^([a-zA-Z0-9_\-/.]+\.(go|py|js|ts|tsx|jsx|java|rs|rb|php|c|cpp|h|hpp|cs|swift|kt|yaml|yml|json|cfg))$')

# Match markdown headings with function signatures (unchanged - doesn't use inline code)
HEADING_FUNCTION_PATTERN = re.compile(r'^#+\s+([a-z_][a-zA-Z0-9_]*)\s*\([^)]*\)', re.MULTILINE)

# Extract command references - matches content only (no backticks)
# NOTE: Inline code commands will be extracted via MarkdownParser, this pattern validates them
COMMAND_PATTERN = re.compile(r'^([a-z][a-z0-9\-]+(?:\s+[a-z][a-z0-9\-]+)*(?:\s+--?[a-z][a-z0-9\-]*)*)$')

# Extract commands from terminal prompts in raw content (still needed for non-inline-code cases)
TERMINAL_COMMAND_PATTERN = re.compile(r'\$\s+([a-z][a-z0-9\-]+(?:\s+[a-z][a-z0-9\-]+)*(?:\s+--?[a-z][a-z0-9\-]*)*)')

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

# Universal blocklist of common tools that are almost never project-specific
UNIVERSAL_BLOCKLIST = {
    'git', 'docker', 'npm', 'yarn', 'pip', 'brew', 'apt', 'yum', 'dnf',
    'curl', 'wget', 'tar', 'zip', 'unzip', 'ssh', 'scp', 'rsync',
    'sudo', 'su', 'chmod', 'chown', 'apt-get', 'systemctl', 'service',
    'ps', 'kill', 'top', 'htop', 'df', 'du', 'mount', 'umount',
    'make', 'cmake', 'gcc', 'clang', 'javac', 'maven', 'gradle',
    'python', 'python3', 'node', 'ruby', 'php', 'java', 'go',
    'bash', 'sh', 'zsh', 'fish', 'powershell', 'cmd',
}


def _detect_project_name(project_path: Path) -> str | None:
    """Auto-detect the project's CLI command name.

    Detection order:
    1. .doc-manager.yml config file (project_name field)
    2. Git repository name
    3. Parent directory name

    Args:
        project_path: Path to project root

    Returns:
        Detected project name or None
    """
    # Try .doc-manager.yml config
    config_path = project_path / '.doc-manager.yml'
    if config_path.exists():
        try:
            import yaml
            with open(config_path, encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config and 'project_name' in config:
                    return config['project_name']
        except Exception:  # noqa: S110
            pass  # Fail gracefully if yaml not available or file malformed

    # Try git repository name
    git_dir = project_path / '.git'
    if git_dir.exists() and git_dir.is_dir():
        try:
            # Get remote URL
            config_file = git_dir / 'config'
            if config_file.exists():
                with open(config_file, encoding='utf-8') as f:
                    content = f.read()
                    # Extract repo name from URL
                    match = re.search(r'url = .*/([^/]+?)(?:\.git)?$', content, re.MULTILINE)
                    if match:
                        return match.group(1)
        except Exception:  # noqa: S110
            pass  # Graceful fallback to directory name

    # Fallback: use directory name
    return project_path.name


def _extract_subcommand(reference: str) -> str | None:
    """Extract subcommand chain from a command reference.

    Handles references like:
    - "pass-cli vault backup create" → "vault_backup_create"
    - "pass-cli add github" → "add"
    - "git commit -m" → "commit"
    - "docker run --rm" → "run"
    - "add" → "add"

    Args:
        reference: Command reference string

    Returns:
        Subcommand name (with underscores for multi-word) or None if not found
    """
    # Known CLI tool names to skip
    cli_tools = {
        "pass-cli", "git", "docker", "npm", "yarn", "pip", "cargo",
        "go", "node", "python", "python3", "ruby", "php", "java",
        "kubectl", "helm", "terraform", "ansible", "make", "brew"
    }

    words = reference.strip().split()
    if not words:
        return None

    # Determine starting position (skip CLI tool name if present)
    start_idx = 1 if words[0] in cli_tools else 0

    # Collect all subcommand words (stop at flags or arguments)
    subcommands = []
    for i in range(start_idx, len(words)):
        word = words[i]

        # Stop at flags
        if word.startswith('-'):
            break

        # Check if word is a valid subcommand name (lowercase, alphanumeric, hyphens)
        if re.match(r'^[a-z][a-z0-9\-]*$', word):
            subcommands.append(word)
        else:
            # Stop at first non-subcommand word (likely an argument)
            break

    if not subcommands:
        return None

    # Join multi-word subcommands with underscores (e.g., "vault backup create" → "vault_backup_create")
    return '_'.join(subcommands)




def _extract_code_references(content: str, doc_file: Path) -> list[dict[str, Any]]:
    """Extract code references from documentation content (REFACTORED - uses MarkdownParser)."""
    parser = MarkdownParser()
    references = []

    # Extract all inline code spans using MarkdownParser
    inline_codes = parser.extract_inline_code(content)

    # Process each inline code span and classify by type
    for code_span in inline_codes:
        code_text = code_span["text"]
        line = code_span["line"]

        # Check if it's a file path
        if match := FILE_PATH_PATTERN.match(code_text):
            references.append({
                "type": "file_path",
                "reference": match.group(1),
                "doc_file": str(doc_file),
                "line": line  # NEW: line number tracking
            })
            continue

        # Check if it's a function reference
        if match := FUNCTION_PATTERN.match(code_text):
            references.append({
                "type": "function",
                "reference": code_text,
                "doc_file": str(doc_file),
                "line": line  # NEW
            })
            continue

        # Check if it's a class reference
        if match := CLASS_PATTERN.match(code_text):
            class_name = match.group(1)
            # Exclude common words
            if len(class_name) > 2 and class_name not in ['API', 'CLI', 'HTTP', 'HTTPS', 'URL', 'JSON', 'XML']:
                references.append({
                    "type": "class",
                    "reference": class_name,
                    "doc_file": str(doc_file),
                    "line": line  # NEW
                })
            continue

        # Check if it's a command reference
        if match := COMMAND_PATTERN.match(code_text):
            command = match.group(1)
            first_word = command.split()[0]
            # Filter out common prose words
            if first_word not in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'your', 'you', 'a', 'an', 'in', 'on', 'at', 'to', 'of']:
                references.append({
                    "type": "command",
                    "reference": command,
                    "doc_file": str(doc_file),
                    "line": line  # NEW
                })
            continue

        # Check if it's a config key (dotted path, key:value, or simple key)
        # Dotted path: server.port
        if '.' in code_text and re.match(r'^[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+$', code_text):
            references.append({
                "type": "config_key",
                "reference": code_text,
                "doc_file": str(doc_file),
                "line": line  # NEW
            })
            continue

        # Config key with colon: platform: hugo
        if ':' in code_text:
            if match := re.match(r'^([a-z_][a-z0-9_]{2,}):', code_text):
                config_key = match.group(1)
                if config_key not in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'your', 'you', 'file', 'path', 'name', 'type']:
                    references.append({
                        "type": "config_key",
                        "reference": config_key,
                        "doc_file": str(doc_file),
                        "line": line  # NEW
                    })
            continue

        # Simple config key: platform, docs_path (at least 3 chars)
        if len(code_text) >= 3 and re.match(r'^[a-z_][a-z0-9_]{2,}$', code_text):
            if code_text not in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'your', 'you', 'file', 'path', 'name', 'type']:
                references.append({
                    "type": "config_key",
                    "reference": code_text,
                    "doc_file": str(doc_file),
                    "line": line  # NEW
                })

    # Extract function signatures from markdown headings (doesn't use inline code)
    for match in HEADING_FUNCTION_PATTERN.finditer(content):
        func_name = match.group(1) + "()"
        line_num = content[:match.start()].count('\n') + 1
        references.append({
            "type": "function",
            "reference": func_name,
            "doc_file": str(doc_file),
            "line": line_num  # NEW
        })

    # Extract commands from terminal prompts in raw content (e.g., "$ command")
    for match in TERMINAL_COMMAND_PATTERN.finditer(content):
        command = match.group(1)
        first_word = command.split()[0]
        if first_word not in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'your', 'you', 'a', 'an', 'in', 'on', 'at', 'to', 'of']:
            line_num = content[:match.start()].count('\n') + 1
            references.append({
                "type": "command",
                "reference": command,
                "doc_file": str(doc_file),
                "line": line_num  # NEW
            })

    # Extract semantic command references (phrases like "add command", "generate subcommand")
    command_stopwords = {'run', 'help', 'version', 'test', 'build', 'install', 'start', 'stop', 'restart'}
    seen_commands = set()

    for pattern in SEMANTIC_COMMAND_PATTERNS:
        for match in pattern.finditer(content):
            command_name = match.group(1).lower()
            if command_name not in command_stopwords and command_name not in seen_commands:
                seen_commands.add(command_name)
                line_num = content[:match.start()].count('\n') + 1
                references.append({
                    "type": "semantic_command",
                    "reference": command_name,
                    "doc_file": str(doc_file),
                    "line": line_num  # NEW
                })

    return references


def _extract_commands_from_code_blocks(content: str, doc_file: Path, indexer: SymbolIndexer | None = None, project_name: str | None = None) -> list[dict[str, Any]]:
    """Extract command references from fenced code blocks using TreeSitter.

    Only extracts commands matching the project name to reduce noise.

    Args:
        content: Documentation file content
        doc_file: Path to documentation file
        indexer: Optional SymbolIndexer with markdown parser
        project_name: Project CLI name to filter for (e.g., "pass-cli")

    Returns:
        List of command references from code blocks
    """
    references = []

    # Skip if TreeSitter not available or no project name
    if not indexer or not project_name:
        return references

    try:
        # Extract bash code blocks using TreeSitter markdown parser
        code_blocks = indexer.extract_bash_code_blocks(content)

        # Parse each code block for commands
        for block in code_blocks:
            lines = block.strip().split('\n')

            for line in lines:
                # Skip comments and empty lines
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Remove shell prompts ($ or #)
                if line.startswith(('$ ', '# ')):
                    line = line[2:]

                # Skip variable assignments (export FOO=bar, VAR=value)
                if re.match(r'^[A-Z_]+=', line):
                    continue

                # Skip control structures (if, for, while, etc.)
                if re.match(r'^\s*(if|then|else|elif|fi|for|while|do|done|case|esac)\b', line):
                    continue

                # Extract command (first word(s) before flags)
                words = line.split()
                if not words:
                    continue

                # Build command string (tool + subcommand, stop at flags)
                command_words = []
                for word in words:
                    if word.startswith('-'):
                        break
                    # Stop at pipes, redirects, or other shell operators
                    if word in ('|', '>', '>>', '<', '&&', '||', ';'):
                        break
                    command_words.append(word)

                if not command_words:
                    continue

                command = ' '.join(command_words)
                first_word = command_words[0]

                # Skip if first word is in universal blocklist
                if first_word in UNIVERSAL_BLOCKLIST:
                    continue

                # Only extract commands that start with the project name
                if not command.startswith(project_name):
                    continue

                # Add command reference
                references.append({
                    "type": "command",
                    "reference": command,
                    "doc_file": str(doc_file)
                })

    except Exception as e:
        # Fail gracefully if TreeSitter markdown parsing fails
        print(f"Warning: Failed to extract code blocks from {doc_file}: {e}", file=sys.stderr)

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
            command_name = _extract_subcommand(reference)
            if not command_name:
                continue  # Skip if we couldn't extract a valid subcommand
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


def _build_reverse_index(dependencies: dict[str, list[str]], all_references: list[dict[str, Any]] | None = None, project_name: str | None = None) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Build reverse indices: code_to_doc (real files) and unmatched_references (strings).

    Filters unmatched_references to only include project-relevant references.

    Args:
        dependencies: Mapping of doc files to matched source files
        all_references: All extracted references
        project_name: Project name for filtering (e.g., "pass-cli")

    Returns:
        tuple: (code_to_doc, unmatched_references)
            - code_to_doc: Real source file paths -> [doc_files]
            - unmatched_references: Unmatched reference strings -> [doc_files]
    """
    code_to_doc = {}
    unmatched_refs = {}

    # Add matched source files to code_to_doc
    for doc_file, source_files in dependencies.items():
        for source_file in source_files:
            if source_file not in code_to_doc:
                code_to_doc[source_file] = []
            code_to_doc[source_file].append(doc_file)

    # Separate unmatched references into their own dictionary
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

        # Add unmatched references to separate dictionary (filtered)
        for ref in all_references:
            ref_type = ref["type"]
            reference = ref["reference"]
            doc_file = ref["doc_file"]

            # For non-file references that weren't matched, add to unmatched_refs
            if ref_type in ["function", "class", "command", "semantic_command", "config_key"]:
                if (doc_file, reference) not in matched_ref_pairs:
                    # Filter: Only include project-relevant references
                    if ref_type == "command" and project_name:
                        # For commands, only include if it starts with project name
                        first_word = reference.split()[0] if reference else ""
                        if first_word in UNIVERSAL_BLOCKLIST or not reference.startswith(project_name):
                            continue  # Skip blocklisted or non-project commands

                    # Add to unmatched refs
                    if reference not in unmatched_refs:
                        unmatched_refs[reference] = []
                    if doc_file not in unmatched_refs[reference]:
                        unmatched_refs[reference].append(doc_file)

    return code_to_doc, unmatched_refs


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
                                 code_to_doc: dict[str, list[str]], unmatched_refs: dict[str, list[str]],
                                 all_references: list[dict[str, Any]] | None = None,
                                 reference_index: dict[str, list[str]] | None = None):
    """Save dependency graph to memory directory with separated file and reference mappings."""
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
        "code_to_doc": code_to_doc,  # ✓ ONLY real source files
        "unmatched_references": unmatched_refs  # ✓ SEPARATED
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


def _format_dependency_report(dependencies: dict[str, list[str]], code_to_doc: dict[str, list[str]],
                              unmatched_refs: dict[str, list[str]], total_references: int,
                              all_references: list[dict[str, Any]],
                              tree_sitter_stats: dict[str, Any] | None = None) -> dict[str, Any]:
    """Format dependency tracking report with separated file and reference mappings."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_references": total_references,
        "total_doc_files": len(dependencies),
        "total_source_files": len(code_to_doc),  # ✓ ACCURATE: only real files
        "total_unmatched_references": len(unmatched_refs),  # ✓ NEW
        "doc_to_code": dependencies,
        "code_to_doc": code_to_doc,  # ✓ ONLY real source files
        "unmatched_references": unmatched_refs  # ✓ SEPARATED
    }

    # Add TreeSitter indexing stats if available
    if tree_sitter_stats:
        report["tree_sitter"] = tree_sitter_stats

    return report


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

        # Detect project name for smart command filtering
        project_name = _detect_project_name(project_path)
        print(f"Detected project name: {project_name}", file=sys.stderr)

        # Find source files and build TreeSitter index FIRST (needed for markdown extraction)
        source_files = _find_source_files(project_path, docs_path)

        # Build symbol index with TreeSitter for accurate validation
        symbol_index = None
        tree_sitter_stats = None
        try:
            indexer = SymbolIndexer()
            indexer.index_project(project_path)
            symbol_index = indexer
            stats = indexer.get_index_stats()
            tree_sitter_stats = {
                "enabled": True,
                "total_symbols": stats['total_symbols'],
                "files_indexed": stats['files_indexed'],
                "by_type": stats['by_type']
            }
            print(f"TreeSitter: Indexed {stats['total_symbols']} symbols from {stats['files_indexed']} files", file=sys.stderr)
        except Exception as e:
            tree_sitter_stats = {
                "enabled": False,
                "error": str(e)
            }
            print(f"Warning: TreeSitter indexing failed: {e}. Falling back to file-based matching.", file=sys.stderr)

        # Find all markdown files
        markdown_files = find_markdown_files(docs_path, project_path, validate_boundaries=True)
        all_references = []

        if markdown_files:
            # Extract references from all docs (using TreeSitter for code blocks)
            for md_file in markdown_files:
                try:
                    with open(md_file, encoding='utf-8') as f:
                        content = f.read()

                    # Extract inline references (backticks, prose)
                    references = _extract_code_references(content, md_file.relative_to(docs_path))
                    all_references.extend(references)

                    # Extract commands from fenced code blocks (TreeSitter markdown)
                    code_block_refs = _extract_commands_from_code_blocks(content, md_file.relative_to(docs_path), symbol_index, project_name)
                    all_references.extend(code_block_refs)
                except Exception as e:
                    print(f"Warning: Failed to read markdown file {md_file}: {e}", file=sys.stderr)
                    continue

        # Match references to actual source files (with symbol index validation)
        dependencies = _match_references_to_sources(all_references, source_files, project_path, symbol_index)

        # Build reverse indices: code_to_doc (real files) and unmatched_references (strings)
        code_to_doc, unmatched_refs = _build_reverse_index(dependencies, all_references, project_name)

        # Build reference index (reference text -> docs that mention it)
        reference_index = _build_reference_index(all_references)

        # Save to memory
        _save_dependencies_to_memory(project_path, dependencies, code_to_doc, unmatched_refs, all_references, reference_index)

        return _format_dependency_report(dependencies, code_to_doc, unmatched_refs, len(all_references), all_references, tree_sitter_stats)

    except Exception as e:
        return {"error": str(e), "tool": "track_dependencies"}
