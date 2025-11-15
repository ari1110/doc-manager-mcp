"""Integration tests for concurrent operations (T071 - US6).

Tests concurrent file modifications with locking to ensure data integrity.

@spec 001
@userStory US6
@functionalReq FR-018
"""

import pytest
from pathlib import Path
import json
import asyncio
from threading import Thread
import time

from src.models import InitializeMemoryInput, TrackDependenciesInput
from src.constants import ResponseFormat
from src.tools.memory import initialize_memory
from src.tools.dependencies import track_dependencies


@pytest.mark.asyncio
class TestConcurrentFileModification:
    """Integration tests for concurrent file modifications with locks (T071 - US6)."""

    """
    @spec 001
    @testType integration
    @userStory US6
    @functionalReq FR-018
    """
    async def test_concurrent_memory_initialization(self, tmp_path):
        """Test that concurrent memory initializations don't corrupt baseline file.

        This test verifies that file locking prevents race conditions when
        multiple processes try to initialize memory simultaneously.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create some files
        (project_dir / "file1.txt").write_text("content1")
        (project_dir / "file2.txt").write_text("content2")

        # Run two initializations concurrently
        results = await asyncio.gather(
            initialize_memory(InitializeMemoryInput(
                project_path=str(project_dir),
                response_format=ResponseFormat.MARKDOWN
            )),
            initialize_memory(InitializeMemoryInput(
                project_path=str(project_dir),
                response_format=ResponseFormat.MARKDOWN
            ))
        )

        # Both should succeed
        assert all("initialized successfully" in r.lower() for r in results)

        # Baseline file should be valid JSON
        baseline_path = project_dir / ".doc-manager" / "memory" / "repo-baseline.json"
        assert baseline_path.exists()

        with open(baseline_path) as f:
            baseline = json.load(f)
            assert "files" in baseline
            assert baseline["file_count"] == 2

    """
    @spec 001
    @testType integration
    @userStory US6
    @functionalReq FR-018
    """
    async def test_concurrent_dependency_tracking(self, tmp_path):
        """Test that concurrent dependency tracking doesn't corrupt dependencies file."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Create doc files
        (docs_dir / "doc1.md").write_text("Reference to `function1()` in `file1.py`")
        (docs_dir / "doc2.md").write_text("Reference to `function2()` in `file2.py`")

        # Run two dependency tracking operations concurrently
        results = await asyncio.gather(
            track_dependencies(TrackDependenciesInput(
                project_path=str(project_dir),
                docs_path="docs",
                response_format=ResponseFormat.MARKDOWN
            )),
            track_dependencies(TrackDependenciesInput(
                project_path=str(project_dir),
                docs_path="docs",
                response_format=ResponseFormat.MARKDOWN
            ))
        )

        # Both should succeed
        assert all(isinstance(r, str) for r in results)

        # Dependencies file should be valid JSON
        deps_path = project_dir / ".doc-manager" / "dependencies.json"
        assert deps_path.exists()

        with open(deps_path) as f:
            deps = json.load(f)
            assert "doc_to_code" in deps
            assert "code_to_doc" in deps

    """
    @spec 001
    @testType integration
    @userStory US6
    @functionalReq FR-018
    """
    async def test_file_lock_prevents_corruption(self, tmp_path):
        """Test that file locking prevents JSON corruption during concurrent writes."""
        from src.utils import file_lock

        test_file = tmp_path / "test.json"
        test_file.write_text('{"counter": 0}')

        # Use list for thread-safe tracking (list.append is atomic)
        completions = []
        errors = []

        def increment_counter():
            try:
                with file_lock(test_file):
                    # Read current value
                    with open(test_file) as f:
                        data = json.load(f)

                    # Increment
                    data["counter"] += 1
                    time.sleep(0.01)  # Simulate processing

                    # Write back
                    with open(test_file, 'w') as f:
                        json.dump(data, f)

                    completions.append(1)
            except Exception as e:
                errors.append(str(e))

        # Start 3 threads trying to increment concurrently
        threads = [Thread(target=increment_counter) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All writes should succeed
        assert len(completions) == 3, f"Expected 3 completions, got {len(completions)}. Errors: {errors}"
        assert len(errors) == 0, f"Expected no errors, got: {errors}"

        # Final value should be 3 (no lost updates)
        with open(test_file) as f:
            data = json.load(f)
            assert data["counter"] == 3
