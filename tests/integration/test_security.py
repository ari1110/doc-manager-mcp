"""Integration tests for security features (T015 - US3).

Tests that gitignore properly excludes sensitive files and that
the repository doesn't contain exposed credentials.

@spec 001
@userStory US3
@functionalReq FR-004,FR-005
"""

import subprocess
from pathlib import Path
import pytest


class TestGitignoreCredentialProtection:
    """Test that gitignore protects sensitive credential files."""

    def test_gitignore_excludes_mcp_json(self, tmp_path):
        """Test that .gitignore excludes .mcp.json files."""
        # Read actual .gitignore
        gitignore_path = Path(__file__).parent.parent.parent / ".gitignore"
        assert gitignore_path.exists(), ".gitignore file must exist"

        gitignore_content = gitignore_path.read_text()

        # Verify .mcp.json is in .gitignore
        assert ".mcp.json" in gitignore_content, ".mcp.json must be in .gitignore (FR-005)"

    def test_gitignore_excludes_env_files(self, tmp_path):
        """Test that .gitignore excludes .env files."""
        gitignore_path = Path(__file__).parent.parent.parent / ".gitignore"
        gitignore_content = gitignore_path.read_text()

        # Verify .env patterns are in .gitignore
        assert ".env" in gitignore_content, ".env must be in .gitignore (FR-005)"
        assert "*.env.local" in gitignore_content or ".env.local" in gitignore_content, \
            ".env.local pattern must be in .gitignore"

    def test_mcp_json_not_tracked_with_credentials(self):
        """Test that .mcp.json doesn't contain real credentials if tracked."""
        mcp_json_path = Path(__file__).parent.parent.parent / ".mcp.json"

        if mcp_json_path.exists():
            content = mcp_json_path.read_text()

            # Should not contain real API keys (SC-003)
            real_key_patterns = [
                r'sk-or-v1-[a-f0-9]{64}',  # Real OpenRouter key format
                r'sk-[a-zA-Z0-9]{48}',  # Real OpenAI key format
            ]

            import re
            for pattern in real_key_patterns:
                matches = re.findall(pattern, content)
                assert len(matches) == 0, \
                    f"Found real API key pattern in .mcp.json: {pattern} (SC-003 violation)"

            # Should contain placeholders instead
            assert "your-api-key-here" in content or "placeholder" in content.lower() or \
                   "INSERT" in content or "xxx" in content, \
                   ".mcp.json should use placeholders for credentials"

    def test_env_template_exists(self):
        """Test that .env.template exists for documentation."""
        template_path = Path(__file__).parent.parent.parent / ".env.template"
        assert template_path.exists(), ".env.template must exist (T011)"

        content = template_path.read_text()
        # Should document the expected variables
        assert "OPENROUTER_API_KEY" in content or "API_KEY" in content, \
            ".env.template should document required variables"
        # Should contain guidance
        assert "your-" in content.lower() or "placeholder" in content.lower() or \
               "template" in content.lower(), \
            ".env.template should provide guidance"

    def test_no_credentials_in_git_tracked_files(self):
        """Test that git-tracked files don't contain credentials (SC-003)."""
        try:
            # Get list of tracked files
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=Path(__file__).parent.parent.parent
            )

            if result.returncode != 0:
                pytest.skip("Not a git repository or git not available")

            tracked_files = result.stdout.strip().split('\n')

            # Patterns that indicate real credentials (not placeholders)
            credential_patterns = [
                r'sk-or-v1-[a-f0-9]{64}',  # OpenRouter
                r'sk-[a-zA-Z0-9]{48}',  # OpenAI
                r'ghp_[a-zA-Z0-9]{36}',  # GitHub PAT
            ]

            repo_root = Path(__file__).parent.parent.parent
            import re

            for file_path in tracked_files:
                if file_path.endswith(('.pyc', '.png', '.jpg', '.gif', '.ico', '.lock')):
                    continue  # Skip binary and lock files

                full_path = repo_root / file_path
                if not full_path.exists() or not full_path.is_file():
                    continue

                try:
                    content = full_path.read_text(encoding='utf-8', errors='ignore')

                    for pattern in credential_patterns:
                        matches = re.findall(pattern, content)
                        if matches:
                            # Filter out known placeholders/test data
                            real_matches = [m for m in matches if not any(
                                placeholder in content[max(0, content.index(m)-50):content.index(m)+len(m)+50]
                                for placeholder in ["your-", "placeholder", "example", "test", "xxx", "INSERT"]
                            )]

                            assert len(real_matches) == 0, \
                                f"Found potential real credential in tracked file {file_path}: {pattern}"

                except (UnicodeDecodeError, PermissionError):
                    continue  # Skip files that can't be read as text

        except FileNotFoundError:
            pytest.skip("Git not available")

    def test_git_status_respects_gitignore(self):
        """Test that git status doesn't show ignored credential files."""
        try:
            # Check if .mcp.json or .env would show up in git status if they existed
            result = subprocess.run(
                ["git", "status", "--porcelain", "--ignored"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=Path(__file__).parent.parent.parent
            )

            if result.returncode != 0:
                pytest.skip("Not a git repository")

            status_output = result.stdout

            # If .mcp.json exists, it should be marked as ignored (!! prefix)
            mcp_json_path = Path(__file__).parent.parent.parent / ".mcp.json"
            if mcp_json_path.exists():
                # Should either not appear or appear as ignored
                if ".mcp.json" in status_output:
                    assert "!! .mcp.json" in status_output, \
                        ".mcp.json should be ignored by git (SC-004)"

        except FileNotFoundError:
            pytest.skip("Git not available")
