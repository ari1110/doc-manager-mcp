
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.tools.changes import _get_changed_files_from_git


class TestGitCommandConstruction:
    """Test git command construction uses secure array form."""

    @patch('src.tools.changes.run_git_command')
    def test_git_diff_uses_array_form(self, mock_run_git):
        """Test that git diff command is called with array form arguments."""
        mock_run_git.return_value = ""
        project_path = Path("/test/project")
        since_commit = "abc1234"

        _get_changed_files_from_git(project_path, since_commit)

        # Verify run_git_command was called with array form arguments
        mock_run_git.assert_called_once_with(
            project_path,
            "diff",
            "--name-status",
            since_commit,
            "HEAD"
        )

    @patch('src.tools.changes.run_git_command')
    def test_git_command_with_valid_commit_hash(self, mock_run_git):
        """Test git command with valid commit hash."""
        mock_run_git.return_value = "M\tsrc/test.py\nA\tdocs/new.md"
        project_path = Path("/test/project")

        # Valid short hash
        result = _get_changed_files_from_git(project_path, "abc1234")
        assert len(result) == 2
        assert mock_run_git.call_args[0][3] == "abc1234"  # Verify hash passed

        # Valid full hash
        full_hash = "a" * 40
        result = _get_changed_files_from_git(project_path, full_hash)
        assert mock_run_git.call_args[0][3] == full_hash

    @patch('src.tools.changes.run_git_command')
    def test_git_command_arguments_not_concatenated(self, mock_run_git):
        """Test that git arguments are passed separately, not as concatenated string."""
        mock_run_git.return_value = ""
        project_path = Path("/test/project")
        commit = "abc1234"

        _get_changed_files_from_git(project_path, commit)

        # Verify arguments are separate (array form), not concatenated
        call_args = mock_run_git.call_args[0]
        assert call_args[0] == project_path
        assert call_args[1] == "diff"
        assert call_args[2] == "--name-status"
        assert call_args[3] == commit
        assert call_args[4] == "HEAD"

        # Verify NOT called with concatenated string like "diff --name-status abc1234 HEAD"
        assert len(call_args) == 5  # project_path + 4 separate args

    @patch('src.tools.changes.run_git_command')
    def test_git_diff_output_parsing(self, mock_run_git):
        """Test parsing of git diff --name-status output."""
        # Mock git diff output
        mock_run_git.return_value = "M\tsrc/utils.py\nA\tsrc/new.py\nD\told/file.py\nR100\told/path.py\tnew/path.py"

        project_path = Path("/test/project")
        result = _get_changed_files_from_git(project_path, "abc1234")

        assert len(result) == 4
        assert result[0] == {"file": "src/utils.py", "change_type": "modified"}
        assert result[1] == {"file": "src/new.py", "change_type": "added"}
        assert result[2] == {"file": "old/file.py", "change_type": "deleted"}
        assert result[3] == {"file": "old/path.py", "change_type": "renamed"}

    @patch('src.tools.changes.run_git_command')
    def test_git_command_returns_none(self, mock_run_git):
        """Test handling when git command returns None (error case)."""
        mock_run_git.return_value = None

        project_path = Path("/test/project")
        result = _get_changed_files_from_git(project_path, "abc1234")

        # Should return empty list instead of crashing
        assert result == []

    @patch('src.tools.changes.run_git_command')
    def test_git_command_with_empty_output(self, mock_run_git):
        """Test handling of empty git diff output (no changes)."""
        mock_run_git.return_value = ""

        project_path = Path("/test/project")
        result = _get_changed_files_from_git(project_path, "abc1234")

        assert result == []

    @patch('src.tools.changes.run_git_command')
    def test_git_command_ignores_malformed_lines(self, mock_run_git):
        """Test that malformed git output lines are skipped gracefully."""
        # Mix of valid and malformed lines
        mock_run_git.return_value = "M\tsrc/valid.py\nMALFORMED LINE\n\nA\tsrc/another.py"

        project_path = Path("/test/project")
        result = _get_changed_files_from_git(project_path, "abc1234")

        # Should only include valid lines
        assert len(result) == 2
        assert result[0] == {"file": "src/valid.py", "change_type": "modified"}
        assert result[1] == {"file": "src/another.py", "change_type": "added"}


class TestRunGitCommandSecurity:
    """Test that run_git_command enforces security measures."""

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_run_git_command_uses_array_form(self, mock_which, mock_subprocess):
        """Test that run_git_command calls subprocess with array form."""
        from src.utils import run_git_command

        mock_which.return_value = "/usr/bin/git"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_subprocess.return_value = mock_result

        project_path = Path("/test")
        run_git_command(project_path, "status", "--short")

        # Verify subprocess.run called with array form: ["git", "status", "--short"]
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["git", "status", "--short"]

        # Verify NOT called with shell=True (which would enable injection)
        assert 'shell' not in call_args[1] or call_args[1]['shell'] is False

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_run_git_command_timeout_enforced(self, mock_which, mock_subprocess):
        """Test that git commands have 30-second timeout."""
        from src.utils import run_git_command

        mock_which.return_value = "/usr/bin/git"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_subprocess.return_value = mock_result

        project_path = Path("/test")
        run_git_command(project_path, "log")

        # Verify timeout=30 is passed
        call_args = mock_subprocess.call_args
        assert call_args[1]['timeout'] == 30
