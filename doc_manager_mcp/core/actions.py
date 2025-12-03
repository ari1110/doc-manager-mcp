"""Action item generation for AI agents.

This module provides data structures and logic for generating actionable
documentation tasks from detected code changes. It enables AI agents to
act directly on change detection output without manual interpretation.
"""

from dataclasses import asdict, dataclass
from typing import Any, ClassVar

from doc_manager_mcp.indexing.analysis.semantic_diff import (
    ConfigFieldChange,
    SemanticChange,
)


@dataclass
class ActionItem:
    """Represents a specific action for an AI agent to take.

    Action items provide precise, actionable instructions for updating
    documentation based on detected code changes.

    Attributes:
        action_type: Type of documentation action to take
            - "add_section": Add new documentation section
            - "update_section": Update existing section
            - "remove_section": Remove deprecated section
            - "add_field_doc": Document new config field
            - "update_example": Update code example
        target_file: Path to documentation file to modify
        target_section: Section/heading within the target file (optional)
        description: Human-readable description of the action
        priority: Urgency of the action
            - "critical": Breaking change, must fix immediately
            - "high": Important change, fix soon
            - "medium": Moderate impact, schedule fix
            - "low": Minor change, fix when convenient
        source_change: Dictionary with details of the triggering change
        suggested_content: Optional suggested content to add/update
    """

    action_type: str
    target_file: str
    target_section: str | None
    description: str
    priority: str
    source_change: dict[str, Any]
    suggested_content: str | None = None


class ActionGenerator:
    """Generates actionable items from detected changes.

    Maps semantic and config field changes to specific documentation actions
    with appropriate priorities based on change severity.

    Priority Rules:
        - critical: Symbol removed, config field removed
        - high: Signature changed (breaking), config field added
        - medium: Symbol added, default changed, implementation modified
        - low: Non-breaking type changes, doc-only changes
    """

    # Action mapping based on change type and severity
    SEMANTIC_ACTION_MAP: ClassVar[dict[tuple[str, str], tuple[str, str]]] = {
        ("added", "function"): ("add_section", "medium"),
        ("added", "method"): ("add_section", "medium"),
        ("added", "class"): ("add_section", "medium"),
        ("added", "struct"): ("add_section", "medium"),
        ("added", "interface"): ("add_section", "medium"),
        ("removed", "function"): ("remove_section", "critical"),
        ("removed", "method"): ("remove_section", "critical"),
        ("removed", "class"): ("remove_section", "critical"),
        ("removed", "struct"): ("remove_section", "critical"),
        ("removed", "interface"): ("remove_section", "critical"),
        ("signature_changed", "function"): ("update_section", "high"),
        ("signature_changed", "method"): ("update_section", "high"),
        ("modified", "function"): ("update_section", "low"),
        ("modified", "method"): ("update_section", "low"),
        ("modified", "class"): ("update_section", "low"),
    }

    CONFIG_ACTION_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "added": ("add_field_doc", "high"),
        "removed": ("remove_section", "critical"),
        "type_changed": ("update_field_doc", "high"),
        "default_changed": ("update_example", "medium"),
    }

    def __init__(self, docs_path: str = "docs"):
        """Initialize ActionGenerator.

        Args:
            docs_path: Base path for documentation files
        """
        self.docs_path = docs_path

    def generate_actions(
        self,
        semantic_changes: list[SemanticChange],
        config_changes: list[ConfigFieldChange],
        affected_docs: list[dict[str, Any]] | None = None,
    ) -> list[ActionItem]:
        """Generate prioritized action items from changes.

        Args:
            semantic_changes: List of semantic symbol changes
            config_changes: List of config field changes
            affected_docs: Optional list of affected documentation mappings

        Returns:
            List of ActionItem objects sorted by priority (critical first)
        """
        actions: list[ActionItem] = []

        # Generate actions from semantic changes
        for change in semantic_changes:
            action = self._action_from_semantic_change(change, affected_docs)
            if action:
                actions.append(action)

        # Generate actions from config field changes
        for change in config_changes:
            action = self._action_from_config_change(change, affected_docs)
            if action:
                actions.append(action)

        # Sort by priority: critical > high > medium > low
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        actions.sort(key=lambda a: (
            priority_order.get(a.priority, 99),
            a.target_file,
            a.target_section or "",
        ))

        return actions

    def _action_from_semantic_change(
        self,
        change: SemanticChange,
        affected_docs: list[dict[str, Any]] | None,
    ) -> ActionItem | None:
        """Create an action item from a semantic change."""
        key = (change.change_type, change.symbol_type)
        mapping = self.SEMANTIC_ACTION_MAP.get(key)

        if not mapping:
            # Default for unmapped changes
            action_type = "update_section"
            priority = "medium" if change.severity == "breaking" else "low"
        else:
            action_type, priority = mapping

        # Elevate priority for breaking changes
        if change.severity == "breaking" and priority not in ("critical",):
            priority = "high"

        # Determine target file
        target_file = self._infer_target_doc(change.file, change.name, affected_docs)

        # Build description
        if change.change_type == "added":
            description = f"Document new {change.symbol_type} '{change.name}'"
        elif change.change_type == "removed":
            description = f"Remove documentation for deleted {change.symbol_type} '{change.name}'"
        elif change.change_type == "signature_changed":
            description = f"Update signature documentation for {change.symbol_type} '{change.name}'"
        else:
            description = f"Update documentation for modified {change.symbol_type} '{change.name}'"

        # Build suggested content for additions
        suggested_content = None
        if change.change_type == "added" and change.new_signature:
            suggested_content = f"```\n{change.new_signature}\n```"

        return ActionItem(
            action_type=action_type,
            target_file=target_file,
            target_section=change.name,
            description=description,
            priority=priority,
            source_change={
                "type": "semantic",
                "name": change.name,
                "change_type": change.change_type,
                "symbol_type": change.symbol_type,
                "file": change.file,
                "line": change.line,
                "old_signature": change.old_signature,
                "new_signature": change.new_signature,
                "severity": change.severity,
            },
            suggested_content=suggested_content,
        )

    def _action_from_config_change(
        self,
        change: ConfigFieldChange,
        affected_docs: list[dict[str, Any]] | None,
    ) -> ActionItem | None:
        """Create an action item from a config field change."""
        mapping = self.CONFIG_ACTION_MAP.get(change.change_type)

        if not mapping:
            action_type = "update_field_doc"
            priority = "medium"
        else:
            action_type, priority = mapping

        # Elevate priority for breaking changes
        if change.severity == "breaking" and priority not in ("critical",):
            priority = "high"

        # Determine target file (config docs)
        target_file = self._infer_config_doc(change.parent_symbol, affected_docs)

        # Build description
        if change.change_type == "added":
            description = f"Document new config field '{change.field_name}' in {change.parent_symbol}"
        elif change.change_type == "removed":
            description = f"Remove documentation for deleted field '{change.field_name}' from {change.parent_symbol}"
        elif change.change_type == "type_changed":
            description = f"Update type documentation for '{change.field_name}' in {change.parent_symbol}: {change.old_type} -> {change.new_type}"
        elif change.change_type == "default_changed":
            description = f"Update default value example for '{change.field_name}' in {change.parent_symbol}"
        else:
            description = f"Update documentation for config field '{change.field_name}' in {change.parent_symbol}"

        # Build suggested content
        suggested_content = None
        if change.change_type == "added" and change.new_type:
            suggested_content = f"- `{change.field_name}`: {change.new_type}"
            if change.new_default:
                suggested_content += f" (default: `{change.new_default}`)"

        return ActionItem(
            action_type=action_type,
            target_file=target_file,
            target_section=change.parent_symbol,
            description=description,
            priority=priority,
            source_change={
                "type": "config_field",
                "field_name": change.field_name,
                "parent_symbol": change.parent_symbol,
                "change_type": change.change_type,
                "file": change.file,
                "line": change.line,
                "old_type": change.old_type,
                "new_type": change.new_type,
                "old_default": change.old_default,
                "new_default": change.new_default,
                "severity": change.severity,
                "documentation_action": change.documentation_action,
            },
            suggested_content=suggested_content,
        )

    def _infer_target_doc(
        self,
        source_file: str,
        symbol_name: str,
        affected_docs: list[dict[str, Any]] | None,
    ) -> str:
        """Infer target documentation file from source file and symbol.

        Uses affected_docs mapping if available, otherwise uses conventions.
        """
        # Check affected_docs for explicit mapping
        if affected_docs:
            for mapping in affected_docs:
                if mapping.get("source_file") == source_file:
                    return mapping.get("doc_file", f"{self.docs_path}/api/{source_file}.md")

        # Convention-based inference
        # src/module.py -> docs/reference/module.md
        # cmd/tool/main.go -> docs/cli/tool.md
        if source_file.endswith(".py"):
            module = source_file.replace("/", ".").replace(".py", "")
            return f"{self.docs_path}/reference/{module.split('.')[-1]}.md"
        elif source_file.endswith(".go"):
            parts = source_file.split("/")
            if "cmd" in parts:
                return f"{self.docs_path}/cli/{parts[-2] if len(parts) > 1 else 'main'}.md"
            return f"{self.docs_path}/api/{parts[-1].replace('.go', '.md')}"
        elif source_file.endswith((".ts", ".tsx", ".js", ".jsx")):
            return f"{self.docs_path}/api/{source_file.split('/')[-1].split('.')[0]}.md"
        elif source_file.endswith(".rs"):
            return f"{self.docs_path}/api/{source_file.split('/')[-1].replace('.rs', '.md')}"

        return f"{self.docs_path}/api/{symbol_name.lower()}.md"

    def _infer_config_doc(
        self,
        parent_symbol: str,
        affected_docs: list[dict[str, Any]] | None,
    ) -> str:
        """Infer target documentation file for config models.

        Config models typically go in configuration reference docs.
        """
        # Check affected_docs for explicit mapping
        if affected_docs:
            for mapping in affected_docs:
                if mapping.get("symbol") == parent_symbol:
                    return mapping.get("doc_file", f"{self.docs_path}/reference/configuration.md")

        # Default to configuration reference
        return f"{self.docs_path}/reference/configuration.md"


def actions_to_dicts(actions: list[ActionItem]) -> list[dict[str, Any]]:
    """Convert action items to dictionaries for JSON serialization."""
    return [asdict(a) for a in actions]
