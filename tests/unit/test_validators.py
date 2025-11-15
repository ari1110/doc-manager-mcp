"""Unit tests for Pydantic field validators (T020, T031 - US2, US1).

Tests input validation to prevent command injection and path traversal attacks.

@spec 001
@userStory US2, US1
@functionalReq FR-002, FR-001, FR-006
"""

import pytest
from pathlib import Path
from pydantic import ValidationError
from src.models import MapChangesInput, InitializeConfigInput
from src.constants import ResponseFormat, ChangeDetectionMode, DocumentationPlatform


class TestCommitHashValidator:
    """Test commit hash validation to prevent command injection."""

    def test_valid_short_commit_hash(self):
        """Test that valid short commit hashes (7 chars) are accepted."""
        valid_hashes = [
            "abc1234",
            "1234567",
            "ABCDEF0",
            "a1b2c3d",
        ]

        for commit_hash in valid_hashes:
            model = MapChangesInput(
                project_path="/test/path",
                since_commit=commit_hash,
                response_format=ResponseFormat.MARKDOWN
            )
            assert model.since_commit == commit_hash

    def test_valid_full_commit_hash(self):
        """Test that valid full commit hashes (40 chars) are accepted."""
        full_hash = "a" * 40  # 40 hex characters
        model = MapChangesInput(
            project_path="/test/path",
            since_commit=full_hash,
            response_format=ResponseFormat.MARKDOWN
        )
        assert model.since_commit == full_hash

    def test_none_commit_hash_accepted(self):
        """Test that None is accepted for optional since_commit."""
        model = MapChangesInput(
            project_path="/test/path",
            since_commit=None,
            response_format=ResponseFormat.MARKDOWN
        )
        assert model.since_commit is None

    def test_reject_shell_metacharacters(self):
        """Test that shell metacharacters are rejected (command injection prevention)."""
        malicious_inputs = [
            "HEAD; rm -rf /",  # Command separator
            "abc123 && ls",  # Command chaining
            "abc123 | cat",  # Pipe
            "$(whoami)",  # Command substitution
            "`whoami`",  # Backtick command substitution
            "abc123 > /tmp/exploit",  # Redirection
            "abc123\nrm -rf /",  # Newline injection
        ]

        for malicious in malicious_inputs:
            with pytest.raises(ValidationError) as exc_info:
                MapChangesInput(
                    project_path="/test/path",
                    since_commit=malicious,
                    response_format=ResponseFormat.MARKDOWN
                )

            error = exc_info.value
            assert "Invalid git commit hash format" in str(error)

    def test_reject_too_short_hash(self):
        """Test that commit hashes shorter than 7 characters are rejected."""
        short_hashes = ["a", "ab", "abc", "abc123"]  # <7 chars

        for short_hash in short_hashes:
            with pytest.raises(ValidationError) as exc_info:
                MapChangesInput(
                    project_path="/test/path",
                    since_commit=short_hash,
                    response_format=ResponseFormat.MARKDOWN
                )

            assert "Invalid git commit hash format" in str(exc_info.value)

    def test_reject_too_long_hash(self):
        """Test that commit hashes longer than 40 characters are rejected."""
        long_hash = "a" * 41  # 41 chars (too long for SHA-1)

        with pytest.raises(ValidationError) as exc_info:
            MapChangesInput(
                project_path="/test/path",
                since_commit=long_hash,
                response_format=ResponseFormat.MARKDOWN
            )

        assert "Invalid git commit hash format" in str(exc_info.value)

    def test_reject_non_hexadecimal(self):
        """Test that non-hexadecimal characters are rejected."""
        invalid_hashes = [
            "ghijklm",  # Contains g-m (not hex)
            "abc123z",  # Contains z (not hex)
            "abc-123",  # Contains dash
            "abc 123",  # Contains space
            "abc.123",  # Contains dot
        ]

        for invalid_hash in invalid_hashes:
            with pytest.raises(ValidationError) as exc_info:
                MapChangesInput(
                    project_path="/test/path",
                    since_commit=invalid_hash,
                    response_format=ResponseFormat.MARKDOWN
                )

            assert "Invalid git commit hash format" in str(exc_info.value)

    @pytest.mark.parametrize("length", [7, 8, 10, 20, 32, 40])
    def test_various_valid_lengths(self, length):
        """Test that various valid hash lengths (7-40) are accepted."""
        valid_hash = "a" * length
        model = MapChangesInput(
            project_path="/test/path",
            since_commit=valid_hash,
            response_format=ResponseFormat.MARKDOWN
        )
        assert model.since_commit == valid_hash

    def test_error_message_helpful(self):
        """Test that validation error messages are helpful."""
        with pytest.raises(ValidationError) as exc_info:
            MapChangesInput(
                project_path="/test/path",
                since_commit="invalid!",
                response_format=ResponseFormat.MARKDOWN
            )

        error_msg = str(exc_info.value)
        # Should mention the expected format
        assert "hexadecimal" in error_msg or "7-40" in error_msg
        # Should mention security reason
        assert "command injection" in error_msg.lower()


class TestPathTraversalValidator:
    """Test path traversal validation to prevent directory traversal attacks (T031 - US1)."""

    def test_reject_path_traversal_sequences(self, tmp_path):
        """Test that path traversal sequences are rejected (FR-001)."""
        # Create a valid directory
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        malicious_paths = [
            str(tmp_path / ".." / "etc" / "passwd"),
            str(tmp_path / "project" / ".." / ".." / "etc"),
            "../../../etc/passwd",
            "../../sensitive",
            str(project_dir / ".." / ".." / "escape"),
        ]

        for malicious in malicious_paths:
            with pytest.raises(ValidationError) as exc_info:
                InitializeConfigInput(
                    project_path=malicious,
                    response_format=ResponseFormat.MARKDOWN
                )

            error = exc_info.value
            assert "path traversal" in str(error).lower() or ".." in str(error), \
                f"Expected path traversal error for: {malicious}"

    def test_reject_relative_project_path(self, tmp_path):
        """Test that relative project paths are rejected (FR-006)."""
        relative_paths = [
            "relative/path",
            "./current/dir",
            "project",
        ]

        for rel_path in relative_paths:
            with pytest.raises(ValidationError) as exc_info:
                InitializeConfigInput(
                    project_path=rel_path,
                    response_format=ResponseFormat.MARKDOWN
                )

            assert "absolute" in str(exc_info.value).lower()

    def test_reject_nonexistent_project_path(self):
        """Test that non-existent project paths are rejected (FR-006)."""
        import platform

        # Use platform-specific absolute path
        if platform.system() == "Windows":
            nonexistent_path = "C:\\nonexistent\\project\\path"
        else:
            nonexistent_path = "/nonexistent/project/path"

        with pytest.raises(ValidationError) as exc_info:
            InitializeConfigInput(
                project_path=nonexistent_path,
                response_format=ResponseFormat.MARKDOWN
            )

        assert "does not exist" in str(exc_info.value).lower()

    def test_reject_file_as_project_path(self, tmp_path):
        """Test that files are rejected (only directories allowed) (FR-006)."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        with pytest.raises(ValidationError) as exc_info:
            InitializeConfigInput(
                project_path=str(file_path),
                response_format=ResponseFormat.MARKDOWN
            )

        assert "not a directory" in str(exc_info.value).lower()

    def test_accept_valid_absolute_path(self, tmp_path):
        """Test that valid absolute paths are accepted."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Should not raise ValidationError
        model = InitializeConfigInput(
            project_path=str(project_dir),
            response_format=ResponseFormat.MARKDOWN
        )

        # Path should be resolved to absolute
        assert Path(model.project_path).is_absolute()

    def test_docs_path_rejects_traversal(self, tmp_path):
        """Test that docs_path rejects path traversal sequences (FR-001)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        malicious_docs_paths = [
            "../escape",
            "../../etc",
            "docs/../../../etc",
        ]

        for malicious in malicious_docs_paths:
            with pytest.raises(ValidationError) as exc_info:
                InitializeConfigInput(
                    project_path=str(project_dir),
                    docs_path=malicious,
                    response_format=ResponseFormat.MARKDOWN
                )

            assert "path traversal" in str(exc_info.value).lower() or ".." in str(exc_info.value)

    def test_docs_path_rejects_absolute(self, tmp_path):
        """Test that docs_path rejects absolute paths (must be relative to project)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        absolute_docs_path = str(tmp_path / "other" / "docs")

        with pytest.raises(ValidationError) as exc_info:
            InitializeConfigInput(
                project_path=str(project_dir),
                docs_path=absolute_docs_path,
                response_format=ResponseFormat.MARKDOWN
            )

        assert "relative" in str(exc_info.value).lower()

    def test_docs_path_accepts_valid_relative(self, tmp_path):
        """Test that valid relative docs paths are accepted."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        valid_docs_paths = [
            "docs",
            "documentation",
            "docs/api",
            "website/docs",
        ]

        for docs_path in valid_docs_paths:
            # Should not raise ValidationError
            model = InitializeConfigInput(
                project_path=str(project_dir),
                docs_path=docs_path,
                response_format=ResponseFormat.MARKDOWN
            )

            # Normalize separators for comparison (Windows uses backslash)
            expected_normalized = str(Path(docs_path))
            assert model.docs_path == expected_normalized

    def test_docs_path_accepts_none(self, tmp_path):
        """Test that None is accepted for optional docs_path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        model = InitializeConfigInput(
            project_path=str(project_dir),
            docs_path=None,
            response_format=ResponseFormat.MARKDOWN
        )

        assert model.docs_path is None
