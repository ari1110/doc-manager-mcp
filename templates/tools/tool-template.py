"""Template for implementing new doc-manager tools.

Copy this file to src/tools/ and customize for your specific tool.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from ..models import YourToolInput  # Replace with actual model name
from ..constants import ResponseFormat
from ..utils import handle_error

async def your_tool_name(params: YourToolInput) -> str:
    """Brief one-line description of what this tool does.

    Detailed explanation of the tool's purpose and functionality.
    This tool performs [specific operation] on the project documentation.

    Args:
        params (YourToolInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - [other params]: Description of other parameters

    Returns:
        str: [Description of return format - JSON or Markdown]

    Examples:
        - Use when: [Specific scenario when this tool should be used]
        - Use when: [Another scenario]
        - Don't use when: [When NOT to use this tool]

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if [specific condition]
        - Validates all input parameters via Pydantic model
    """
    try:
        # 1. Validate project path
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return f"Error: Project path does not exist: {project_path}"

        if not project_path.is_dir():
            return f"Error: Project path is not a directory: {project_path}"

        # 2. Load any necessary configuration or memory
        # config = load_config(project_path)
        # memory = _load_memory(project_path)

        # 3. Perform the main tool logic
        result_data = await _perform_tool_operation(project_path, params)

        # 4. Format response based on requested format
        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result_data, indent=2)
        else:
            return _format_markdown_response(result_data)

    except Exception as e:
        return handle_error(e, "your_tool_name")


# Private helper functions

async def _perform_tool_operation(project_path: Path, params: YourToolInput) -> Dict[str, Any]:
    """Main logic for the tool.

    Args:
        project_path: Resolved project path
        params: Validated input parameters

    Returns:
        Dict containing operation results
    """
    # TODO: Implement main tool logic here

    result = {
        "success": True,
        "data": {},
        "message": "Operation completed successfully"
    }

    return result


def _format_markdown_response(data: Dict[str, Any]) -> str:
    """Format results as human-readable Markdown.

    Args:
        data: Result data from tool operation

    Returns:
        Formatted Markdown string
    """
    lines = ["# Tool Operation Results", ""]

    if data.get("success"):
        lines.append("✓ Operation completed successfully")
        lines.append("")

    # TODO: Add specific formatting for your tool's data

    lines.append("## Summary")
    lines.append(f"- Status: {'Success' if data.get('success') else 'Failed'}")
    lines.append(f"- Message: {data.get('message', 'N/A')}")

    return "\n".join(lines)


def _load_memory(project_path: Path) -> Optional[Dict[str, Any]]:
    """Load memory baseline from .doc-manager/ if needed.

    Args:
        project_path: Project root path

    Returns:
        Memory data or None if not found
    """
    memory_file = project_path / ".doc-manager" / "memory" / "repo-baseline.json"

    if not memory_file.exists():
        return None

    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


# Tool-specific helper functions
# Add any additional helper functions needed for your tool below
