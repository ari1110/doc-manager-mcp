"""Semantic change detection for code symbols.

This module provides data structures for representing semantic changes detected
in code symbols between versions. It focuses on API-level changes like function
signatures, class definitions, and method modifications rather than
implementation details.

Semantic changes are categorized by:
- Change type: added, removed, modified, signature_changed
- Symbol type: function, class, method, variable, etc.
- Severity: breaking, non-breaking, unknown

This information can be used for:
- Generating changelogs
- Detecting breaking API changes
- Tracking code evolution
- Documentation updates
"""

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .tree_sitter import Symbol, SymbolType


@dataclass
class SemanticChange:
    """Represents a semantic change detected in code symbols.

    A semantic change captures modifications to the public API or structure
    of code symbols, focusing on changes that affect how the code is used
    rather than internal implementation details.

    Attributes:
        name: The fully qualified name of the symbol (e.g., 'MyClass.my_method')
        change_type: Type of change - "added", "removed", "modified", or "signature_changed"
        symbol_type: Kind of symbol - "function", "class", "method", "variable", "constant", etc.
        file: File path relative to project root where the symbol is located
        line: Line number in the new version where the symbol is defined (None if removed)
        old_signature: Previous signature or definition (None if newly added)
        new_signature: New signature or definition (None if removed)
        severity: Impact assessment - "breaking" (incompatible), "non-breaking" (compatible),
                 or "unknown" (requires manual review)
    """

    name: str
    change_type: str
    symbol_type: str
    file: str
    line: int | None
    old_signature: str | None
    new_signature: str | None
    severity: str


def load_symbol_baseline(baseline_path: Path) -> dict[str, list[Symbol]] | None:
    """Load symbol baseline from JSON file.

    Args:
        baseline_path: Path to the baseline JSON file
                      (typically .doc-manager/memory/symbol-baseline.json)

    Returns:
        Dictionary mapping file paths to lists of Symbol objects,
        or None if the file doesn't exist or cannot be parsed.

    Error Handling:
        - Returns None if file doesn't exist (expected on first run)
        - Returns None if JSON is malformed (logs warning internally)
        - Returns None if required fields are missing
        - Skips invalid symbol entries (continues parsing remaining symbols)
    """
    if not baseline_path.exists():
        return None

    try:
        with open(baseline_path, encoding="utf-8") as f:
            data = json.load(f)

        # Validate basic structure
        if not isinstance(data, dict) or "symbols" not in data:
            return None

        # Convert JSON dicts back to Symbol objects
        result: dict[str, list[Symbol]] = {}
        for file_path, symbol_dicts in data["symbols"].items():
            symbols = []
            for sym_dict in symbol_dicts:
                try:
                    # Convert type string back to SymbolType enum
                    symbol = Symbol(
                        name=sym_dict["name"],
                        type=SymbolType(sym_dict["type"]),
                        file=sym_dict["file"],
                        line=sym_dict["line"],
                        column=sym_dict.get("column", 0),
                        signature=sym_dict.get("signature"),
                        parent=sym_dict.get("parent"),
                        doc=sym_dict.get("doc"),
                    )
                    symbols.append(symbol)
                except (KeyError, ValueError, TypeError):
                    # Skip invalid symbol entries, continue with remaining
                    continue

            if symbols:
                result[file_path] = symbols

        return result

    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        # JSON parsing error, file read error, or encoding error
        return None


def save_symbol_baseline(
    baseline_path: Path, symbols: dict[str, list[Symbol]]
) -> None:
    """Save symbol baseline to JSON file with atomic write.

    Args:
        baseline_path: Path to the baseline JSON file
                      (typically .doc-manager/memory/symbol-baseline.json)
        symbols: Dictionary mapping file paths to lists of Symbol objects

    Raises:
        OSError: If file cannot be written (permissions, disk space, etc.)
        ValueError: If symbols dictionary is invalid

    Implementation:
        - Uses atomic write pattern (temp file + rename)
        - Creates parent directory if it doesn't exist
        - Preserves created_at timestamp if baseline exists
        - Updates updated_at timestamp on every save
    """
    if not isinstance(symbols, dict):
        raise ValueError("symbols must be a dictionary")

    # Ensure parent directory exists
    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing baseline to preserve created_at timestamp
    created_at = None
    if baseline_path.exists():
        try:
            with open(baseline_path, encoding="utf-8") as f:
                existing = json.load(f)
                created_at = existing.get("created_at")
        except (json.JSONDecodeError, OSError):
            pass

    # If no existing timestamp, use current time
    now = datetime.now(timezone.utc).isoformat()
    if created_at is None:
        created_at = now

    # Convert Symbol objects to JSON-serializable dicts
    symbols_dict = {}
    for file_path, symbol_list in symbols.items():
        symbols_dict[file_path] = [
            {
                "name": sym.name,
                "type": sym.type.value,
                "file": sym.file,
                "line": sym.line,
                "column": sym.column,
                "signature": sym.signature,
                "parent": sym.parent,
                "doc": sym.doc,
            }
            for sym in symbol_list
        ]

    # Build JSON structure with metadata
    baseline_data = {
        "version": "1.0",
        "created_at": created_at,
        "updated_at": now,
        "project_root": str(baseline_path.parent.parent.parent.absolute()),
        "symbols": symbols_dict,
    }

    # Atomic write: write to temp file, then rename
    # This prevents corruption if write fails mid-operation
    temp_fd, temp_path = tempfile.mkstemp(
        dir=baseline_path.parent, suffix=".tmp", prefix=".symbol-baseline-"
    )

    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(baseline_data, f, indent=2, ensure_ascii=False)
            f.flush()

        # Atomic rename (overwrites existing file on POSIX, may not be atomic on Windows)
        Path(temp_path).replace(baseline_path)

    except Exception:
        # Clean up temp file on any error
        try:
            Path(temp_path).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def compare_symbols(
    old_symbols: dict[str, list[Symbol]],
    new_symbols: dict[str, list[Symbol]]
) -> list[SemanticChange]:
    """Compare two symbol indexes and detect changes.

    Analyzes differences between two symbol baselines to identify:
    - Added symbols (in new but not in old)
    - Removed symbols (in old but not in new)
    - Modified symbols (signature changes)
    - Implementation changes (same signature, different location/parent/doc)

    Args:
        old_symbols: Previous baseline (file path -> list of Symbol objects)
        new_symbols: Current codebase symbols (file path -> list of Symbol objects)

    Returns:
        List of SemanticChange objects representing detected changes,
        sorted by severity (breaking changes first) and then by file path

    Change Detection Logic:
        1. Added: Symbol exists in new but not in old baseline
           - Severity: non-breaking (backward compatible)

        2. Removed: Symbol exists in old but not in new baseline
           - Severity: breaking (existing code may reference it)

        3. Signature Changed: Symbol exists in both, but signature differs
           - Severity: breaking if public API, non-breaking if private
           - Public determined by naming convention (no leading underscore in Python,
             uppercase first letter in Go)

        4. Modified: Symbol exists in both with same signature but different
                    location, parent, or documentation
           - Severity: non-breaking (implementation detail change)

    Example:
        >>> old = {"file.py": [Symbol(name="foo", type=SymbolType.FUNCTION, ...)]}
        >>> new = {"file.py": [Symbol(name="bar", type=SymbolType.FUNCTION, ...)]}
        >>> changes = compare_symbols(old, new)
        >>> changes[0].change_type  # "removed"
        >>> changes[1].change_type  # "added"
    """
    changes: list[SemanticChange] = []

    # Build symbol lookup tables for efficient comparison
    # Key: (symbol_name, file_path) -> Symbol
    old_lookup: dict[tuple[str, str], Symbol] = {}
    new_lookup: dict[tuple[str, str], Symbol] = {}

    for file_path, symbol_list in old_symbols.items():
        for sym in symbol_list:
            old_lookup[(sym.name, file_path)] = sym

    for file_path, symbol_list in new_symbols.items():
        for sym in symbol_list:
            new_lookup[(sym.name, file_path)] = sym

    # Detect added and modified symbols
    for (name, file_path), new_sym in new_lookup.items():
        if (name, file_path) not in old_lookup:
            # Symbol added
            changes.append(SemanticChange(
                name=name,
                change_type="added",
                symbol_type=new_sym.type.value,
                file=file_path,
                line=new_sym.line,
                old_signature=None,
                new_signature=new_sym.signature,
                severity="non-breaking"
            ))
        else:
            # Symbol exists in both - check for modifications
            old_sym = old_lookup[(name, file_path)]

            # Check if signature changed
            if old_sym.signature != new_sym.signature:
                # Determine severity based on public/private API
                is_public = _is_public_api(new_sym)
                severity = "breaking" if is_public else "non-breaking"

                changes.append(SemanticChange(
                    name=name,
                    change_type="signature_changed",
                    symbol_type=new_sym.type.value,
                    file=file_path,
                    line=new_sym.line,
                    old_signature=old_sym.signature,
                    new_signature=new_sym.signature,
                    severity=severity
                ))
            # Check for implementation changes (line, parent, doc)
            elif (old_sym.line != new_sym.line or
                  old_sym.parent != new_sym.parent or
                  old_sym.doc != new_sym.doc):
                changes.append(SemanticChange(
                    name=name,
                    change_type="modified",
                    symbol_type=new_sym.type.value,
                    file=file_path,
                    line=new_sym.line,
                    old_signature=old_sym.signature,
                    new_signature=new_sym.signature,
                    severity="non-breaking"
                ))

    # Detect removed symbols
    for (name, file_path), old_sym in old_lookup.items():
        if (name, file_path) not in new_lookup:
            # Symbol removed
            changes.append(SemanticChange(
                name=name,
                change_type="removed",
                symbol_type=old_sym.type.value,
                file=file_path,
                line=None,  # No line in new version (removed)
                old_signature=old_sym.signature,
                new_signature=None,
                severity="breaking"
            ))

    # Sort changes: breaking first, then by file path, then by line
    changes.sort(key=lambda c: (
        0 if c.severity == "breaking" else 1,
        c.file,
        c.line if c.line is not None else 0
    ))

    return changes


def _is_public_api(symbol: Symbol) -> bool:
    """Determine if a symbol is part of the public API.

    Uses language-specific naming conventions to determine visibility:
    - Python: Public if name doesn't start with underscore
    - Go: Public if name starts with uppercase letter
    - JavaScript/TypeScript: Assume public (no clear convention)

    Args:
        symbol: Symbol to check

    Returns:
        True if symbol is considered public API, False if private
    """
    if not symbol.name:
        return False

    # Python convention: underscore prefix means private
    if symbol.file.endswith('.py'):
        return not symbol.name.startswith('_')

    # Go convention: uppercase first letter means public
    if symbol.file.endswith('.go'):
        return symbol.name[0].isupper() if symbol.name else False

    # JavaScript/TypeScript: no clear convention, assume public
    if symbol.file.endswith(('.js', '.ts', '.jsx', '.tsx')):
        return True

    # Default: assume public
    return True
