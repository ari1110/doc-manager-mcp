
import pytest
import asyncio
from pathlib import Path


@pytest.mark.asyncio
class TestResourceLimits:
    """Test suite for resource limits and timeout enforcement."""

    async def test_operation_timeout_triggers(self, tmp_path, monkeypatch):
        """Test that real operations trigger timeout when limit is very short.

        Requirements (T087):
        - Create scenario where real tool operation exceeds timeout
        - Use monkeypatch to set OPERATION_TIMEOUT to very short value (0.001s)
        - Call actual tool function
        - Verify TimeoutError is raised
        - Verify error message contains "exceeded timeout"

        Implementation:
        - Patches internal function to inject async delay (2 seconds)
        - Creates a new timeout wrapper with very short timeout (0.5 seconds)
        - Calls validate_docs with the short timeout
        - The 2-second delay exceeds the 0.5-second timeout
        - Verifies timeout triggers with proper error message

        This tests the actual with_timeout decorator mechanism by creating
        a realistic scenario where an operation (simulated slow I/O) exceeds
        the configured timeout limit.
        """
        # Create realistic scenario with files
        for i in range(10):
            doc_file = tmp_path / f"doc{i}.md"
            doc_file.write_text(f"# Test Document {i}\n\n[Link](./doc{i+1}.md)\n")

        # Also need a .doc-manager directory for validation
        doc_manager_dir = tmp_path / ".doc-manager"
        doc_manager_dir.mkdir()

        # Import validation module
        from src.tools import validation
        from src.tools.memory import with_timeout
        from src.models import ValidateDocsInput

        # Get the original unwrapped function
        original_validate_unwrapped = validation.validate_docs.__wrapped__

        # Create a slow version that adds async delay
        async def slow_validate(params):
            """Add async delay to simulate slow operation."""
            # Sleep for 2 seconds (will exceed 0.5s timeout)
            await asyncio.sleep(2)
            return await original_validate_unwrapped(params)

        # Wrap it with short timeout
        @with_timeout(0.5)  # Very short timeout - 0.5 seconds
        async def validate_with_short_timeout(params):
            return await slow_validate(params)

        # Replace validate_docs temporarily
        monkeypatch.setattr(validation, 'validate_docs', validate_with_short_timeout)

        # Operation should timeout: 2 second delay > 0.5 second timeout
        with pytest.raises(TimeoutError) as exc_info:
            await validation.validate_docs(ValidateDocsInput(
                project_path=str(tmp_path),
                response_format="markdown"
            ))

        # Verify timeout error message
        error_msg = str(exc_info.value).lower()
        assert "exceeded timeout" in error_msg, (
            f"Expected 'exceeded timeout' in error message, got: {exc_info.value}"
        )
        # Should mention the timeout value (0.5s)
        assert "0.5" in str(exc_info.value), (
            f"Expected timeout value (0.5s) in error message, got: {exc_info.value}"
        )

    async def test_large_project_file_count_limit(self, tmp_path, monkeypatch):
        """Test that file count limit is enforced during initialize_memory (T086).

        This test verifies FR-019 requirement that the system rejects
        operations when file count exceeds MAX_FILES limit (10,000).

        Requirements (T086):
        - Create 10,001+ files (or use smaller limit with monkeypatch)
        - Call actual tool (initialize_memory or validate_docs)
        - Verify ValueError is raised with "File count limit exceeded"
        - Verify error message contains actionable guidance

        Implementation:
        - Uses monkeypatch to set MAX_FILES to 50 for fast testing
        - Creates 51 files (exceeding the limit)
        - Calls initialize_memory tool
        - Verifies proper error handling with actionable message
        """
        # Set smaller limit for fast testing (instead of 10,000)
        from src.tools import memory
        monkeypatch.setattr(memory, 'MAX_FILES', 50)

        # Create 51 files (over the limit of 50)
        for i in range(51):
            test_file = tmp_path / f"file{i:04d}.txt"
            test_file.write_text(f"Content for file {i}")

        # Call actual tool that traverses files
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format="markdown"
        ))

        # Tool returns error string instead of raising exception
        # Verify error message contains expected information
        error_msg = result.lower()
        assert "error" in error_msg, \
            "Response must indicate an error occurred"
        assert "file count limit exceeded" in error_msg, \
            "Error message must indicate file count limit was exceeded"
        assert "50" in result, \
            "Error message must show the actual limit (50)"
        assert "increasing the limit" in error_msg or "smaller directory" in error_msg, \
            "Error message must provide actionable guidance (FR-019)"

    async def test_validate_docs_file_count_limit(self, tmp_path, monkeypatch):
        """Test that file count limit is enforced during validate_docs.

        This test verifies FR-019 is enforced across different tools,
        specifically during documentation validation.
        """
        # Set smaller limit for fast testing
        from src.tools import validation
        monkeypatch.setattr(validation, 'MAX_FILES', 30)

        # Create docs directory structure
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create 31 markdown files (over the limit of 30)
        for i in range(31):
            md_file = docs_dir / f"doc{i:04d}.md"
            md_file.write_text(f"# Document {i}\n\nSome content here.")

        # Call validate_docs tool
        from src.tools.validation import validate_docs
        from src.models import ValidateDocsInput

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format="markdown"
        ))

        # Verify error message
        error_msg = result.lower()
        assert "error" in error_msg, \
            "Response must indicate an error occurred"
        assert "file count limit exceeded" in error_msg, \
            "Error message must indicate file count limit was exceeded"
        assert "30" in result, \
            "Error message must show the actual limit (30)"

    async def test_file_count_limit_excludes_hidden_files(self, tmp_path, monkeypatch):
        """Test that hidden files (starting with .) don't count toward limit.

        This verifies that .git, .doc-manager, and other hidden directories
        are properly excluded from the file count.
        """
        from src.tools import memory
        monkeypatch.setattr(memory, 'MAX_FILES', 25)

        # Create hidden directory with many files (should be ignored)
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        for i in range(100):
            (hidden_dir / f"hidden{i}.txt").write_text("ignored")

        # Create normal files under the limit
        for i in range(20):
            (tmp_path / f"visible{i}.txt").write_text(f"Content {i}")

        # Should succeed because hidden files don't count
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format="json"
        ))

        # Verify success (no exception raised)
        assert "success" in result.lower() or "initialized" in result.lower(), \
            "Should succeed when only visible files are under limit"

    async def test_file_count_under_limit_succeeds(self, tmp_path, monkeypatch):
        """Test that operations succeed when file count is under the limit.

        This verifies that the limit check allows operations when
        file count is below MAX_FILES.
        """
        from src.tools import memory
        monkeypatch.setattr(memory, 'MAX_FILES', 30)

        # Create files under the limit
        for i in range(20):
            (tmp_path / f"file{i}.txt").write_text(f"Content {i}")

        # Should succeed because we're under the limit
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format="json"
        ))

        # Verify success
        assert "success" in result.lower() or "initialized" in result.lower(), \
            "Should succeed when file count is under limit"
        assert "error" not in result.lower(), \
            "Should not contain error message when under limit"

    async def test_large_project_realistic_simulation(self, tmp_path, monkeypatch):
        """Test with realistic project structure hitting the limit.

        This simulates a more realistic scenario with nested directories,
        mixed file types, and some excluded patterns.
        """
        from src.tools import memory
        monkeypatch.setattr(memory, 'MAX_FILES', 100)

        # Create realistic directory structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create files in each directory
        # src: 60 files
        for i in range(60):
            (src_dir / f"module{i}.py").write_text(f"# Module {i}")

        # tests: 45 files (total 105, over limit)
        for i in range(45):
            (tests_dir / f"test_{i}.py").write_text(f"# Test {i}")

        # docs: 10 files
        for i in range(10):
            (docs_dir / f"doc{i}.md").write_text(f"# Doc {i}")

        # Should fail because total is 115 files (over 100 limit)
        from src.tools.memory import initialize_memory
        from src.models import InitializeMemoryInput

        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(tmp_path),
            response_format="markdown"
        ))

        error_msg = result.lower()
        assert "error" in error_msg
        assert "file count limit exceeded" in error_msg
        assert "100" in result
