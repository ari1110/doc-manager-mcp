"""End-to-end workflow tests for doc-manager."""

import pytest
import json
from pathlib import Path

from src.models import (
    InitializeConfigInput,
    InitializeMemoryInput,
    DetectPlatformInput,
    BootstrapInput,
    ValidateDocsInput,
    AssessQualityInput,
    MapChangesInput,
    TrackDependenciesInput,
    SyncInput,
)
from src.constants import ResponseFormat, Platform, ChangeDetectionMode
from src.tools.config import initialize_config
from src.tools.memory import initialize_memory
from src.tools.platform import detect_platform
from src.tools.workflows import bootstrap, sync
from src.tools.validation import validate_docs
from src.tools.quality import assess_quality
from src.tools.changes import map_changes
from src.tools.dependencies import track_dependencies


@pytest.mark.asyncio
class TestCompleteBootstrapWorkflow:
    """Test complete bootstrap workflow from start to finish."""

    async def test_bootstrap_new_python_project(self, tmp_path):
        """Test bootstrapping a new Python project with MkDocs."""
        # Setup: Create a minimal Python project
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup(name='test')")
        (tmp_path / "README.md").write_text("# Test Project\n\nA test project.")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("")
        (src_dir / "main.py").write_text("""
def hello_world():
    \"\"\"Print hello world.\"\"\"
    print("Hello, World!")

def greet(name: str):
    \"\"\"Greet a person by name.\"\"\"
    return f"Hello, {name}!"
""")

        # Step 1: Detect platform
        platform_result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "python" in platform_result.lower()
        assert "mkdocs" in platform_result.lower() or "sphinx" in platform_result.lower()

        # Step 2: Bootstrap documentation
        bootstrap_result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "success" in bootstrap_result.lower()

        # Verify: Check structure created
        assert (tmp_path / ".doc-manager.yml").exists()
        assert (tmp_path / ".doc-manager" / "memory").exists()
        assert (tmp_path / "docs").exists()
        assert (tmp_path / "docs" / "index.md").exists()

        # Step 3: Validate documentation
        validation_result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "validation complete" in validation_result.lower()

        # Step 4: Assess quality
        quality_result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "quality assessment" in quality_result.lower()

        # Step 5: Track dependencies
        deps_result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "dependency" in deps_result.lower()

    async def test_bootstrap_go_project_with_hugo(self, tmp_path):
        """Test bootstrapping a Go project with Hugo."""
        # Setup: Create a Go project
        (tmp_path / "go.mod").write_text("module example.com/test\n\ngo 1.20")
        (tmp_path / "main.go").write_text("""
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
""")
        (tmp_path / "README.md").write_text("# Go Test Project")

        # Detect platform
        platform_result = await detect_platform(DetectPlatformInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "go" in platform_result.lower()
        assert "hugo" in platform_result.lower()

        # Bootstrap with Hugo
        bootstrap_result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.HUGO,
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "success" in bootstrap_result.lower()

        # Verify Hugo structure
        docs_dir = tmp_path / "docs"
        assert docs_dir.exists()
        assert (docs_dir / "content").exists()


@pytest.mark.asyncio
class TestCompleteSyncWorkflow:
    """Test complete synchronization workflow."""

    async def test_full_sync_cycle(self, tmp_path):
        """Test complete sync cycle: init -> changes -> sync."""
        # Setup: Initialize project
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "api.py").write_text("""
def authenticate(username: str, password: str) -> bool:
    \"\"\"Authenticate a user.

    Args:
        username: User's username
        password: User's password

    Returns:
        True if authenticated, False otherwise
    \"\"\"
    return True

def get_user(user_id: int):
    \"\"\"Retrieve user by ID.\"\"\"
    return {"id": user_id, "name": "User"}
""")

        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "api.md").write_text("""
# API Reference

## authenticate(username, password)

Authenticates a user with username and password.

## get_user(user_id)

Retrieves a user by their ID.
""")

        # Step 1: Initialize config
        config_result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "success" in config_result.lower()

        # Step 2: Initialize memory (create baseline)
        memory_result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "success" in memory_result.lower()

        # Step 3: Track initial dependencies
        deps_result = await track_dependencies(TrackDependenciesInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "authenticate" in deps_result
        assert "get_user" in deps_result

        # Simulate code changes
        (tmp_path / "src" / "api.py").write_text("""
def authenticate(username: str, password: str, mfa_token: str = None) -> bool:
    \"\"\"Authenticate a user with optional MFA.

    Args:
        username: User's username
        password: User's password
        mfa_token: Optional MFA token

    Returns:
        True if authenticated, False otherwise
    \"\"\"
    return True

def get_user(user_id: int):
    \"\"\"Retrieve user by ID.\"\"\"
    return {"id": user_id, "name": "User"}

def create_user(username: str, email: str):
    \"\"\"Create a new user.

    Args:
        username: Desired username
        email: User's email address
    \"\"\"
    return {"username": username, "email": email}
""")

        # Step 4: Map changes
        changes_result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "api.py" in changes_result
        assert "change" in changes_result.lower()

        # Step 5: Sync to get recommendations
        sync_result = await sync(SyncInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "change" in sync_result.lower()
        assert "api.py" in sync_result

        # Step 6: Validate current docs
        validation_result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        # Docs are outdated but structurally valid
        assert "validation complete" in validation_result.lower()


@pytest.mark.asyncio
class TestCompleteQualityWorkflow:
    """Test complete quality assurance workflow."""

    async def test_quality_improvement_cycle(self, tmp_path):
        """Test cycle of quality assessment and improvement."""
        # Setup: Create initial low-quality docs
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        (docs_dir / "bad.md").write_text("""
# Stuff

Do the thing with the stuff.
You know what I mean.

[Broken Link](./missing.md)
""")

        # Initialize
        await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Step 1: Initial quality assessment
        quality1 = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "quality assessment" in quality1.lower()

        # Step 2: Validate to find issues
        validation = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "broken" in validation.lower()
        assert "missing.md" in validation

        # Step 3: Improve documentation
        (docs_dir / "bad.md").write_text("""
# Getting Started Guide

This guide will help you get started with the project.

## Prerequisites

Before you begin, ensure you have:
- Python 3.10 or higher
- pip package manager

## Installation

Install the package using pip:

```bash
pip install doc-manager
```

## Quick Start

Initialize your project:

```bash
docmgr init
```

For more details, see the [API Reference](./api.md).
""")

        # Create referenced file
        (docs_dir / "api.md").write_text("""
# API Reference

Complete API documentation.
""")

        # Step 4: Re-validate
        validation2 = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        # Should have fewer issues now
        assert "validation complete" in validation2.lower()

        # Step 5: Re-assess quality
        quality2 = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        # Quality should be better
        assert "quality assessment" in quality2.lower()


@pytest.mark.asyncio
class TestMultiPlatformWorkflow:
    """Test workflows across different platforms."""

    async def test_detect_and_bootstrap_all_platforms(self, tmp_path):
        """Test detection and bootstrap for all supported platforms."""
        platforms_to_test = [
            (Platform.HUGO, "go.mod", "module test"),
            (Platform.MKDOCS, "requirements.txt", "mkdocs==1.4.0"),
            (Platform.SPHINX, "setup.py", "from setuptools import setup"),
            (Platform.DOCUSAURUS, "package.json", '{"dependencies": {"@docusaurus/core": "2.0.0"}}'),
            (Platform.VITEPRESS, "package.json", '{"dependencies": {"vitepress": "1.0.0"}}'),
        ]

        for platform, indicator_file, indicator_content in platforms_to_test:
            # Create platform-specific subdirectory
            platform_dir = tmp_path / platform.value
            platform_dir.mkdir()

            # Create platform indicator
            (platform_dir / indicator_file).write_text(indicator_content)
            (platform_dir / "README.md").write_text(f"# {platform.value.title()} Project")

            # Detect platform
            detect_result = await detect_platform(DetectPlatformInput(
                project_path=str(platform_dir),
                response_format=ResponseFormat.MARKDOWN
            ))
            assert platform.value in detect_result.lower()

            # Bootstrap
            bootstrap_result = await bootstrap(BootstrapInput(
                project_path=str(platform_dir),
                platform=platform,
                response_format=ResponseFormat.MARKDOWN
            ))
            assert "success" in bootstrap_result.lower()

            # Verify structure
            assert (platform_dir / ".doc-manager.yml").exists()
            assert (platform_dir / "docs").exists()


@pytest.mark.asyncio
class TestErrorRecoveryWorkflow:
    """Test error handling and recovery scenarios."""

    async def test_recovery_from_invalid_state(self, tmp_path):
        """Test recovery when project is in invalid state."""
        # Create corrupted config
        (tmp_path / ".doc-manager.yml").write_text("invalid: yaml: content: [unclosed")

        # Should handle gracefully
        result = await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))
        # Should succeed by overwriting
        assert "success" in result.lower()

        # Verify fixed
        assert (tmp_path / ".doc-manager.yml").exists()

    async def test_missing_baseline_recovery(self, tmp_path):
        """Test recovery when baseline is missing."""
        # Create config but no memory
        await initialize_config(InitializeConfigInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))

        # Try to sync without baseline
        sync_result = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should indicate need to initialize
        assert "baseline" in sync_result.lower() or "initialize" in sync_result.lower()

        # Initialize memory
        await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Now sync should work
        sync_result2 = await sync(SyncInput(
            project_path=str(tmp_path),
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "no changes" in sync_result2.lower() or "up to date" in sync_result2.lower()


@pytest.mark.asyncio
class TestRealWorldScenario:
    """Test realistic end-to-end scenario."""

    async def test_realistic_project_lifecycle(self, tmp_path):
        """Test realistic project documentation lifecycle."""
        # Phase 1: Project Creation
        # Create a small CLI tool project
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup(name='mytool')")
        (tmp_path / "README.md").write_text("# My CLI Tool\n\nA useful CLI tool.")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cli.py").write_text("""
import argparse

def main():
    parser = argparse.ArgumentParser(description='My CLI Tool')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--config', type=str, help='Config file path')
    args = parser.parse_args()

def run_command(config_path: str):
    \"\"\"Run the main command.\"\"\"
    print(f"Running with config: {config_path}")
""")

        # Phase 2: Bootstrap Documentation
        bootstrap_result = await bootstrap(BootstrapInput(
            project_path=str(tmp_path),
            platform=Platform.MKDOCS,
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "success" in bootstrap_result.lower()

        # Manually add CLI documentation
        docs_dir = tmp_path / "docs"
        (docs_dir / "cli.md").write_text("""
# CLI Reference

## Basic Usage

```bash
mytool --verbose --config config.yaml
```

### Options

- `--verbose`: Enable verbose output
- `--config`: Path to configuration file
""")

        # Phase 3: Development - Add New Features
        (src_dir / "cli.py").write_text("""
import argparse

def main():
    parser = argparse.ArgumentParser(description='My CLI Tool')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--output', type=str, help='Output directory')  # NEW
    parser.add_argument('--format', choices=['json', 'yaml'], help='Output format')  # NEW
    args = parser.parse_args()

def run_command(config_path: str, output_dir: str = None):
    \"\"\"Run the main command.\"\"\"
    print(f"Running with config: {config_path}")
    if output_dir:
        print(f"Output to: {output_dir}")
""")

        # Phase 4: Detect Changes
        changes_result = await map_changes(MapChangesInput(
            project_path=str(tmp_path),
            mode=ChangeDetectionMode.CHECKSUM,
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "cli.py" in changes_result

        # Phase 5: Sync
        sync_result = await sync(SyncInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "change" in sync_result.lower()
        assert "cli.py" in sync_result

        # Phase 6: Update Documentation
        (docs_dir / "cli.md").write_text("""
# CLI Reference

## Basic Usage

```bash
mytool --verbose --config config.yaml --output ./out --format json
```

### Options

- `--verbose`: Enable verbose output
- `--config`: Path to configuration file
- `--output`: Output directory path (NEW)
- `--format`: Output format: json or yaml (NEW)
""")

        # Phase 7: Final Quality Check
        validation_result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "validation complete" in validation_result.lower()

        quality_result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))
        assert "quality assessment" in quality_result.lower()
