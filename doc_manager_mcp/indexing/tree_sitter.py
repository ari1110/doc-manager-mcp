"""TreeSitter-based code symbol indexer for accurate AST parsing."""

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..utils import load_config, matches_exclude_pattern

# TreeSitter imports (will be available after pip install)
if TYPE_CHECKING:
    from tree_sitter import Language, Parser

try:
    from tree_sitter import Language, Parser
    from tree_sitter_language_pack import get_language

    # Load languages from the language pack
    go_language = get_language("go")
    py_language = get_language("python")
    js_language = get_language("javascript")
    ts_language = get_language("typescript")
    tsx_language = get_language("tsx")
    md_language = get_language("markdown")
    bash_language = get_language("bash")
    yaml_language = get_language("yaml")

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    go_language = None
    py_language = None
    js_language = None
    ts_language = None
    tsx_language = None
    md_language = None
    bash_language = None
    yaml_language = None
    print(
        "Warning: TreeSitter not available. Run: pip install tree-sitter tree-sitter-language-pack",
        file=sys.stderr,
    )


class SymbolType(str, Enum):
    """Types of code symbols that can be indexed."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    STRUCT = "struct"
    INTERFACE = "interface"
    TYPE = "type"
    CONSTANT = "constant"
    VARIABLE = "variable"
    COMMAND = "command"  # CLI command registration


@dataclass
class Symbol:
    """Represents a code symbol found in the codebase."""

    name: str
    type: SymbolType
    file: str  # Relative path from project root
    line: int
    column: int
    signature: str | None = None  # Full signature for functions/methods
    parent: str | None = None  # Parent class/struct for methods
    doc: str | None = None  # Documentation string


class SymbolIndexer:
    """
    TreeSitter-based code indexer that builds accurate symbol maps.

    Parses source files using language-specific AST parsers to extract
    functions, classes, types, and other symbols. Much more accurate than
    regex-based text search.
    """

    def __init__(self):
        """Initialize the symbol indexer with language parsers."""
        if not TREE_SITTER_AVAILABLE:
            raise ImportError(
                "TreeSitter dependencies not installed. "
                "Run: pip install tree-sitter tree-sitter-language-pack"
            )

        # Initialize parsers for each supported language
        # Language pack returns Language objects directly (no call needed)
        # Languages are guaranteed to be available here due to TREE_SITTER_AVAILABLE check
        assert go_language is not None
        assert py_language is not None
        assert js_language is not None
        assert ts_language is not None
        assert tsx_language is not None
        assert md_language is not None
        assert bash_language is not None
        assert yaml_language is not None

        self.parsers = {
            "go": self._create_parser(go_language),
            "python": self._create_parser(py_language),
            "javascript": self._create_parser(js_language),
            "typescript": self._create_parser(ts_language),
            "tsx": self._create_parser(tsx_language),
            "markdown": self._create_parser(md_language),
            "bash": self._create_parser(bash_language),
            "yaml": self._create_parser(yaml_language),
        }

        # Symbol index: symbol_name -> list of Symbol objects
        # Multiple symbols can have same name (overloading, different files)
        self.index: dict[str, list[Symbol]] = {}

    def _create_parser(self, language: Language) -> Parser:
        """Create a TreeSitter parser for a language."""
        parser = Parser(language)
        return parser

    def index_project(self, project_path: Path, file_patterns: list[str] | None = None) -> dict[str, list[Symbol]]:
        """
        Index all source files in a project.

        Args:
            project_path: Root directory of the project
            file_patterns: Optional list of glob patterns (e.g., ["src/**/*.go"])

        Returns:
            Symbol index dictionary
        """
        self.index = {}

        # Load configuration if available
        config = load_config(project_path)

        # Determine file patterns: config sources > provided patterns > defaults
        if config and config.get("sources"):
            file_patterns = config["sources"]
        elif not file_patterns:
            file_patterns = [
                "**/*.go",
                "**/*.py",
                "**/*.js",
                "**/*.ts",
                "**/*.tsx",
            ]

        # Merge user excludes with hardcoded defaults
        default_excludes = [
            "node_modules/**",
            "vendor/**",
            "venv/**",
            ".venv/**",
            ".git/**",
            "dist/**",
            "build/**",
            "__pycache__/**",
            ".pytest_cache/**",
        ]
        user_excludes = config.get("exclude", []) if config else []
        exclude_patterns = default_excludes + user_excludes

        source_files = []
        for pattern in file_patterns:
            for file_path in project_path.glob(pattern):
                if not file_path.is_file():
                    continue

                # Get relative path for pattern matching
                try:
                    relative_path = str(file_path.relative_to(project_path))
                except ValueError:
                    continue

                # Check if excluded using proper pattern matching
                if matches_exclude_pattern(relative_path, exclude_patterns):
                    continue

                source_files.append(file_path)

        # Index each file
        for file_path in source_files:
            try:
                self._index_file(file_path, project_path)
            except Exception as e:
                print(f"Warning: Failed to index {file_path}: {e}", file=sys.stderr)
                continue

        return self.index

    def _index_file(self, file_path: Path, project_path: Path):
        """Index symbols in a single file."""
        # Determine language from extension
        ext = file_path.suffix.lstrip(".")
        language = None

        if ext == "go":
            language = "go"
        elif ext == "py":
            language = "python"
        elif ext in ("js", "jsx"):
            language = "javascript"
        elif ext == "ts":
            language = "typescript"
        elif ext == "tsx":
            language = "tsx"

        if not language or language not in self.parsers:
            return

        # Read file content
        try:
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()
        except Exception:
            return

        # Parse with TreeSitter
        parser = self.parsers[language]
        tree = parser.parse(bytes(source_code, "utf8"))

        # Extract symbols based on language
        relative_path = str(file_path.relative_to(project_path)).replace("\\", "/")

        if language == "go":
            self._extract_go_symbols(tree.root_node, source_code, relative_path)
        elif language == "python":
            self._extract_python_symbols(tree.root_node, source_code, relative_path)
        elif language in ("javascript", "typescript", "tsx"):
            self._extract_js_symbols(tree.root_node, source_code, relative_path)

    def _extract_go_symbols(self, node: Any, source: str, file_path: str):
        """Extract symbols from Go AST."""
        # Function declarations
        for func_node in self._find_nodes(node, "function_declaration"):
            name_node = self._find_child(func_node, "identifier")
            if name_node:
                name = self._get_node_text(name_node, source)
                signature = self._get_node_text(func_node, source).split("{")[0].strip()

                symbol = Symbol(
                    name=name,
                    type=SymbolType.FUNCTION,
                    file=file_path,
                    line=func_node.start_point[0] + 1,
                    column=func_node.start_point[1],
                    signature=signature,
                )
                self._add_symbol(symbol)

        # Method declarations
        for method_node in self._find_nodes(node, "method_declaration"):
            name_node = self._find_child(method_node, "field_identifier")
            if name_node:
                name = self._get_node_text(name_node, source)
                signature = self._get_node_text(method_node, source).split("{")[0].strip()

                # Try to find receiver type
                receiver_node = self._find_child(method_node, "parameter_list")
                parent_type = None
                if receiver_node and receiver_node.children:
                    for child in receiver_node.children:
                        if child.type == "parameter_declaration":
                            type_node = self._find_child(child, "type_identifier")
                            if type_node:
                                parent_type = self._get_node_text(type_node, source)
                                break

                symbol = Symbol(
                    name=name,
                    type=SymbolType.METHOD,
                    file=file_path,
                    line=method_node.start_point[0] + 1,
                    column=method_node.start_point[1],
                    signature=signature,
                    parent=parent_type,
                )
                self._add_symbol(symbol)

        # Type declarations (structs, interfaces)
        for type_node in self._find_nodes(node, "type_declaration"):
            for spec in type_node.children:
                if spec.type == "type_spec":
                    name_node = self._find_child(spec, "type_identifier")
                    if name_node:
                        name = self._get_node_text(name_node, source)
                        # Determine if struct or interface
                        symbol_type = SymbolType.TYPE
                        for child in spec.children:
                            if child.type == "struct_type":
                                symbol_type = SymbolType.STRUCT
                            elif child.type == "interface_type":
                                symbol_type = SymbolType.INTERFACE

                        symbol = Symbol(
                            name=name,
                            type=symbol_type,
                            file=file_path,
                            line=type_node.start_point[0] + 1,
                            column=type_node.start_point[1],
                        )
                        self._add_symbol(symbol)

    def _extract_python_symbols(self, node: Any, source: str, file_path: str):
        """Extract symbols from Python AST."""
        # Function definitions
        for func_node in self._find_nodes(node, "function_definition"):
            name_node = self._find_child(func_node, "identifier")
            if name_node:
                name = self._get_node_text(name_node, source)
                signature = self._get_node_text(func_node, source).split(":")[0].strip()

                symbol = Symbol(
                    name=name,
                    type=SymbolType.FUNCTION,
                    file=file_path,
                    line=func_node.start_point[0] + 1,
                    column=func_node.start_point[1],
                    signature=signature,
                )
                self._add_symbol(symbol)

        # Class definitions
        for class_node in self._find_nodes(node, "class_definition"):
            name_node = self._find_child(class_node, "identifier")
            if name_node:
                name = self._get_node_text(name_node, source)

                symbol = Symbol(
                    name=name,
                    type=SymbolType.CLASS,
                    file=file_path,
                    line=class_node.start_point[0] + 1,
                    column=class_node.start_point[1],
                )
                self._add_symbol(symbol)

                # Extract methods within class
                for method_node in self._find_nodes(class_node, "function_definition"):
                    method_name_node = self._find_child(method_node, "identifier")
                    if method_name_node:
                        method_name = self._get_node_text(method_name_node, source)
                        signature = self._get_node_text(method_node, source).split(":")[0].strip()

                        method_symbol = Symbol(
                            name=method_name,
                            type=SymbolType.METHOD,
                            file=file_path,
                            line=method_node.start_point[0] + 1,
                            column=method_node.start_point[1],
                            signature=signature,
                            parent=name,
                        )
                        self._add_symbol(method_symbol)

    def _extract_js_symbols(self, node: Any, source: str, file_path: str):
        """Extract symbols from JavaScript/TypeScript AST."""
        # Function declarations
        for func_node in self._find_nodes(node, "function_declaration"):
            name_node = self._find_child(func_node, "identifier")
            if name_node:
                name = self._get_node_text(name_node, source)
                signature = self._get_node_text(func_node, source).split("{")[0].strip()

                symbol = Symbol(
                    name=name,
                    type=SymbolType.FUNCTION,
                    file=file_path,
                    line=func_node.start_point[0] + 1,
                    column=func_node.start_point[1],
                    signature=signature,
                )
                self._add_symbol(symbol)

        # Class declarations
        for class_node in self._find_nodes(node, "class_declaration"):
            name_node = self._find_child(class_node, "identifier") or self._find_child(
                class_node, "type_identifier"
            )
            if name_node:
                name = self._get_node_text(name_node, source)

                symbol = Symbol(
                    name=name,
                    type=SymbolType.CLASS,
                    file=file_path,
                    line=class_node.start_point[0] + 1,
                    column=class_node.start_point[1],
                )
                self._add_symbol(symbol)

        # Arrow functions assigned to variables/constants
        for var_node in self._find_nodes(node, "lexical_declaration"):
            for declarator in self._find_nodes(var_node, "variable_declarator"):
                name_node = self._find_child(declarator, "identifier")
                value_node = self._find_child(declarator, "arrow_function")
                if name_node and value_node:
                    name = self._get_node_text(name_node, source)
                    signature = self._get_node_text(declarator, source).split("=>")[0].strip() + "=> ..."

                    symbol = Symbol(
                        name=name,
                        type=SymbolType.FUNCTION,
                        file=file_path,
                        line=var_node.start_point[0] + 1,
                        column=var_node.start_point[1],
                        signature=signature,
                    )
                    self._add_symbol(symbol)

    def _find_nodes(self, node: Any, node_type: str) -> list[Any]:
        """Recursively find all nodes of a specific type."""
        nodes = []

        def traverse(n):
            if n.type == node_type:
                nodes.append(n)
            for child in n.children:
                traverse(child)

        traverse(node)
        return nodes

    def _find_child(self, node: Any, child_type: str) -> Any | None:
        """Find first direct child of a specific type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def _get_node_text(self, node: Any, source: str) -> str:
        """Get the source text for a node."""
        return source[node.start_byte : node.end_byte]

    def _add_symbol(self, symbol: Symbol):
        """Add a symbol to the index."""
        if symbol.name not in self.index:
            self.index[symbol.name] = []
        self.index[symbol.name].append(symbol)

    def lookup(self, symbol_name: str) -> list[Symbol]:
        """Look up symbols by name."""
        return self.index.get(symbol_name, [])

    def get_symbols_in_file(self, file_path: str) -> list[Symbol]:
        """Get all symbols defined in a specific file."""
        symbols = []
        for symbol_list in self.index.values():
            for symbol in symbol_list:
                if symbol.file == file_path:
                    symbols.append(symbol)
        return symbols

    def get_all_symbols(self) -> list[Symbol]:
        """Get all indexed symbols."""
        all_symbols = []
        for symbol_list in self.index.values():
            all_symbols.extend(symbol_list)
        return all_symbols

    def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about the symbol index."""
        type_counts = {}
        files = set()

        for symbol_list in self.index.values():
            for symbol in symbol_list:
                type_counts[symbol.type] = type_counts.get(symbol.type, 0) + 1
                files.add(symbol.file)

        return {
            "total_symbols": sum(len(syms) for syms in self.index.values()),
            "unique_names": len(self.index),
            "files_indexed": len(files),
            "by_type": type_counts,
        }

    def extract_bash_code_blocks(self, content: str) -> list[str]:
        """Extract bash code from fenced code blocks in markdown.

        Args:
            content: Markdown file content

        Returns:
            List of code block contents (strings)
        """
        if "markdown" not in self.parsers:
            return []

        # TreeSitter works with bytes - convert once and use throughout
        source_bytes = content.encode("utf8")
        tree = self.parsers["markdown"].parse(source_bytes)
        code_blocks = []

        # Find all fenced code blocks
        for node in self._find_all_nodes(tree.root_node, "fenced_code_block"):
            # Check if it's a bash/shell block
            info_node = self._find_child_by_type(node, "info_string")
            if info_node:
                # Extract from bytes, then decode
                lang = source_bytes[info_node.start_byte:info_node.end_byte].decode("utf8").strip()
                if lang in ("bash", "sh", "shell", "console"):
                    # Get the code content
                    code_node = self._find_child_by_type(node, "code_fence_content")
                    if code_node:
                        # Extract from bytes, then decode
                        code = source_bytes[code_node.start_byte:code_node.end_byte].decode("utf8")
                        code_blocks.append(code)

        return code_blocks

    def _find_all_nodes(self, node: Any, node_type: str) -> list[Any]:
        """Recursively find all nodes of a given type."""
        results = []
        if node.type == node_type:
            results.append(node)
        for child in node.children:
            results.extend(self._find_all_nodes(child, node_type))
        return results

    def _find_child_by_type(self, node: Any, child_type: str) -> Any | None:
        """Find first child node with given type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None
