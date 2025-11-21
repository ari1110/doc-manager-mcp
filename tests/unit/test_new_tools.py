"""Unit tests for new refactored tools (docmgr_init, docmgr_detect_changes, docmgr_update_baseline)."""

import tempfile
from pathlib import Path

import pytest

from doc_manager_mcp.models import (
    DocmgrDetectChangesInput,
    DocmgrInitInput,
    DocmgrUpdateBaselineInput,
)
from doc_manager_mcp.tools.analysis.detect_changes import docmgr_detect_changes
from doc_manager_mcp.tools.state.init import docmgr_init
from doc_manager_mcp.tools.state.update_baseline import docmgr_update_baseline


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create minimal project structure
        (project_path / "src").mkdir()
        (project_path / "src" / "main.py").write_text("def hello(): pass\n")

        # Initialize git repo (required for some operations)
        import subprocess
        subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=project_path,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=project_path,
            check=True,
            capture_output=True
        )

        yield project_path


@pytest.mark.asyncio
async def test_docmgr_init_existing_mode(temp_project):
    """Test docmgr_init with mode='existing'."""
    # Create a docs directory first
    docs_path = temp_project / "docs"
    docs_path.mkdir()
    (docs_path / "README.md").write_text("# Test Docs\n")

    params = DocmgrInitInput(
        project_path=str(temp_project),
        mode="existing",
        platform=None,
        exclude_patterns=None,
        docs_path="docs",
        sources=None
    )

    result = await docmgr_init(params)

    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert result["mode"] == "existing"
    assert "steps_completed" in result

    # Verify created files
    assert (temp_project / ".doc-manager.yml").exists()
    assert (temp_project / ".doc-manager" / "memory").exists()
    assert (temp_project / ".doc-manager" / "dependencies.json").exists()


@pytest.mark.asyncio
async def test_docmgr_init_bootstrap_mode(temp_project):
    """Test docmgr_init with mode='bootstrap'."""
    params = DocmgrInitInput(
        project_path=str(temp_project),
        mode="bootstrap",
        platform=None,
        exclude_patterns=None,
        docs_path="docs",
        sources=None
    )

    result = await docmgr_init(params)

    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert result["mode"] == "bootstrap"

    # Verify docs were created
    docs_path = temp_project / "docs"
    assert docs_path.exists()
    assert (docs_path / "README.md").exists()


@pytest.mark.asyncio
async def test_docmgr_detect_changes_no_baseline(temp_project):
    """Test docmgr_detect_changes when no baseline exists."""
    params = DocmgrDetectChangesInput(
        project_path=str(temp_project),
        since_commit=None,
        mode="checksum",
        include_semantic=False
    )

    result = await docmgr_detect_changes(params)

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "baseline" in result["message"].lower()


@pytest.mark.asyncio
async def test_docmgr_detect_changes_with_baseline(temp_project):
    """Test docmgr_detect_changes after creating baseline."""
    # First initialize to create baseline
    docs_path = temp_project / "docs"
    docs_path.mkdir()
    (docs_path / "README.md").write_text("# Test\n")

    init_params = DocmgrInitInput(
        project_path=str(temp_project),
        mode="existing",
        docs_path="docs"
    )
    await docmgr_init(init_params)

    # Now test detect_changes
    params = DocmgrDetectChangesInput(
        project_path=str(temp_project),
        since_commit=None,
        mode="checksum",
        include_semantic=False
    )

    result = await docmgr_detect_changes(params)

    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "changes_detected" in result
    assert "note" in result
    assert "Read-only" in result["note"]


@pytest.mark.asyncio
async def test_docmgr_detect_changes_readonly(temp_project):
    """Test that docmgr_detect_changes never writes to symbol-baseline.json."""
    # Initialize project
    docs_path = temp_project / "docs"
    docs_path.mkdir()
    (docs_path / "README.md").write_text("# Test\n")

    init_params = DocmgrInitInput(
        project_path=str(temp_project),
        mode="existing",
        docs_path="docs"
    )
    await docmgr_init(init_params)

    # Get baseline modification time before detect_changes
    symbol_baseline_path = temp_project / ".doc-manager" / "memory" / "symbol-baseline.json"
    if symbol_baseline_path.exists():
        mtime_before = symbol_baseline_path.stat().st_mtime
    else:
        mtime_before = None

    # Run detect_changes
    params = DocmgrDetectChangesInput(
        project_path=str(temp_project),
        since_commit=None,
        mode="checksum",
        include_semantic=True  # Even with semantic analysis, should not write
    )
    result = await docmgr_detect_changes(params)

    # Verify baseline was NOT modified
    if mtime_before is not None and symbol_baseline_path.exists():
        mtime_after = symbol_baseline_path.stat().st_mtime
        assert mtime_after == mtime_before, "detect_changes should NEVER write to baselines"


@pytest.mark.asyncio
async def test_docmgr_update_baseline_no_init(temp_project):
    """Test docmgr_update_baseline when .doc-manager not initialized."""
    params = DocmgrUpdateBaselineInput(
        project_path=str(temp_project),
        docs_path="docs"
    )

    result = await docmgr_update_baseline(params)

    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert "not initialized" in result["message"].lower()


@pytest.mark.asyncio
async def test_docmgr_update_baseline_success(temp_project):
    """Test docmgr_update_baseline updates all baselines."""
    # Initialize project first
    docs_path = temp_project / "docs"
    docs_path.mkdir()
    (docs_path / "README.md").write_text("# Test\n")

    init_params = DocmgrInitInput(
        project_path=str(temp_project),
        mode="existing",
        docs_path="docs"
    )
    await docmgr_init(init_params)

    # Make a change to source file
    (temp_project / "src" / "main.py").write_text("def hello():\n    return 'world'\n")

    # Update baselines
    params = DocmgrUpdateBaselineInput(
        project_path=str(temp_project),
        docs_path="docs"
    )

    result = await docmgr_update_baseline(params)

    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert "updated_files" in result

    # Verify all 3 baselines were updated
    updated_files = result["updated_files"]
    assert "repo-baseline.json" in updated_files
    assert "symbol-baseline.json" in updated_files
    assert "dependencies.json" in updated_files
