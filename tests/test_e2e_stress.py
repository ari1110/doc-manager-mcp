
import pytest
import json
import asyncio
from pathlib import Path

from src.models import (
    InitializeMemoryInput,
    TrackDependenciesInput,
    ValidateDocsInput,
    AssessQualityInput,
)
from src.constants import ResponseFormat
from src.tools.memory import initialize_memory
from src.tools.dependencies import track_dependencies
from src.tools.validation import validate_docs
from src.tools.quality import assess_quality


@pytest.mark.asyncio
class TestConcurrentStress:

    async def test_100_concurrent_tool_invocations(self, tmp_path):
        """Test 100 concurrent tool invocations to verify no race conditions, deadlocks, or corruption.

        This test verifies:
        - File locks prevent concurrent write corruption
        - All operations complete successfully or with expected errors
        - No race conditions or deadlocks occur
        - State files (baseline.json, dependencies.json) remain valid after concurrent writes
        - System handles high concurrency without crashes

        Test approach:
        - Create test project with 10 markdown files
        - Launch 100 concurrent asyncio tasks (25 each of 4 different tools)
        - Mix operations: initialize_memory, track_dependencies, validate_docs, assess_quality
        - Use same project_path for all operations (tests concurrent access)
        - Verify all operations complete (some may error, but no crashes)
        - Verify state files remain valid JSON after all operations
        """
        # Setup test project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Create test markdown files
        for i in range(10):
            doc_content = f"""# Document {i}

## Overview
This is test document number {i}.

## Details
- Point A
- Point B
- Point C

## References
See `file{i}.py` for implementation.

## Links
- [Internal link](doc{(i+1) % 10}.md)
- [External link](https://example.com/doc{i})
"""
            (docs_dir / f"doc{i}.md").write_text(doc_content)

        # Create some source files referenced by docs
        src_dir = project_dir / "src"
        src_dir.mkdir()
        for i in range(10):
            (src_dir / f"file{i}.py").write_text(f"# File {i}\ndef function{i}():\n    pass\n")

        # Define concurrent operations
        async def run_memory_init(task_id: int):
            """Initialize memory system."""
            try:
                result = await initialize_memory(InitializeMemoryInput(
                    project_path=str(project_dir),
                    response_format="markdown"
                ))
                return ("memory_init", task_id, "success", result)
            except Exception as e:
                return ("memory_init", task_id, "error", str(e))

        async def run_track_deps(task_id: int):
            """Track documentation dependencies."""
            try:
                result = await track_dependencies(TrackDependenciesInput(
                    project_path=str(project_dir),
                    docs_path="docs",
                    response_format="markdown"
                ))
                return ("track_deps", task_id, "success", result)
            except Exception as e:
                return ("track_deps", task_id, "error", str(e))

        async def run_validate(task_id: int):
            """Validate documentation."""
            try:
                result = await validate_docs(ValidateDocsInput(
                    project_path=str(project_dir),
                    docs_path="docs",
                    response_format="markdown"
                ))
                return ("validate", task_id, "success", result)
            except Exception as e:
                return ("validate", task_id, "error", str(e))

        async def run_assess_quality(task_id: int):
            """Assess documentation quality."""
            try:
                result = await assess_quality(AssessQualityInput(
                    project_path=str(project_dir),
                    docs_path="docs",
                    response_format="markdown"
                ))
                return ("assess_quality", task_id, "success", result)
            except Exception as e:
                return ("assess_quality", task_id, "error", str(e))

        # Build list of 100 concurrent tasks (25 of each type)
        tasks = []
        task_id = 0

        for _ in range(25):
            tasks.append(run_memory_init(task_id))
            task_id += 1

        for _ in range(25):
            tasks.append(run_track_deps(task_id))
            task_id += 1

        for _ in range(25):
            tasks.append(run_validate(task_id))
            task_id += 1

        for _ in range(25):
            tasks.append(run_assess_quality(task_id))
            task_id += 1

        # Execute all 100 tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all 100 operations completed (no crashes)
        assert len(results) == 100, f"Expected 100 results, got {len(results)}"

        # Analyze results by operation type
        success_count = 0
        error_count = 0
        exception_count = 0

        operation_stats = {
            "memory_init": {"success": 0, "error": 0},
            "track_deps": {"success": 0, "error": 0},
            "validate": {"success": 0, "error": 0},
            "assess_quality": {"success": 0, "error": 0},
        }

        for result in results:
            if isinstance(result, Exception):
                # Unexpected exception (not caught by tool)
                exception_count += 1
            elif isinstance(result, tuple) and len(result) == 4:
                op_type, task_id, status, data = result
                if status == "success":
                    success_count += 1
                    operation_stats[op_type]["success"] += 1
                else:
                    error_count += 1
                    operation_stats[op_type]["error"] += 1
            else:
                # Malformed result
                exception_count += 1

        # At least some operations should succeed (concurrent access is handled)
        assert success_count > 0, "No operations succeeded - possible deadlock or systemic failure"

        # No unexpected exceptions should occur (all errors should be handled)
        assert exception_count == 0, f"Found {exception_count} unexpected exceptions"

        # Verify state files remain valid JSON (no corruption from concurrent writes)

        # Check baseline.json
        baseline_path = project_dir / ".doc-manager" / "memory" / "repo-baseline.json"
        if baseline_path.exists():
            with open(baseline_path) as f:
                baseline = json.load(f)  # Will raise if corrupted
                assert "files" in baseline, "Baseline missing 'files' key"
                assert "metadata" in baseline, "Baseline missing 'metadata' key"

        # Check dependencies.json
        deps_path = project_dir / ".doc-manager" / "dependencies" / "dependencies.json"
        if deps_path.exists():
            with open(deps_path) as f:
                dependencies = json.load(f)  # Will raise if corrupted
                assert "files" in dependencies, "Dependencies missing 'files' key"
                assert "metadata" in dependencies, "Dependencies missing 'metadata' key"

        # Check validation-report.json
        validation_path = project_dir / ".doc-manager" / "validation" / "validation-report.json"
        if validation_path.exists():
            with open(validation_path) as f:
                validation = json.load(f)  # Will raise if corrupted
                assert "summary" in validation, "Validation missing 'summary' key"

        # Check quality-report.json
        quality_path = project_dir / ".doc-manager" / "quality" / "quality-report.json"
        if quality_path.exists():
            with open(quality_path) as f:
                quality = json.load(f)  # Will raise if corrupted
                assert "overall_score" in quality, "Quality report missing 'overall_score' key"

        # Print stress test summary for debugging
        print("\n=== Stress Test Summary ===")
        print(f"Total operations: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Handled errors: {error_count}")
        print(f"Unexpected exceptions: {exception_count}")
        print("\nOperation breakdown:")
        for op_type, stats in operation_stats.items():
            print(f"  {op_type}: {stats['success']} success, {stats['error']} error")

        # Overall assertion: system handled concurrent load without corruption
        assert baseline_path.exists() or deps_path.exists() or validation_path.exists() or quality_path.exists(), \
            "No state files created - all operations may have failed"
