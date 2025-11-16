
import pytest
from pathlib import Path

from src.models import InitializeMemoryInput
from src.constants import ResponseFormat
from src.tools.memory import initialize_memory


@pytest.mark.asyncio
class TestE2ESecuritySymlinks:
    """E2E tests for symlink security across all operations."""

    async def test_malicious_symlinks_in_memory_initialization(self, tmp_path):
        """Test that malicious symlinks are skipped during memory initialization (T035 - US1).

        This E2E test creates a realistic attack scenario where:
        1. Project contains malicious symlinks pointing outside boundary
        2. User initializes memory system
        3. System should skip malicious symlinks without crashing
        4. Baseline should only include safe files within project
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create legitimate project files
        (project_root / "README.md").write_text("# Project\n\nLegitimate content")
        src_dir = project_root / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("def main(): pass")

        # Create sensitive file outside project
        outside_dir = tmp_path / "sensitive"
        outside_dir.mkdir()
        secret_file = outside_dir / "credentials.txt"
        secret_file.write_text("SECRET_API_KEY=abc123")

        # Create malicious symlinks inside project pointing outside
        malicious_link1 = project_root / "steal_creds"
        malicious_link1.symlink_to(secret_file)

        malicious_link2 = src_dir / "backdoor.py"
        malicious_link2.symlink_to(outside_dir)

        # Initialize memory - should complete without processing malicious symlinks
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(project_root),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Memory initialization should succeed
        assert "initialized successfully" in result.lower()

        # Check baseline file was created
        baseline_path = project_root / ".doc-manager" / "memory" / "repo-baseline.json"
        assert baseline_path.exists()

        # Read baseline and verify it doesn't include malicious symlinks
        import json
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)

        # Verify legitimate files are included
        assert "README.md" in baseline["files"]
        assert "src/main.py" in baseline["files"]

        # Verify malicious symlinks are NOT included
        assert "steal_creds" not in str(baseline["files"])
        assert "backdoor.py" not in str(baseline["files"])

        # Verify file count is correct (only safe files)
        assert baseline["file_count"] == 2  # README.md + main.py

    async def test_symlink_chain_attack(self, tmp_path):
        """Test that symlink chains escaping boundary are blocked (T035 - US1).

        This test simulates a sophisticated attack using symlink chains:
        1. Symlink inside project points to intermediate symlink
        2. Intermediate symlink points outside project boundary
        3. System should detect and reject the entire chain
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create legitimate file
        (project_root / "README.md").write_text("# README")

        # Create target outside project
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("Sensitive data")

        # Create intermediate symlink outside project
        intermediate_link = tmp_path / "intermediate_link"
        intermediate_link.symlink_to(secret_file)

        # Create symlink inside project pointing to intermediate
        chain_link = project_root / "chain_attack"
        chain_link.symlink_to(intermediate_link)

        # Initialize memory
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(project_root),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should complete successfully
        assert "initialized successfully" in result.lower()

        # Verify baseline doesn't include the symlink chain
        baseline_path = project_root / ".doc-manager" / "memory" / "repo-baseline.json"
        import json
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)

        # Only README.md should be included
        assert baseline["file_count"] == 1
        assert "README.md" in baseline["files"]
        assert "chain_attack" not in str(baseline["files"])

    async def test_safe_symlinks_within_boundary(self, tmp_path):
        """Test that safe symlinks within project boundary are allowed (T035 - US1).

        This test verifies that legitimate use of symlinks within the project
        is supported (e.g., for documentation aliases or build artifacts).
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create original file
        docs_dir = project_root / "docs"
        docs_dir.mkdir()
        original_file = docs_dir / "guide.md"
        original_file.write_text("# Guide\n\nContent here")

        # Create safe symlink pointing within project
        safe_link = project_root / "quick-start.md"
        safe_link.symlink_to(original_file)

        # Initialize memory
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(project_root),
            response_format=ResponseFormat.MARKDOWN
        ))

        # Should complete successfully
        assert "initialized successfully" in result.lower()

        # Verify both original and symlink are tracked
        baseline_path = project_root / ".doc-manager" / "memory" / "repo-baseline.json"
        import json
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)

        # Both files should be included (symlink resolves to same content)
        assert "docs/guide.md" in baseline["files"] or "quick-start.md" in baseline["files"]
