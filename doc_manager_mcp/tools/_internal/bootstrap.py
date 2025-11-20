"""Bootstrap workflow for creating fresh documentation from scratch.

This workflow orchestrates multiple tools to set up documentation for a project:
1. Detects/recommends documentation platform
2. Creates configuration file
3. Creates documentation directory structure
4. Generates initial documentation files
5. Initializes memory system
6. Runs initial quality assessment
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from doc_manager_mcp.constants import DocumentationPlatform
from doc_manager_mcp.core import detect_project_language, enforce_response_limit, handle_error
from doc_manager_mcp.models import BootstrapInput
from doc_manager_mcp.tools.analysis.platform import detect_platform
from doc_manager_mcp.tools.analysis.quality.assessment import assess_quality

from .config import initialize_config
from .memory import initialize_memory


async def bootstrap(params: BootstrapInput) -> str | dict[str, Any]:
    """Bootstrap fresh documentation for a project.

    INTERNAL USE ONLY: This function is not exposed as an MCP tool in v2.0.0.
    It is automatically called by docmgr_init(mode="bootstrap").

    Orchestrates multiple tools to set up documentation from scratch:
    1. Detects/recommends documentation platform
    2. Creates configuration file
    3. Creates documentation directory structure
    4. Generates initial documentation files
    5. Initializes memory system
    6. Runs initial quality assessment

    Args:
        params (BootstrapInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - platform (Optional[DocumentationPlatform]): Platform to use (auto-detected if not specified)
            - docs_path (str): Where to create docs (default: "docs")

    Returns:
        str: Bootstrap report with created files and next steps

    Examples:
        - Use when: Starting documentation for a new project
        - Use when: Setting up docs for existing project without documentation

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns error if docs_path already exists (won't overwrite)
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Check if docs already exist
        docs_path = project_path / params.docs_path
        if docs_path.exists():
            return enforce_response_limit(f"Error: Documentation directory already exists at {docs_path}. Use migrate workflow to restructure existing docs.")

        lines = ["# Documentation Bootstrap Report", ""]
        lines.append(f"**Project:** {project_path.name}")
        lines.append(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Step 1: Detect platform
        lines.append("## Step 1: Platform Detection")
        lines.append("")

        from ...models import DetectPlatformInput
        platform_result = await detect_platform(DetectPlatformInput(
            project_path=str(project_path)
        ))

        platform_data = platform_result if isinstance(platform_result, dict) else json.loads(platform_result)
        recommended_platform = params.platform or DocumentationPlatform(platform_data["recommendation"])

        lines.append(f"Platform selected: **{recommended_platform.value}**")
        if not params.platform:
            lines.append(f"  (Auto-detected based on: {platform_data['project_language']})")
        lines.append("")

        # Step 2: Create configuration
        lines.append("## Step 2: Configuration")
        lines.append("")

        from ...models import InitializeConfigInput
        config_result = await initialize_config(InitializeConfigInput(
            project_path=str(project_path),
            platform=recommended_platform,
            exclude_patterns=None  # Let default_factory handle it, tools will merge with DEFAULT_EXCLUDE_PATTERNS
        ))

        if "Error" in config_result:
            return enforce_response_limit(f"Error: Bootstrap failed at configuration step:\n{config_result}")

        lines.append("Created `.doc-manager.yml` configuration")
        lines.append("")

        # Step 3: Create documentation structure
        lines.append("## Step 3: Documentation Structure")
        lines.append("")

        docs_path.mkdir(parents=True, exist_ok=True)

        # Create platform-specific documentation structure
        structure: dict[str, str] = {}
        if recommended_platform == DocumentationPlatform.MKDOCS:
            structure = {
                "README.md": _create_readme_template(project_path),
                "index.md": _create_index_template(project_path),  # MkDocs uses index.md
                "getting-started/installation.md": _create_installation_template(project_path),
                "getting-started/quick-start.md": _create_quickstart_template(project_path),
                "guides/basic-usage.md": _create_usage_template(project_path),
                "reference/configuration.md": _create_config_reference_template(project_path),
            }
        elif recommended_platform == DocumentationPlatform.HUGO:
            structure = {
                "README.md": _create_readme_template(project_path),
                "content/_index.md": _create_index_template(project_path),  # Hugo uses content/_index.md
                "content/getting-started/installation.md": _create_installation_template(project_path),
                "content/getting-started/quick-start.md": _create_quickstart_template(project_path),
                "content/guides/basic-usage.md": _create_usage_template(project_path),
                "content/reference/configuration.md": _create_config_reference_template(project_path),
            }
        elif recommended_platform == DocumentationPlatform.DOCUSAURUS:
            structure = {
                "README.md": _create_readme_template(project_path),
                "intro.md": _create_index_template(project_path),  # Docusaurus uses intro.md
                "getting-started/installation.md": _create_installation_template(project_path),
                "getting-started/quick-start.md": _create_quickstart_template(project_path),
                "guides/basic-usage.md": _create_usage_template(project_path),
                "reference/configuration.md": _create_config_reference_template(project_path),
            }
        created_files = []
        for relative_path, content in structure.items():
            file_path = docs_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            created_files.append(str(file_path.relative_to(project_path)))

        lines.append(f"Created {len(created_files)} documentation files:")
        for file in created_files:
            lines.append(f"  - {file}")
        lines.append("")

        # Step 4: Initialize memory system
        lines.append("## Step 4: Memory System")
        lines.append("")

        from ...models import InitializeMemoryInput
        memory_result = await initialize_memory(InitializeMemoryInput(
            project_path=str(project_path)
        ))

        if "Error" in memory_result:
            return enforce_response_limit(f"Error: Bootstrap failed at memory initialization:\n{memory_result}")

        lines.append("Initialized memory system with baseline checksums")
        lines.append("")

        # Step 5: Initial quality assessment
        lines.append("## Step 5: Initial Quality Assessment")
        lines.append("")

        from ...models import AssessQualityInput
        quality_result = await assess_quality(AssessQualityInput(
            project_path=str(project_path),
            docs_path=params.docs_path
        ))

        quality_data = quality_result if isinstance(quality_result, dict) else json.loads(quality_result)
        overall_score = quality_data.get("overall_score", "unknown")

        lines.append(f"Initial quality score: **{overall_score}**")
        lines.append("  (This will improve as you fill in the template content)")
        lines.append("")

        # Summary and next steps
        lines.append("## Summary")
        lines.append("")
        lines.append("Documentation bootstrapped successfully!")
        lines.append("")
        lines.append("**What was created:**")
        lines.append("- Configuration: `.doc-manager.yml`")
        lines.append(f"- Documentation: `{params.docs_path}/` with {len(created_files)} files")
        lines.append("- Memory system: `.doc-manager/memory/`")
        lines.append("")

        lines.append("## Next Steps")
        lines.append("")
        lines.append("1. **Customize templates**: Fill in project-specific content in the created files")
        lines.append("2. **Add examples**: Include code examples and screenshots")
        lines.append("3. **Configure platform**: Set up your chosen documentation platform")
        lines.append("4. **Run validation**: Use `docmgr_validate_docs` to check for issues")
        lines.append("5. **Assess quality**: Use `docmgr_assess_quality` to measure improvements")
        lines.append("")

        lines.append("**Platform-Specific Setup:**")
        if recommended_platform == DocumentationPlatform.HUGO:
            lines.append("- Install Hugo: `brew install hugo` or download from hugo.io")
            lines.append("- Initialize site: `hugo new site . --force`")
            lines.append("- Add theme: `git submodule add <theme-url> themes/<theme-name>`")
        elif recommended_platform == DocumentationPlatform.MKDOCS:
            lines.append("- Install MkDocs: `pip install mkdocs`")
            lines.append("- Create config: `mkdocs new .`")
            lines.append("- Choose theme in `mkdocs.yml`")
        elif recommended_platform == DocumentationPlatform.DOCUSAURUS:
            lines.append("- Install Node.js/npm if not present")
            lines.append("- Initialize: `npx create-docusaurus@latest . classic`")
            lines.append("- Move generated docs to match structure")

        return {
            "status": "success",
            "message": "Documentation bootstrapped successfully",
            "report": "\n".join(lines),
            "project": project_path.name,
            "platform": recommended_platform.value,
            "docs_path": params.docs_path,
            "files_created": len(created_files),
            "steps": {
                "platform_detection": "completed",
                "configuration": "completed",
                "structure_creation": "completed",
                "memory_initialization": "completed",
                "quality_assessment": "completed"
            },
            "created_files": created_files,
            "quality_score": overall_score
        }
    except Exception as e:
        return enforce_response_limit(handle_error(e, "bootstrap"))


def _create_readme_template(project_path: Path) -> str:
    """Create README.md template."""
    project_name = project_path.name
    return f"""# {project_name} Documentation

Welcome to the {project_name} documentation!

## Quick Links

- [Installation](getting-started/installation.md)
- [Quick Start](getting-started/quick-start.md)
- [Guides](guides/basic-usage.md)
- [Configuration Reference](reference/configuration.md)

## About

[Add a brief description of your project here]

## Getting Help

[Add information about how users can get help - links to issue tracker, community channels, etc.]

## Contributing

[Add link to contributing guide if applicable]
"""


def _create_index_template(project_path: Path) -> str:
    """Create index page template."""
    project_name = project_path.name
    return f"""# {project_name}

## Overview

[Provide a comprehensive overview of your project, its purpose, and key features]

## Key Features

- Feature 1
- Feature 2
- Feature 3

## Quick Example

```
[Add a simple code example showing basic usage]
```

## Documentation Sections

### Getting Started
Learn how to install and start using {project_name}.

### Guides
Step-by-step tutorials for common tasks.

### Reference
Detailed technical reference documentation.
"""


def _create_installation_template(project_path: Path) -> str:
    """Create installation guide template."""
    language = detect_project_language(project_path)

    content = """# Installation

## Prerequisites

[List required software, versions, etc.]

## Installation Methods

### Method 1: [Primary method]

[Provide installation instructions for your primary installation method]

"""

    if language == "Python":
        content += """```bash
pip install {project_name}
```
"""
    elif language == "Go":
        content += """```bash
go install github.com/your-org/{project_name}@latest
```
"""
    elif language in ["JavaScript/TypeScript", "Node.js"]:
        content += """```bash
npm install {project_name}
# or
yarn add {project_name}
```
"""

    content += """
### Method 2: [Alternative method]

[Provide alternative installation method if applicable]

## Verification

[Explain how users can verify the installation was successful]

```bash
[command to verify installation]
```

## Troubleshooting

[Add common installation issues and solutions]
"""

    return content


def _create_quickstart_template(project_path: Path) -> str:
    """Create quick start guide template."""
    project_name = project_path.name
    return f"""# Quick Start

Get up and running with {project_name} in 5 minutes.

## Step 1: Installation

See [Installation Guide](installation.md) for detailed instructions.

## Step 2: Basic Configuration

[Provide minimal configuration needed to get started]

## Step 3: Your First [Task]

[Walk through a simple, practical example]

```bash
[commands or code]
```

## Next Steps

- [Link to more detailed guides]
- [Link to examples]
- [Link to API reference]
"""


def _create_usage_template(project_path: Path) -> str:
    """Create basic usage guide template."""
    return """# Basic Usage

## Common Tasks

### Task 1: [Common task name]

[Step-by-step instructions]

```bash
[example command or code]
```

### Task 2: [Another common task]

[Instructions]

```bash
[example]
```

## Best Practices

[Add recommended practices for using the tool/library]

## Examples

### Example 1: [Realistic scenario]

[Full example with explanation]

## See Also

- [Link to related guides]
- [Link to API reference]
"""


def _create_config_reference_template(project_path: Path) -> str:
    """Create configuration reference template."""
    return """# Configuration Reference

## Configuration File

[Describe the configuration file format, location, and structure]

## Configuration Options

### Option 1

- **Type**: [string/number/boolean/etc.]
- **Default**: [default value]
- **Required**: [yes/no]
- **Description**: [What this option does]

**Example:**
```yaml
option1: value
```

### Option 2

[Repeat for each configuration option]

## Environment Variables

[Document environment variables if applicable]

## Configuration Examples

### Example 1: [Common configuration scenario]

```yaml
[full configuration example]
```

### Example 2: [Another scenario]

```yaml
[configuration]
```
"""
