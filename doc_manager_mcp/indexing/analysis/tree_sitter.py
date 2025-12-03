"""TreeSitter-based code symbol indexer for accurate AST parsing."""

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from doc_manager_mcp.core import load_config, matches_exclude_pattern

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
    rust_language = get_language("rust")

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
    rust_language = None
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
    CONFIG_FIELD = "config_field"  # Configuration field in config models


@dataclass
class ConfigField:
    """Represents a configuration field in a config struct/class/model.

    Used to track field-level changes in configuration models across
    Python (Pydantic, dataclass, TypedDict, attrs), Go (yaml/json tags),
    TypeScript (interface properties), and Rust (serde derives).
    """

    name: str
    parent_symbol: str  # Name of parent class/struct
    field_type: str | None  # Type annotation (e.g., "str", "int | None")
    default_value: str | None  # Default value as string
    file: str  # Relative path from project root
    line: int
    column: int
    tags: dict[str, str] | None = None  # Go yaml/json, Rust serde attrs
    is_optional: bool = False  # Whether field is optional
    doc: str | None = None  # Field docstring or description


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
    config_fields: list[ConfigField] | None = None  # Config fields if this is a config model


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
        assert rust_language is not None

        self.parsers = {
            "go": self._create_parser(go_language),
            "python": self._create_parser(py_language),
            "javascript": self._create_parser(js_language),
            "typescript": self._create_parser(ts_language),
            "tsx": self._create_parser(tsx_language),
            "markdown": self._create_parser(md_language),
            "bash": self._create_parser(bash_language),
            "yaml": self._create_parser(yaml_language),
            "rust": self._create_parser(rust_language),
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
        if not file_patterns:
            file_patterns = [
                "**/*.go",
                "**/*.py",
                "**/*.js",
                "**/*.ts",
                "**/*.tsx",
                "**/*.rs",
            ]

        # Merge user excludes with hardcoded defaults (correct priority: user > gitignore > defaults)
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
        use_gitignore = config.get("use_gitignore", False) if config else False

        # Build exclude patterns with correct priority: user > defaults
        exclude_patterns = []
        exclude_patterns.extend(user_excludes)  # User patterns first (highest priority)
        exclude_patterns.extend(default_excludes)  # Defaults last (lowest priority)

        # Parse .gitignore if enabled (middle priority, checked separately)
        gitignore_spec = None
        if use_gitignore:
            from doc_manager_mcp.core import parse_gitignore
            gitignore_spec = parse_gitignore(project_path)

        source_files = []
        for pattern in file_patterns:
            for file_path in project_path.glob(pattern):
                if not file_path.is_file():
                    continue

                # Get relative path for pattern matching
                try:
                    relative_path = str(file_path.relative_to(project_path)).replace('\\', '/')
                except ValueError:
                    continue

                # Check if excluded using proper pattern matching (user + defaults)
                if matches_exclude_pattern(relative_path, exclude_patterns):
                    continue

                # Check gitignore patterns (if enabled)
                if gitignore_spec and gitignore_spec.match_file(relative_path):
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
        elif ext == "rs":
            language = "rust"

        if not language or language not in self.parsers:
            return

        # Read file content
        try:
            with open(file_path, "rb") as f:
                source_bytes = f.read()
        except Exception:
            return

        # Parse with TreeSitter
        parser = self.parsers[language]
        tree = parser.parse(source_bytes)

        # Extract symbols based on language
        relative_path = str(file_path.relative_to(project_path)).replace("\\", "/")

        if language == "go":
            self._extract_go_symbols(tree.root_node, source_bytes, relative_path)
        elif language == "python":
            self._extract_python_symbols(tree.root_node, source_bytes, relative_path)
        elif language in ("javascript", "typescript", "tsx"):
            self._extract_js_symbols(tree.root_node, source_bytes, relative_path)
        elif language == "rust":
            self._extract_rust_symbols(tree.root_node, source_bytes, relative_path)

    def _extract_go_symbols(self, node: Any, source: bytes, file_path: str):
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
                        struct_type_node = None
                        for child in spec.children:
                            if child.type == "struct_type":
                                symbol_type = SymbolType.STRUCT
                                struct_type_node = child
                            elif child.type == "interface_type":
                                symbol_type = SymbolType.INTERFACE

                        symbol = Symbol(
                            name=name,
                            type=symbol_type,
                            file=file_path,
                            line=type_node.start_point[0] + 1,
                            column=type_node.start_point[1],
                        )

                        # T009: Extract config fields for Go structs
                        if symbol_type == SymbolType.STRUCT and struct_type_node:
                            if self._is_go_config_struct(struct_type_node, source, name):
                                symbol.config_fields = self._extract_go_config_fields(
                                    struct_type_node, name, source, file_path
                                )

                        self._add_symbol(symbol)

    def _extract_python_symbols(self, node: Any, source: bytes, file_path: str):
        """Extract symbols from Python AST.

        Uses processed node tracking to prevent methods from being counted twice
        (once as FUNCTION, once as METHOD). See Phase 1 of data quality bug fix.
        """
        # Track processed function nodes to prevent duplicates (Bug #1 fix)
        processed_func_nodes: set[int] = set()

        # FIRST: Process classes and their methods
        # Build a map of class node to (name, start_line, end_line) for parent attribution
        class_info: dict[int, tuple[str, int, int]] = {}
        for class_node in self._find_nodes(node, "class_definition"):
            name_node = self._find_child(class_node, "identifier")
            if name_node:
                name = self._get_node_text(name_node, source)
                start_line = class_node.start_point[0]
                end_line = class_node.end_point[0]
                class_info[id(class_node)] = (name, start_line, end_line)

        # Process each class
        for class_node in self._find_nodes(node, "class_definition"):
            name_node = self._find_child(class_node, "identifier")
            if name_node:
                name = self._get_node_text(name_node, source)
                current_start = class_node.start_point[0]
                current_end = class_node.end_point[0]

                # Find parent class by checking if this class is within another class's range
                parent_class_name = None
                smallest_parent_range = float('inf')

                for other_id, (other_name, other_start, other_end) in class_info.items():
                    # Skip self
                    if other_id == id(class_node):
                        continue

                    # Check if current class is within other class's range
                    if other_start < current_start and current_end <= other_end:
                        # This is a potential parent - choose the closest (smallest range)
                        parent_range = other_end - other_start
                        if parent_range < smallest_parent_range:
                            smallest_parent_range = parent_range
                            parent_class_name = other_name

                symbol = Symbol(
                    name=name,
                    type=SymbolType.CLASS,
                    file=file_path,
                    line=class_node.start_point[0] + 1,
                    column=class_node.start_point[1],
                    parent=parent_class_name,
                )

                # T009: Extract config fields for Python config classes
                config_type = self._is_python_config_class(class_node, source)
                if config_type:
                    symbol.config_fields = self._extract_python_config_fields(
                        class_node, name, source, file_path, config_type
                    )

                self._add_symbol(symbol)

                # Extract methods within class (only direct methods, not from nested classes)
                for method_node in self._find_direct_methods(class_node):
                    # Mark this node as processed to prevent duplicate counting
                    processed_func_nodes.add(id(method_node))

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

        # SECOND: Process module-level functions (skip already-processed methods)
        for func_node in self._find_nodes(node, "function_definition"):
            # Skip if this node was already processed as a method
            if id(func_node) in processed_func_nodes:
                continue

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

    def _extract_js_symbols(self, node: Any, source: bytes, file_path: str):
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

        # T009: Interface declarations (TypeScript)
        for interface_node in self._find_nodes(node, "interface_declaration"):
            name_node = self._find_child(interface_node, "type_identifier")
            if name_node:
                name = self._get_node_text(name_node, source)

                symbol = Symbol(
                    name=name,
                    type=SymbolType.INTERFACE,
                    file=file_path,
                    line=interface_node.start_point[0] + 1,
                    column=interface_node.start_point[1],
                )

                # Extract config fields for config interfaces
                if self._is_ts_config_interface(interface_node, source, name):
                    symbol.config_fields = self._extract_ts_config_fields(
                        interface_node, name, source, file_path
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

    def _extract_rust_symbols(self, node: Any, source: bytes, file_path: str):
        """Extract symbols from Rust AST: fn, struct, impl, trait."""
        # Function declarations
        for func_node in self._find_nodes(node, "function_item"):
            name_node = self._find_child(func_node, "identifier")
            if name_node:
                name = self._get_node_text(name_node, source)
                # Get signature up to the block
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

        # Struct declarations
        for struct_node in self._find_nodes(node, "struct_item"):
            name_node = self._find_child(struct_node, "type_identifier")
            if name_node:
                name = self._get_node_text(name_node, source)

                symbol = Symbol(
                    name=name,
                    type=SymbolType.STRUCT,
                    file=file_path,
                    line=struct_node.start_point[0] + 1,
                    column=struct_node.start_point[1],
                )

                # T009: Extract config fields for Rust serde structs
                if self._is_rust_config_struct(struct_node, source):
                    symbol.config_fields = self._extract_rust_config_fields(
                        struct_node, name, source, file_path
                    )

                self._add_symbol(symbol)

        # Trait declarations
        for trait_node in self._find_nodes(node, "trait_item"):
            name_node = self._find_child(trait_node, "type_identifier")
            if name_node:
                name = self._get_node_text(name_node, source)

                symbol = Symbol(
                    name=name,
                    type=SymbolType.INTERFACE,  # Traits are like interfaces
                    file=file_path,
                    line=trait_node.start_point[0] + 1,
                    column=trait_node.start_point[1],
                )
                self._add_symbol(symbol)

        # Type aliases
        for type_node in self._find_nodes(node, "type_item"):
            name_node = self._find_child(type_node, "type_identifier")
            if name_node:
                name = self._get_node_text(name_node, source)

                symbol = Symbol(
                    name=name,
                    type=SymbolType.TYPE,
                    file=file_path,
                    line=type_node.start_point[0] + 1,
                    column=type_node.start_point[1],
                )
                self._add_symbol(symbol)

    # ============================================================================
    # Config Detection Methods - T004-T007
    # ============================================================================

    def _is_python_config_class(self, class_node: Any, source: bytes) -> str | None:
        """Detect if class is a config model.

        Returns:
            'pydantic' | 'dataclass' | 'typeddict' | 'attrs' | None
        """
        # Check decorators for @dataclass, @attrs, @define
        # Decorators may be in class_node children OR in parent decorated_definition
        nodes_to_check = [class_node]
        if class_node.parent and class_node.parent.type == "decorated_definition":
            nodes_to_check.append(class_node.parent)

        for node in nodes_to_check:
            for child in node.children:
                if child.type == "decorator":
                    decorator_text = self._get_node_text(child, source)
                    if "@dataclass" in decorator_text:
                        return "dataclass"
                    if "@attr.s" in decorator_text or "@attrs" in decorator_text or "@define" in decorator_text:
                        return "attrs"

        # Check base classes for BaseModel, BaseSettings, TypedDict
        for child in class_node.children:
            if child.type == "argument_list":
                bases_text = self._get_node_text(child, source)
                if "BaseModel" in bases_text or "BaseSettings" in bases_text:
                    return "pydantic"
                if "TypedDict" in bases_text:
                    return "typeddict"

        return None

    def _extract_python_config_fields(
        self,
        class_node: Any,
        class_name: str,
        source: bytes,
        file_path: str,
        config_type: str,
    ) -> list[ConfigField]:
        """Extract config fields from a Python config class."""
        import re

        fields: list[ConfigField] = []

        # Find the class body (block node)
        body_node = self._find_child(class_node, "block")
        if not body_node:
            return fields

        for child in body_node.children:
            # TreeSitter puts typed assignments directly in block (not in expression_statement)
            # Handle: field: Type = value OR field: Type
            if child.type == "assignment":
                # Find the identifier (field name)
                left = self._find_child(child, "identifier")
                if not left:
                    continue

                field_name = self._get_node_text(left, source)
                # Skip private/dunder fields
                if field_name.startswith("_"):
                    continue

                field_type = None
                default_value = None
                is_optional = False
                doc = None

                # Look for type annotation
                type_node = self._find_child(child, "type")
                if type_node:
                    field_type = self._get_node_text(type_node, source)
                    if "None" in field_type or "Optional" in field_type:
                        is_optional = True

                # Look for default value (last child that's not identifier, type, or punctuation)
                for subchild in reversed(child.children):
                    if subchild.type not in ("identifier", "type", ":", "="):
                        default_value = self._get_node_text(subchild, source)
                        # Extract description from Field(description=...)
                        if "Field(" in default_value and "description=" in default_value:
                            match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', default_value)
                            if match:
                                doc = match.group(1)
                        break

                fields.append(ConfigField(
                    name=field_name,
                    parent_symbol=class_name,
                    field_type=field_type,
                    default_value=default_value,
                    file=file_path,
                    line=child.start_point[0] + 1,
                    column=child.start_point[1],
                    is_optional=is_optional,
                    doc=doc,
                ))

            # Handle typed declarations without assignment: field: Type
            # These appear as expression_statement containing just the annotation
            elif child.type == "expression_statement":
                expr = child.children[0] if child.children else None
                if expr and expr.type == "assignment":
                    # This is a plain assignment without type annotation
                    continue
                # Check if this is a type annotation without value
                text = self._get_node_text(child, source)
                if ":" in text and "=" not in text:
                    parts = text.split(":", 1)
                    if len(parts) == 2:
                        field_name = parts[0].strip()
                        field_type = parts[1].strip()
                        if not field_name.startswith("_"):
                            is_optional = "None" in field_type or "Optional" in field_type
                            fields.append(ConfigField(
                                name=field_name,
                                parent_symbol=class_name,
                                field_type=field_type,
                                default_value=None,
                                file=file_path,
                                line=child.start_point[0] + 1,
                                column=child.start_point[1],
                                is_optional=is_optional,
                            ))

        return fields

    def _is_go_config_struct(self, struct_node: Any, source: bytes, struct_name: str) -> bool:
        """Detect if struct has yaml/json field tags or config naming pattern."""
        # Check naming pattern
        if any(struct_name.endswith(suffix) for suffix in ("Config", "Settings", "Options")):
            return True

        # Check if any field has yaml/json tags
        field_list = self._find_child(struct_node, "field_declaration_list")
        if field_list:
            for field in self._find_nodes(field_list, "field_declaration"):
                tag_node = self._find_child(field, "raw_string_literal")
                if tag_node:
                    tag_text = self._get_node_text(tag_node, source)
                    if "yaml:" in tag_text or "json:" in tag_text:
                        return True

        return False

    def _extract_go_config_fields(
        self,
        struct_node: Any,
        struct_name: str,
        source: bytes,
        file_path: str,
    ) -> list[ConfigField]:
        """Extract config fields from a Go struct with yaml/json tags."""
        fields: list[ConfigField] = []

        field_list = self._find_child(struct_node, "field_declaration_list")
        if not field_list:
            return fields

        for field_node in self._find_nodes(field_list, "field_declaration"):
            # Get field name
            name_node = self._find_child(field_node, "field_identifier")
            if not name_node:
                continue

            field_name = self._get_node_text(name_node, source)

            # Get field type
            field_type = None
            for child in field_node.children:
                if child.type in ("type_identifier", "pointer_type", "slice_type", "map_type", "qualified_type"):
                    field_type = self._get_node_text(child, source)
                    break

            # Parse tags
            tags: dict[str, str] = {}
            tag_node = self._find_child(field_node, "raw_string_literal")
            if tag_node:
                tag_text = self._get_node_text(tag_node, source).strip("`")
                # Parse yaml:"name,omitempty" json:"name"
                import re
                for match in re.finditer(r'(\w+):"([^"]*)"', tag_text):
                    tags[match.group(1)] = match.group(2)

            is_optional = False
            if tags.get("yaml", "").endswith(",omitempty") or tags.get("json", "").endswith(",omitempty"):
                is_optional = True

            fields.append(ConfigField(
                name=field_name,
                parent_symbol=struct_name,
                field_type=field_type,
                default_value=None,
                file=file_path,
                line=field_node.start_point[0] + 1,
                column=field_node.start_point[1],
                tags=tags if tags else None,
                is_optional=is_optional,
            ))

        return fields

    def _is_ts_config_interface(self, interface_node: Any, source: bytes, interface_name: str) -> bool:
        """Detect if interface is config-like by name pattern."""
        config_suffixes = ("Config", "Options", "Settings", "Props")
        return any(interface_name.endswith(suffix) for suffix in config_suffixes)

    def _extract_ts_config_fields(
        self,
        interface_node: Any,
        interface_name: str,
        source: bytes,
        file_path: str,
    ) -> list[ConfigField]:
        """Extract properties from TypeScript interface."""
        fields: list[ConfigField] = []

        # Find the object type body
        body_node = self._find_child(interface_node, "object_type") or self._find_child(interface_node, "interface_body")
        if not body_node:
            return fields

        for child in body_node.children:
            if child.type == "property_signature":
                # Get property name
                name_node = self._find_child(child, "property_identifier")
                if not name_node:
                    continue

                field_name = self._get_node_text(name_node, source)

                # Check for optional marker (?)
                is_optional = False
                full_text = self._get_node_text(child, source)
                if "?" in full_text.split(":")[0]:
                    is_optional = True

                # Get type annotation
                field_type = None
                type_node = self._find_child(child, "type_annotation")
                if type_node:
                    field_type = self._get_node_text(type_node, source).lstrip(":").strip()

                fields.append(ConfigField(
                    name=field_name,
                    parent_symbol=interface_name,
                    field_type=field_type,
                    default_value=None,
                    file=file_path,
                    line=child.start_point[0] + 1,
                    column=child.start_point[1],
                    is_optional=is_optional,
                ))

        return fields

    def _is_rust_config_struct(self, struct_node: Any, source: bytes) -> bool:
        """Detect if struct has serde derives or serde attributes."""
        # Look for attributes before the struct
        # TreeSitter puts attributes as siblings before the struct_item
        parent = struct_node.parent
        if not parent:
            return False

        # Find attribute nodes that precede this struct
        struct_index = -1
        for i, child in enumerate(parent.children):
            if child == struct_node:
                struct_index = i
                break

        # Check preceding attribute items
        for i in range(struct_index - 1, -1, -1):
            child = parent.children[i]
            if child.type != "attribute_item":
                break
            attr_text = self._get_node_text(child, source)
            # Check for serde derives
            if "#[derive(" in attr_text:
                if "Serialize" in attr_text or "Deserialize" in attr_text:
                    return True
                if "serde::" in attr_text:
                    return True
            # Check for #[serde(...)]
            if "#[serde(" in attr_text:
                return True

        return False

    def _extract_rust_config_fields(
        self,
        struct_node: Any,
        struct_name: str,
        source: bytes,
        file_path: str,
    ) -> list[ConfigField]:
        """Extract fields from Rust struct with serde attributes."""
        fields: list[ConfigField] = []

        # Find field declaration list
        field_list = self._find_child(struct_node, "field_declaration_list")
        if not field_list:
            return fields

        for field_node in self._find_nodes(field_list, "field_declaration"):
            # Get field name
            name_node = self._find_child(field_node, "field_identifier")
            if not name_node:
                continue

            field_name = self._get_node_text(name_node, source)

            # Get field type
            field_type = None
            type_node = self._find_child(field_node, "type_identifier")
            if not type_node:
                # Try generic type
                type_node = self._find_child(field_node, "generic_type")
            if type_node:
                field_type = self._get_node_text(type_node, source)

            # Check for Option<T> to determine optionality
            is_optional = False
            if field_type and field_type.startswith("Option<"):
                is_optional = True

            # Parse serde attributes on the field
            tags: dict[str, str] = {}
            # Look for attribute items before this field
            parent = field_node.parent
            if parent:
                field_index = -1
                for i, child in enumerate(parent.children):
                    if child == field_node:
                        field_index = i
                        break

                for i in range(field_index - 1, -1, -1):
                    child = parent.children[i]
                    if child.type != "attribute_item":
                        break
                    attr_text = self._get_node_text(child, source)
                    if "#[serde(" in attr_text:
                        # Parse serde attributes
                        import re
                        # Handle rename = "name"
                        match = re.search(r'rename\s*=\s*"([^"]+)"', attr_text)
                        if match:
                            tags["serde_rename"] = match.group(1)
                        # Handle default
                        if "default" in attr_text:
                            tags["serde_default"] = "true"
                        # Handle skip_serializing_if
                        match = re.search(r'skip_serializing_if\s*=\s*"([^"]+)"', attr_text)
                        if match:
                            tags["serde_skip_if"] = match.group(1)

            fields.append(ConfigField(
                name=field_name,
                parent_symbol=struct_name,
                field_type=field_type,
                default_value=None,
                file=file_path,
                line=field_node.start_point[0] + 1,
                column=field_node.start_point[1],
                tags=tags if tags else None,
                is_optional=is_optional,
            ))

        return fields

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

    def _find_direct_methods(self, class_node: Any, func_type: str = "function_definition") -> list[Any]:
        """Find function definitions that are direct methods of this class.

        This method finds functions that belong to the class but stops recursion
        at nested class boundaries. This prevents methods of nested classes from
        being attributed to the outer class.

        Args:
            class_node: The class AST node to search
            func_type: Node type to search for (default: "function_definition")

        Returns:
            List of function nodes that are direct methods of this class
        """
        methods = []

        def traverse(n, inside_nested_class=False):
            # If we encounter a nested class definition, mark that we're inside it
            if n != class_node and n.type == "class_definition":
                inside_nested_class = True

            # Only collect functions that are NOT inside nested classes
            if n.type == func_type and not inside_nested_class:
                methods.append(n)

            # Continue traversal, passing the nested class flag
            for child in n.children:
                traverse(child, inside_nested_class)

        # Start traversal from class body
        traverse(class_node)
        return methods

    def _find_child(self, node: Any, child_type: str) -> Any | None:
        """Find first direct child of a specific type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def _get_node_text(self, node: Any, source: bytes) -> str:
        """Get the source text for a node.

        Args:
            node: Tree-sitter AST node with byte offset positions
            source: Source code as bytes (required for correct byte offset slicing)

        Returns:
            Decoded UTF-8 string of the node's text

        Note:
            Tree-sitter returns byte offsets, not character indices.
            Must use bytes for slicing, then decode to string.
        """
        return source[node.start_byte : node.end_byte].decode("utf8")

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
