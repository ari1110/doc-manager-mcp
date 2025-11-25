"""Tests for configurable documentation path mappings.

This module tests that doc_mappings configuration allows projects with
non-standard documentation layouts to correctly map code changes to
affected documentation files.
"""

import tempfile
from pathlib import Path
import pytest
import yaml
from doc_manager_mcp.tools._internal.changes import _map_to_affected_docs
from doc_manager_mcp.core.config import save_config, load_config


@pytest.fixture
def temp_project():
    """Create a temporary project structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        yield project_path


def create_project_with_custom_docs(project_path: Path, docs_dir: str, doc_mappings: dict = None):
    """Create a project with custom documentation layout.

    Args:
        project_path: Root project directory
        docs_dir: Name of documentation directory (e.g., 'docs', 'documentation', 'wiki')
        doc_mappings: Optional custom doc_mappings for config
    """
    # Create documentation directory
    docs_path = project_path / docs_dir
    docs_path.mkdir(parents=True)

    # Create source directories
    (project_path / "src").mkdir()
    (project_path / "cmd" / "cli").mkdir(parents=True)
    (project_path / "api").mkdir()
    (project_path / "config").mkdir()
    (project_path / ".github" / "workflows").mkdir(parents=True)

    # Create sample source files
    (project_path / "src" / "core.py").write_text("# Core module\n")
    (project_path / "cmd" / "cli" / "main.go").write_text("// CLI main\n")
    (project_path / "api" / "handler.js").write_text("// API handler\n")
    (project_path / "config" / "settings.yaml").write_text("# Config\n")
    (project_path / ".github" / "workflows" / "ci.yml").write_text("# CI\n")

    # Create documentation files based on mappings
    if doc_mappings:
        for category, doc_path in doc_mappings.items():
            full_path = project_path / doc_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f"# {category.title()} Documentation\n")
    else:
        # Create default structure
        (docs_path / "reference").mkdir()
        (docs_path / "guides").mkdir()
        (docs_path / "reference" / "command-reference.md").write_text("# CLI Commands\n")
        (docs_path / "reference" / "api.md").write_text("# API\n")
        (docs_path / "guides" / "basic-workflows.md").write_text("# Workflows\n")

    # Create README.md
    (project_path / "README.md").write_text("# Project\n")

    # Create config
    config = {
        "platform": "mkdocs",
        "docs_path": docs_dir,
        "exclude": [],
        "sources": ["src/**/*.py", "cmd/**/*.go", "api/**/*.js"],
        "metadata": {
            "language": "Python",
            "version": "1.0.0"
        }
    }

    if doc_mappings:
        config["doc_mappings"] = doc_mappings

    save_config(project_path, config)

    return project_path


def test_standard_docs_layout_with_mappings(temp_project):
    """Test standard docs/ layout with explicit doc_mappings."""
    doc_mappings = {
        "cli": "docs/reference/command-reference.md",
        "api": "docs/reference/api.md",
        "config": "docs/reference/configuration.md"
    }

    project_path = create_project_with_custom_docs(
        temp_project, "docs", doc_mappings
    )

    # Simulate CLI file change
    changed_files = [
        {"file": "cmd/cli/main.go", "change_type": "modified"}
    ]

    # Mock categorization (would normally be done by _categorize_change)
    for change in changed_files:
        change["category"] = "cli"

    # Map to affected docs
    affected = _map_to_affected_docs(changed_files, project_path)

    # Verify CLI doc is affected
    assert len(affected) > 0, "Should have affected docs"
    cli_docs = [doc for doc in affected if "command-reference" in doc["file"]]
    assert len(cli_docs) > 0, "CLI changes should affect command-reference.md"
    assert cli_docs[0]["exists"], "Mapped doc should exist"


def test_documentation_directory_layout(temp_project):
    """Test non-standard 'documentation/' directory."""
    doc_mappings = {
        "cli": "documentation/commands/reference.md",
        "api": "documentation/api/index.md",
        "config": "documentation/configuration.md"
    }

    project_path = create_project_with_custom_docs(
        temp_project, "documentation", doc_mappings
    )

    # Simulate API file change
    changed_files = [
        {"file": "api/handler.js", "change_type": "modified", "category": "api"}
    ]

    affected = _map_to_affected_docs(changed_files, project_path)

    # Verify API doc in documentation/ is affected
    api_docs = [doc for doc in affected if "api" in doc["file"].lower()]
    assert len(api_docs) > 0, "API changes should affect api docs"
    assert "documentation" in api_docs[0]["file"], "Should use documentation/ directory"
    assert api_docs[0]["exists"], "Mapped doc should exist"


def test_wiki_directory_layout(temp_project):
    """Test wiki/ directory layout (common in GitHub projects)."""
    doc_mappings = {
        "cli": "wiki/CLI-Commands.md",
        "api": "wiki/API-Reference.md",
        "config": "wiki/Configuration.md"
    }

    project_path = create_project_with_custom_docs(
        temp_project, "wiki", doc_mappings
    )

    # Simulate config file change
    changed_files = [
        {"file": "config/settings.yaml", "change_type": "modified", "category": "config"}
    ]

    affected = _map_to_affected_docs(changed_files, project_path)

    # Verify wiki doc is affected
    config_docs = [doc for doc in affected if "Configuration" in doc["file"]]
    assert len(config_docs) > 0, "Config changes should affect Configuration.md"
    assert "wiki" in config_docs[0]["file"], "Should use wiki/ directory"


def test_underscore_docs_layout(temp_project):
    """Test _docs/ directory layout (Jekyll style)."""
    doc_mappings = {
        "cli": "_docs/cli.md",
        "api": "_docs/api.md"
    }

    project_path = create_project_with_custom_docs(
        temp_project, "_docs", doc_mappings
    )

    changed_files = [
        {"file": "cmd/cli/main.go", "change_type": "modified", "category": "cli"}
    ]

    affected = _map_to_affected_docs(changed_files, project_path)

    cli_docs = [doc for doc in affected if "cli.md" in doc["file"]]
    assert len(cli_docs) > 0
    assert "_docs" in cli_docs[0]["file"]


def test_site_docs_subdirectory(temp_project):
    """Test site/docs/ nested directory layout."""
    doc_mappings = {
        "cli": "site/docs/reference/cli.md",
        "api": "site/docs/reference/api.md"
    }

    project_path = create_project_with_custom_docs(
        temp_project, "site/docs", doc_mappings
    )

    changed_files = [
        {"file": "api/handler.js", "change_type": "modified", "category": "api"}
    ]

    affected = _map_to_affected_docs(changed_files, project_path)

    api_docs = [doc for doc in affected if "api.md" in doc["file"]]
    assert len(api_docs) > 0
    assert "site/docs" in api_docs[0]["file"]


def test_missing_config_falls_back_to_defaults(temp_project):
    """Test that missing doc_mappings config falls back to default paths."""
    # Create project WITHOUT doc_mappings in config
    project_path = temp_project

    # Create standard structure but no config
    (project_path / "docs" / "reference").mkdir(parents=True)
    (project_path / "docs" / "reference" / "command-reference.md").write_text("# CLI\n")
    (project_path / "cmd" / "cli").mkdir(parents=True)
    (project_path / "cmd" / "cli" / "main.go").write_text("// CLI\n")

    # Create config WITHOUT doc_mappings
    config = {
        "platform": "mkdocs",
        "docs_path": "docs",
        "exclude": []
    }
    save_config(project_path, config)

    # Verify config has no doc_mappings
    loaded_config = load_config(project_path)
    assert "doc_mappings" not in loaded_config or loaded_config.get("doc_mappings") is None

    # Map changes - should fall back to defaults
    changed_files = [
        {"file": "cmd/cli/main.go", "change_type": "modified", "category": "cli"}
    ]

    affected = _map_to_affected_docs(changed_files, project_path)

    # Should use default path
    cli_docs = [doc for doc in affected if "command-reference" in doc["file"]]
    assert len(cli_docs) > 0, "Should fall back to default path"
    assert "docs/reference/command-reference.md" in cli_docs[0]["file"]


def test_partial_config_with_some_mappings(temp_project):
    """Test partial doc_mappings config (some categories mapped, others use defaults)."""
    # Only map CLI, leave others to default
    doc_mappings = {
        "cli": "documentation/commands.md"
    }

    project_path = temp_project

    # Create both custom and default paths
    (project_path / "documentation").mkdir()
    (project_path / "documentation" / "commands.md").write_text("# CLI\n")
    (project_path / "docs" / "reference").mkdir(parents=True)
    (project_path / "docs" / "reference" / "api.md").write_text("# API\n")

    # Create source files
    (project_path / "cmd" / "cli").mkdir(parents=True)
    (project_path / "cmd" / "cli" / "main.go").write_text("// CLI\n")
    (project_path / "api").mkdir()
    (project_path / "api" / "handler.js").write_text("// API\n")

    # Save config with partial mappings
    config = {
        "platform": "mkdocs",
        "docs_path": "docs",
        "doc_mappings": doc_mappings,
        "exclude": []
    }
    save_config(project_path, config)

    # Test CLI change - should use custom mapping
    cli_changes = [
        {"file": "cmd/cli/main.go", "change_type": "modified", "category": "cli"}
    ]

    affected_cli = _map_to_affected_docs(cli_changes, project_path)
    cli_docs = [doc for doc in affected_cli if "commands.md" in doc["file"]]
    assert len(cli_docs) > 0, "Should use custom mapping for CLI"
    assert "documentation/commands.md" in cli_docs[0]["file"]

    # Test API change - should use default mapping
    api_changes = [
        {"file": "api/handler.js", "change_type": "modified", "category": "api"}
    ]

    affected_api = _map_to_affected_docs(api_changes, project_path)
    api_docs = [doc for doc in affected_api if "api" in doc["file"].lower()]
    assert len(api_docs) > 0, "Should fall back to default for API"
    # Default should be docs/reference/api.md
    assert any("docs" in doc["file"] and "api.md" in doc["file"] for doc in api_docs)


def test_nonexistent_mapped_docs_marked_as_not_exists(temp_project):
    """Test that mapped docs that don't exist are marked with exists=False."""
    doc_mappings = {
        "cli": "docs/nonexistent-cli.md",  # This file doesn't exist
        "api": "docs/existing-api.md"      # This file exists
    }

    project_path = temp_project

    # Create docs dir
    (project_path / "docs").mkdir()

    # Only create the API doc, not the CLI doc
    (project_path / "docs" / "existing-api.md").write_text("# API\n")

    # Create source files
    (project_path / "cmd" / "cli").mkdir(parents=True)
    (project_path / "cmd" / "cli" / "main.go").write_text("// CLI\n")

    config = {
        "platform": "mkdocs",
        "docs_path": "docs",
        "doc_mappings": doc_mappings,
        "exclude": []
    }
    save_config(project_path, config)

    # Test CLI change to nonexistent doc
    cli_changes = [
        {"file": "cmd/cli/main.go", "change_type": "modified", "category": "cli"}
    ]

    affected = _map_to_affected_docs(cli_changes, project_path)

    # Find the CLI doc entry
    cli_docs = [doc for doc in affected if "nonexistent-cli.md" in doc["file"]]
    assert len(cli_docs) > 0, "Should still map to configured path even if doesn't exist"
    assert cli_docs[0]["exists"] == False, "Should mark nonexistent doc with exists=False"


def test_multiple_categories_map_to_same_doc(temp_project):
    """Test multiple change categories can map to the same documentation file."""
    # Both cli and config map to the same doc
    doc_mappings = {
        "cli": "docs/getting-started.md",
        "config": "docs/getting-started.md",  # Same file
        "api": "docs/api-reference.md"
    }

    project_path = temp_project

    (project_path / "docs").mkdir()
    (project_path / "docs" / "getting-started.md").write_text("# Getting Started\n")
    (project_path / "docs" / "api-reference.md").write_text("# API\n")

    (project_path / "cmd" / "cli").mkdir(parents=True)
    (project_path / "cmd" / "cli" / "main.go").write_text("// CLI\n")
    (project_path / "config").mkdir()
    (project_path / "config" / "settings.yaml").write_text("# Config\n")

    config = {
        "platform": "mkdocs",
        "docs_path": "docs",
        "doc_mappings": doc_mappings,
        "exclude": []
    }
    save_config(project_path, config)

    # Changes in both CLI and config
    changes = [
        {"file": "cmd/cli/main.go", "change_type": "modified", "category": "cli"},
        {"file": "config/settings.yaml", "change_type": "modified", "category": "config"}
    ]

    affected = _map_to_affected_docs(changes, project_path)

    # Should have getting-started.md (but only once, deduplicated)
    getting_started_docs = [doc for doc in affected if "getting-started.md" in doc["file"]]
    assert len(getting_started_docs) == 1, "Should deduplicate same doc from multiple categories"

    # Should list both files as affected_by
    assert len(getting_started_docs[0]["affected_by"]) == 2, "Should track both source files"


@pytest.mark.parametrize("layout,doc_dir", [
    ("documentation", "documentation"),
    ("wiki", "wiki"),
    ("_docs", "_docs"),
    ("help", "help"),
    ("site/docs", "site/docs")
])
def test_parametrized_non_standard_layouts(temp_project, layout, doc_dir):
    """Parametrized test for various non-standard layouts."""
    doc_mappings = {
        "cli": f"{doc_dir}/cli.md"
    }

    project_path = create_project_with_custom_docs(
        temp_project, doc_dir, doc_mappings
    )

    changed_files = [
        {"file": "cmd/cli/main.go", "change_type": "modified", "category": "cli"}
    ]

    affected = _map_to_affected_docs(changed_files, project_path)

    assert len(affected) > 0, f"Should have affected docs for {layout}"
    assert any(doc_dir in doc["file"] for doc in affected), \
        f"Should use {doc_dir} directory"
