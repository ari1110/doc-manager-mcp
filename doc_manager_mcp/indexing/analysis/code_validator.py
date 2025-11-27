"""Code syntax validator using TreeSitter parsers.

This module provides the CodeValidator class for validating code syntax
in multiple programming languages using TreeSitter parsers.
"""

from __future__ import annotations

from typing import Any

from .tree_sitter import SymbolIndexer


class CodeValidator:
    """Validate code syntax using TreeSitter parsers.

    Uses the SymbolIndexer's TreeSitter parsers to validate code snippets
    and detect syntax errors with precise line and column information.

    Supported languages:
    - Python
    - Go
    - JavaScript
    - TypeScript
    - Any other language supported by SymbolIndexer
    """

    def __init__(self):
        """Initialize the code validator with TreeSitter parsers."""
        self.indexer = SymbolIndexer()

    def validate_syntax(self, language: str, code: str) -> dict[str, Any]:
        """Validate code syntax and return errors with locations.

        Args:
            language: Programming language (e.g., "python", "go", "javascript")
            code: Code content to validate

        Returns:
            Dict with keys:
            - valid: bool - Whether code is syntactically valid
            - errors: list[dict] - List of syntax errors with locations
            - warning: str | None - Warning if language not supported

        Example:
            >>> validator = CodeValidator()
            >>> result = validator.validate_syntax("python", "print('hello')")
            >>> result
            {'valid': True, 'errors': []}

            >>> result = validator.validate_syntax("python", "print('hello'")
            >>> result
            {'valid': False, 'errors': [{'type': 'syntax_error', 'line': 1, ...}]}
        """
        # Check if language is supported
        if language not in self.indexer.parsers:
            return {
                "valid": True,
                "errors": [],
                "warning": f"Language '{language}' not supported for validation"
            }

        # Parse code with TreeSitter
        source_bytes = code.encode("utf8")
        tree = self.indexer.parsers[language].parse(source_bytes)

        # Check for syntax errors
        if tree.root_node.has_error:
            errors = self._find_error_nodes(tree.root_node, source_bytes)
            return {
                "valid": False,
                "errors": errors,
                "warning": None
            }

        return {
            "valid": True,
            "errors": [],
            "warning": None
        }

    def _find_error_nodes(self, node: Any, source: bytes) -> list[dict[str, Any]]:
        """Recursively find all ERROR nodes in the syntax tree.

        Args:
            node: TreeSitter node to search with byte offset positions
            source: Original source code as bytes (required for correct byte offset slicing)

        Returns:
            List of error dicts with keys: type, line, column, text, message

        Note:
            Tree-sitter returns byte offsets, not character indices.
            Must use bytes for slicing, then decode to string.
        """
        errors = []

        # Check if this node is an error
        if node.type == "ERROR" or node.is_missing:
            # Extract error context using byte offsets
            try:
                error_text = source[node.start_byte:node.end_byte].decode("utf8")
            except (UnicodeDecodeError, IndexError):
                error_text = ""

            # Build error message
            if node.is_missing:
                message = f"Missing {node.type}"
            else:
                message = "Syntax error"

            errors.append({
                "type": "syntax_error",
                "line": node.start_point[0] + 1,  # 0-indexed to 1-indexed
                "column": node.start_point[1] + 1,
                "text": error_text[:50],  # Limit context length
                "message": message
            })

        # Recursively check children
        for child in node.children:
            errors.extend(self._find_error_nodes(child, source))

        return errors

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages for validation.

        Returns:
            List of language names that can be validated
        """
        return list(self.indexer.parsers.keys())
