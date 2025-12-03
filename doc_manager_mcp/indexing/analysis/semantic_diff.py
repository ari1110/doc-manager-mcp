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

from doc_manager_mcp.core.security import file_lock

from .tree_sitter import ConfigField, Symbol, SymbolType


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


@dataclass
class ConfigFieldChange:
    """Represents a change detected in a config field.

    Used to track field-level changes in configuration models for
    precise documentation updates by AI agents.

    Attributes:
        field_name: Name of the config field
        parent_symbol: Name of the parent class/struct
        change_type: Type of change - "added", "removed", "type_changed", "default_changed"
        file: File path relative to project root
        line: Line number of the field (None if removed)
        old_type: Previous type annotation (None if newly added)
        new_type: New type annotation (None if removed)
        old_default: Previous default value (None if newly added)
        new_default: New default value (None if removed)
        severity: Impact - "breaking" (removed/type incompatible) or "non-breaking"
        documentation_action: Suggested doc action (e.g., "add_field_doc", "update_field_doc")
    """

    field_name: str
    parent_symbol: str
    change_type: str  # added, removed, type_changed, default_changed
    file: str
    line: int | None
    old_type: str | None
    new_type: str | None
    old_default: str | None
    new_default: str | None
    severity: str  # breaking, non-breaking
    documentation_action: str


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
                    # Convert config_fields if present (v1.1+)
                    config_fields = None
                    if sym_dict.get("config_fields"):
                        config_fields = []
                        for cf_dict in sym_dict["config_fields"]:
                            config_fields.append(ConfigField(
                                name=cf_dict["name"],
                                parent_symbol=cf_dict["parent_symbol"],
                                field_type=cf_dict.get("field_type"),
                                default_value=cf_dict.get("default_value"),
                                file=cf_dict["file"],
                                line=cf_dict["line"],
                                column=cf_dict.get("column", 0),
                                tags=cf_dict.get("tags"),
                                is_optional=cf_dict.get("is_optional", False),
                                doc=cf_dict.get("doc"),
                            ))

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
                        config_fields=config_fields,
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
        serialized_symbols = []
        for sym in symbol_list:
            sym_dict = {
                "name": sym.name,
                "type": sym.type.value,
                "file": sym.file,
                "line": sym.line,
                "column": sym.column,
                "signature": sym.signature,
                "parent": sym.parent,
                "doc": sym.doc,
            }
            # Serialize config_fields if present (v1.1 feature)
            if sym.config_fields:
                sym_dict["config_fields"] = [
                    {
                        "name": cf.name,
                        "parent_symbol": cf.parent_symbol,
                        "field_type": cf.field_type,
                        "default_value": cf.default_value,
                        "file": cf.file,
                        "line": cf.line,
                        "column": cf.column,
                        "tags": cf.tags,
                        "is_optional": cf.is_optional,
                        "doc": cf.doc,
                    }
                    for cf in sym.config_fields
                ]
            serialized_symbols.append(sym_dict)
        symbols_dict[file_path] = serialized_symbols

    # Build JSON structure with metadata
    baseline_data = {
        "version": "1.1",  # Bumped for config_fields support
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

        # Atomic rename with file locking to prevent concurrent write corruption
        # (overwrites existing file on POSIX, may not be atomic on Windows)
        with file_lock(baseline_path, timeout=10, retries=3):
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


def compare_config_fields(
    old_symbols: dict[str, list[Symbol]],
    new_symbols: dict[str, list[Symbol]]
) -> list[ConfigFieldChange]:
    """Compare config fields between two symbol baselines.

    Analyzes differences in config model fields to identify:
    - Added fields (non-breaking)
    - Removed fields (breaking)
    - Type changes (breaking if incompatible)
    - Default value changes (non-breaking)
    - Optional → Required changes (breaking)

    Args:
        old_symbols: Previous baseline (file path -> list of Symbol objects)
        new_symbols: Current codebase symbols (file path -> list of Symbol objects)

    Returns:
        List of ConfigFieldChange objects sorted by severity (breaking first)

    Severity Rules:
        - Field added: non-breaking (new configs need it, old ones work)
        - Field removed: breaking (existing configs may use it)
        - Type changed (incompatible): breaking
        - Type changed (compatible widening): non-breaking
        - Default changed: non-breaking
        - Optional → Required: breaking
        - Required → Optional: non-breaking
    """
    changes: list[ConfigFieldChange] = []

    # Build lookup tables for config fields
    # Key: (parent_symbol, field_name, file_path) -> ConfigField
    old_fields: dict[tuple[str, str, str], ConfigField] = {}
    new_fields: dict[tuple[str, str, str], ConfigField] = {}

    for file_path, symbol_list in old_symbols.items():
        for sym in symbol_list:
            if sym.config_fields:
                for cf in sym.config_fields:
                    old_fields[(sym.name, cf.name, file_path)] = cf

    for file_path, symbol_list in new_symbols.items():
        for sym in symbol_list:
            if sym.config_fields:
                for cf in sym.config_fields:
                    new_fields[(sym.name, cf.name, file_path)] = cf

    # Detect added and modified fields
    for (parent, field_name, file_path), new_cf in new_fields.items():
        if (parent, field_name, file_path) not in old_fields:
            # Field added
            changes.append(ConfigFieldChange(
                field_name=field_name,
                parent_symbol=parent,
                change_type="added",
                file=file_path,
                line=new_cf.line,
                old_type=None,
                new_type=new_cf.field_type,
                old_default=None,
                new_default=new_cf.default_value,
                severity="non-breaking",
                documentation_action="add_field_doc",
            ))
        else:
            # Field exists in both - check for modifications
            old_cf = old_fields[(parent, field_name, file_path)]

            # Check type change
            if old_cf.field_type != new_cf.field_type:
                # Determine if type change is breaking
                severity = _is_type_change_breaking(old_cf.field_type, new_cf.field_type)
                changes.append(ConfigFieldChange(
                    field_name=field_name,
                    parent_symbol=parent,
                    change_type="type_changed",
                    file=file_path,
                    line=new_cf.line,
                    old_type=old_cf.field_type,
                    new_type=new_cf.field_type,
                    old_default=old_cf.default_value,
                    new_default=new_cf.default_value,
                    severity=severity,
                    documentation_action="update_field_doc",
                ))
            # Check default value change
            elif old_cf.default_value != new_cf.default_value:
                changes.append(ConfigFieldChange(
                    field_name=field_name,
                    parent_symbol=parent,
                    change_type="default_changed",
                    file=file_path,
                    line=new_cf.line,
                    old_type=old_cf.field_type,
                    new_type=new_cf.field_type,
                    old_default=old_cf.default_value,
                    new_default=new_cf.default_value,
                    severity="non-breaking",
                    documentation_action="update_field_doc",
                ))
            # Check optional → required change
            elif old_cf.is_optional and not new_cf.is_optional:
                changes.append(ConfigFieldChange(
                    field_name=field_name,
                    parent_symbol=parent,
                    change_type="type_changed",
                    file=file_path,
                    line=new_cf.line,
                    old_type=f"{old_cf.field_type} (optional)",
                    new_type=f"{new_cf.field_type} (required)",
                    old_default=old_cf.default_value,
                    new_default=new_cf.default_value,
                    severity="breaking",
                    documentation_action="update_field_doc",
                ))

    # Detect removed fields
    for (parent, field_name, file_path), old_cf in old_fields.items():
        if (parent, field_name, file_path) not in new_fields:
            # Field removed
            changes.append(ConfigFieldChange(
                field_name=field_name,
                parent_symbol=parent,
                change_type="removed",
                file=file_path,
                line=None,
                old_type=old_cf.field_type,
                new_type=None,
                old_default=old_cf.default_value,
                new_default=None,
                severity="breaking",
                documentation_action="remove_field_doc",
            ))

    # Sort changes: breaking first, then by file, then by parent, then by field
    changes.sort(key=lambda c: (
        0 if c.severity == "breaking" else 1,
        c.file,
        c.parent_symbol,
        c.field_name,
    ))

    return changes


def _is_type_change_breaking(old_type: str | None, new_type: str | None) -> str:
    """Determine if a type change is breaking or non-breaking.

    Type changes are generally considered breaking unless they are
    "widening" changes that accept more inputs.

    Args:
        old_type: Previous type annotation
        new_type: New type annotation

    Returns:
        "breaking" or "non-breaking"
    """
    if not old_type or not new_type:
        return "breaking"

    # Common widening patterns (non-breaking)
    # str -> str | None (accepting None is widening)
    # int -> int | str (accepting more types is widening)
    # Required -> Optional (accepting None is widening)

    # If new type includes old type and adds Optional/None, it's widening
    if "None" in new_type and "None" not in old_type:
        # Check if base type is same
        old_base = old_type.replace(" | None", "").replace("Optional[", "").rstrip("]")
        new_base = new_type.replace(" | None", "").replace("Optional[", "").rstrip("]")
        if old_base in new_base or new_base.startswith(old_base):
            return "non-breaking"

    # If types are identical, non-breaking
    if old_type == new_type:
        return "non-breaking"

    # Default: assume breaking for safety
    return "breaking"


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
