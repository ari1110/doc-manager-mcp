"""Integration test for 7-tool architecture workflow."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from doc_manager_mcp.models import (
    DocmgrDetectChangesInput,
    DocmgrInitInput,
    DocmgrUpdateBaselineInput,
    SyncInput,
)
from doc_manager_mcp.tools.detect_changes import docmgr_detect_changes
from doc_manager_mcp.tools.init import docmgr_init
from doc_manager_mcp.tools.update_baseline import docmgr_update_baseline
from doc_manager_mcp.tools.workflows import sync


@pytest.fixture
def project_with_git():
    """Create a temporary project with git initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create project structure
        src_dir = project_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text(
            'def greet(name):\n    return f"Hello, {name}!"\n'
        )
        (src_dir / "utils.py").write_text(
            'def add(a, b):\n    return a + b\n'
        )

        # Initialize git
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
async def test_full_7_tool_workflow(project_with_git):
    """Test the complete 7-tool workflow: init -> detect_changes -> update_baseline -> sync."""
    project_path = project_with_git

    # STEP 1: Initialize with existing docs
    docs_path = project_path / "docs"
    docs_path.mkdir()
    (docs_path / "README.md").write_text("# Project Documentation\n")
    (docs_path / "api.md").write_text("# API Reference\n\nSee `src/main.py` for greet function.\n")

    print("\n=== STEP 1: docmgr_init (mode=existing) ===")
    init_result = await docmgr_init(DocmgrInitInput(
        project_path=str(project_path),
        mode="existing",
        docs_path="docs"
    ))

    assert init_result["status"] == "success"
    assert init_result["mode"] == "existing"
    assert (project_path / ".doc-manager.yml").exists()
    assert (project_path / ".doc-manager" / "memory" / "repo-baseline.json").exists()
    print(f"✓ Initialized with {init_result['steps_completed']}")

    # STEP 2: Detect changes (should be none initially)
    print("\n=== STEP 2: docmgr_detect_changes (initial check) ===")
    detect_result1 = await docmgr_detect_changes(DocmgrDetectChangesInput(
        project_path=str(project_path),
        mode="checksum"
    ))

    assert detect_result1["status"] == "success"
    assert detect_result1["changes_detected"] is False
    assert detect_result1["total_changes"] == 0
    print("✓ No changes detected (as expected)")

    # STEP 3: Make code changes
    print("\n=== STEP 3: Make code changes ===")
    (project_path / "src" / "main.py").write_text(
        'def greet(name, greeting="Hello"):\n    return f"{greeting}, {name}!"\n'
    )
    (project_path / "src" / "new_feature.py").write_text(
        'def process_data(data):\n    return data.upper()\n'
    )
    print("✓ Modified main.py and added new_feature.py")

    # STEP 4: Detect changes after modifications (read-only)
    print("\n=== STEP 4: docmgr_detect_changes (after modifications) ===")
    detect_result2 = await docmgr_detect_changes(DocmgrDetectChangesInput(
        project_path=str(project_path),
        mode="checksum"
    ))

    assert detect_result2["status"] == "success"
    assert detect_result2["changes_detected"] is True
    assert detect_result2["total_changes"] > 0
    print(f"✓ Detected {detect_result2['total_changes']} changes")
    print(f"  Changed files: {[c['file'] for c in detect_result2['changed_files']]}")

    # STEP 5: Sync with mode="check" (read-only analysis)
    print("\n=== STEP 5: docmgr_sync (mode=check) ===")
    sync_check_result = await sync(SyncInput(
        project_path=str(project_path),
        mode="check",
        docs_path="docs"
    ))

    assert sync_check_result["status"] == "success"
    assert sync_check_result["mode"] == "check"
    assert sync_check_result["baseline_updated"] is None  # Check mode doesn't update
    print(f"✓ Sync check completed ({sync_check_result['changes']} changes)")

    # STEP 6: Update documentation
    print("\n=== STEP 6: Update documentation ===")
    (docs_path / "api.md").write_text(
        "# API Reference\n\n"
        "## greet(name, greeting='Hello')\n\n"
        "Greet a person with custom greeting.\n"
    )
    print("✓ Updated api.md to reflect code changes")

    # STEP 7: Update baselines atomically
    print("\n=== STEP 7: docmgr_update_baseline ===")
    update_result = await docmgr_update_baseline(DocmgrUpdateBaselineInput(
        project_path=str(project_path),
        docs_path="docs"
    ))

    assert update_result["status"] == "success"
    assert len(update_result["updated_files"]) == 3
    assert "repo-baseline.json" in update_result["updated_files"]
    assert "symbol-baseline.json" in update_result["updated_files"]
    assert "dependencies.json" in update_result["updated_files"]
    print(f"✓ Updated {len(update_result['updated_files'])} baselines")

    # STEP 8: Detect changes again (should be none after baseline update)
    print("\n=== STEP 8: docmgr_detect_changes (after baseline update) ===")
    detect_result3 = await docmgr_detect_changes(DocmgrDetectChangesInput(
        project_path=str(project_path),
        mode="checksum"
    ))

    assert detect_result3["status"] == "success"
    assert detect_result3["changes_detected"] is False
    print("✓ No changes detected (baselines in sync)")

    # STEP 9: Sync with mode="resync" (should update baselines)
    print("\n=== STEP 9: Make another change and sync with mode=resync ===")
    (project_path / "src" / "utils.py").write_text(
        'def add(a, b):\n    """Add two numbers."""\n    return a + b\n'
    )

    sync_resync_result = await sync(SyncInput(
        project_path=str(project_path),
        mode="resync",
        docs_path="docs"
    ))

    assert sync_resync_result["status"] == "success"
    assert sync_resync_result["mode"] == "resync"
    assert sync_resync_result["baseline_updated"] is True
    print(f"✓ Sync resync completed (baselines updated: {sync_resync_result['baseline_updated']})")

    print("\n=== WORKFLOW COMPLETE ===")
    print("✅ All 7-tool workflow steps passed")


@pytest.mark.asyncio
async def test_bootstrap_workflow(project_with_git):
    """Test bootstrap workflow (creating docs from scratch)."""
    project_path = project_with_git

    print("\n=== Bootstrap Workflow Test ===")

    # Initialize with bootstrap mode
    print("\nSTEP 1: docmgr_init (mode=bootstrap)")
    init_result = await docmgr_init(DocmgrInitInput(
        project_path=str(project_path),
        mode="bootstrap",
        docs_path="docs"
    ))

    assert init_result["status"] == "success"
    assert init_result["mode"] == "bootstrap"

    # Verify docs were created
    docs_path = project_path / "docs"
    assert docs_path.exists()
    assert (docs_path / "README.md").exists()
    assert (project_path / ".doc-manager.yml").exists()
    assert (project_path / ".doc-manager" / "dependencies.json").exists()

    print("✓ Bootstrap created docs and initialized system")

    # Detect changes (should be none)
    print("\nSTEP 2: docmgr_detect_changes")
    detect_result = await docmgr_detect_changes(DocmgrDetectChangesInput(
        project_path=str(project_path),
        mode="checksum"
    ))

    assert detect_result["status"] == "success"
    assert detect_result["changes_detected"] is False
    print("✓ No changes detected after bootstrap")

    print("\n✅ Bootstrap workflow complete")


@pytest.mark.asyncio
async def test_readonly_guarantee(project_with_git):
    """Test that detect_changes truly never writes to baselines."""
    project_path = project_with_git

    # Initialize
    docs_path = project_path / "docs"
    docs_path.mkdir()
    (docs_path / "README.md").write_text("# Test\n")

    await docmgr_init(DocmgrInitInput(
        project_path=str(project_path),
        mode="existing",
        docs_path="docs"
    ))

    # Get baseline file modification times
    repo_baseline = project_path / ".doc-manager" / "memory" / "repo-baseline.json"
    symbol_baseline = project_path / ".doc-manager" / "memory" / "symbol-baseline.json"

    baseline_mtimes = {
        "repo": repo_baseline.stat().st_mtime if repo_baseline.exists() else None,
        "symbol": symbol_baseline.stat().st_mtime if symbol_baseline.exists() else None,
    }

    # Make changes
    (project_path / "src" / "main.py").write_text("def new_function(): pass\n")

    # Call detect_changes multiple times
    for i in range(3):
        result = await docmgr_detect_changes(DocmgrDetectChangesInput(
            project_path=str(project_path),
            mode="checksum",
            include_semantic=True  # Even with semantic analysis
        ))
        assert result["status"] == "success"

    # Verify baselines were NOT modified
    new_mtimes = {
        "repo": repo_baseline.stat().st_mtime if repo_baseline.exists() else None,
        "symbol": symbol_baseline.stat().st_mtime if symbol_baseline.exists() else None,
    }

    assert baseline_mtimes == new_mtimes, "detect_changes violated read-only contract!"
    print("✅ Read-only guarantee verified: detect_changes never writes to baselines")
