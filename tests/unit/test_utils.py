"""Unit tests for utility functions."""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.utils import (
    calculate_checksum,
    detect_project_language,
    find_docs_directory,
    handle_error,
    validate_path_boundary,
    safe_json_dumps,
    enforce_response_limit
)


class TestCalculateChecksum:
    """Tests for calculate_checksum function."""

    """
    @spec 001
    @testType unit
    """
    def test_checksum_consistency(self, tmp_path):
        """Test that same content produces same checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        checksum1 = calculate_checksum(test_file)
        checksum2 = calculate_checksum(test_file)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 hex length

    """
    @spec 001
    @testType unit
    """
    def test_checksum_different_content(self, tmp_path):
        """Test that different content produces different checksums."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        checksum1 = calculate_checksum(file1)
        checksum2 = calculate_checksum(file2)

        assert checksum1 != checksum2

    """
    @spec 001
    @testType unit
    """
    def test_checksum_nonexistent_file(self, tmp_path):
        """Test checksum of nonexistent file returns empty string."""
        nonexistent = tmp_path / "nonexistent.txt"
        checksum = calculate_checksum(nonexistent)

        assert checksum == ""


class TestDetectProjectLanguage:
    """Tests for detect_project_language function."""

    """
    @spec 001
    @testType unit
    """
    def test_detect_go(self, tmp_path):
        """Test Go project detection."""
        (tmp_path / "go.mod").write_text("module example.com/project")
        language = detect_project_language(tmp_path)
        assert language == "Go"

    """
    @spec 001
    @testType unit
    """
    def test_detect_python_requirements(self, tmp_path):
        """Test Python project detection via requirements.txt."""
        (tmp_path / "requirements.txt").write_text("pytest==7.0.0")
        language = detect_project_language(tmp_path)
        assert language == "Python"

    """
    @spec 001
    @testType unit
    """
    def test_detect_python_setup(self, tmp_path):
        """Test Python project detection via setup.py."""
        (tmp_path / "setup.py").write_text("from setuptools import setup")
        language = detect_project_language(tmp_path)
        assert language == "Python"

    """
    @spec 001
    @testType unit
    """
    def test_detect_javascript(self, tmp_path):
        """Test JavaScript project detection."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        language = detect_project_language(tmp_path)
        assert language == "JavaScript/TypeScript"

    """
    @spec 001
    @testType unit
    """
    def test_detect_rust(self, tmp_path):
        """Test Rust project detection."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')
        language = detect_project_language(tmp_path)
        assert language == "Rust"

    """
    @spec 001
    @testType unit
    """
    def test_detect_java_maven(self, tmp_path):
        """Test Java project detection via pom.xml."""
        (tmp_path / "pom.xml").write_text('<project></project>')
        language = detect_project_language(tmp_path)
        assert language == "Java"

    """
    @spec 001
    @testType unit
    """
    def test_detect_java_gradle(self, tmp_path):
        """Test Java project detection via build.gradle."""
        (tmp_path / "build.gradle").write_text('plugins {}')
        language = detect_project_language(tmp_path)
        assert language == "Java"

    """
    @spec 001
    @testType unit
    """
    def test_detect_ruby(self, tmp_path):
        """Test Ruby project detection."""
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"')
        language = detect_project_language(tmp_path)
        assert language == "Ruby"

    """
    @spec 001
    @testType unit
    """
    def test_detect_php(self, tmp_path):
        """Test PHP project detection."""
        (tmp_path / "composer.json").write_text('{"require": {}}')
        language = detect_project_language(tmp_path)
        assert language == "PHP"

    """
    @spec 001
    @testType unit
    """
    def test_detect_unknown(self, tmp_path):
        """Test unknown project returns 'Unknown'."""
        language = detect_project_language(tmp_path)
        assert language == "Unknown"


class TestFindDocsDirectory:
    """Tests for find_docs_directory function."""

    """
    @spec 001
    @testType unit
    """
    def test_find_docs(self, tmp_path):
        """Test finding 'docs' directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == docs_dir

    """
    @spec 001
    @testType unit
    """
    def test_find_doc(self, tmp_path):
        """Test finding 'doc' directory."""
        doc_dir = tmp_path / "doc"
        doc_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    """
    @spec 001
    @testType unit
    """
    def test_find_documentation(self, tmp_path):
        """Test finding 'documentation' directory."""
        doc_dir = tmp_path / "documentation"
        doc_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    """
    @spec 001
    @testType unit
    """
    def test_find_docsite(self, tmp_path):
        """Test finding 'docsite' directory."""
        doc_dir = tmp_path / "docsite"
        doc_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    """
    @spec 001
    @testType unit
    """
    def test_find_website_docs(self, tmp_path):
        """Test finding 'website/docs' directory."""
        doc_dir = tmp_path / "website" / "docs"
        doc_dir.mkdir(parents=True)
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    """
    @spec 001
    @testType unit
    """
    def test_priority_order(self, tmp_path):
        """Test that 'docs' takes priority over other names."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "documentation").mkdir()
        found = find_docs_directory(tmp_path)
        assert found.name == "docs"

    """
    @spec 001
    @testType unit
    """
    def test_no_docs_directory(self, tmp_path):
        """Test returns None when no docs directory found."""
        found = find_docs_directory(tmp_path)
        assert found is None


class TestHandleError:
    """Tests for handle_error function."""

    """
    @spec 001
    @testType unit
    """
    def test_handle_error_with_context(self):
        """Test error handling with context."""
        error = ValueError("test error")
        result = handle_error(error, "test_function")

        assert "Error: ValueError" in result
        assert "test_function" in result
        assert "test error" in result

    """
    @spec 001
    @testType unit
    """
    def test_handle_error_without_context(self):
        """Test error handling without context."""
        error = ValueError("test error")
        result = handle_error(error)

        assert "Error: ValueError" in result
        assert "test error" in result

    """
    @spec 001
    @testType unit
    """
    def test_handle_different_exception_types(self):
        """Test handling different exception types."""
        exceptions = [
            ValueError("value error"),
            TypeError("type error"),
            FileNotFoundError("file not found"),
            RuntimeError("runtime error")
        ]

        for exc in exceptions:
            result = handle_error(exc, "test")
            assert exc.__class__.__name__ in result
            assert str(exc) in result


class TestValidatePathBoundary:
    """Tests for validate_path_boundary function (T032 - US1).

    @spec 001
    @userStory US1
    @functionalReq FR-001, FR-003, FR-025, FR-028
    """

    def test_path_within_boundary(self, tmp_path):
        """Test that paths within project boundary are accepted (FR-025)."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        file_path = project_root / "file.txt"
        file_path.write_text("content")

        # Should not raise ValueError
        result = validate_path_boundary(file_path, project_root)

        assert result.is_absolute()
        assert result.is_relative_to(project_root)

    def test_reject_path_escaping_boundary(self, tmp_path):
        """Test that paths escaping project boundary are rejected (FR-001, FR-025)."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Path outside project
        outside_path = tmp_path / "outside" / "file.txt"
        outside_path.parent.mkdir()
        outside_path.write_text("content")

        with pytest.raises(ValueError) as exc_info:
            validate_path_boundary(outside_path, project_root)

        assert "escapes project boundary" in str(exc_info.value).lower()

    def test_reject_malicious_symlink(self, tmp_path):
        """Test that symlinks escaping boundary are rejected (FR-003, FR-028)."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create target outside project
        outside_target = tmp_path / "outside" / "secret.txt"
        outside_target.parent.mkdir()
        outside_target.write_text("secret data")

        # Create symlink inside project pointing outside
        symlink_path = project_root / "link_to_secret"
        symlink_path.symlink_to(outside_target)

        with pytest.raises(ValueError) as exc_info:
            validate_path_boundary(symlink_path, project_root)

        error_msg = str(exc_info.value).lower()
        assert "symlink" in error_msg and "escapes" in error_msg

    def test_accept_safe_symlink(self, tmp_path):
        """Test that symlinks within boundary are accepted (FR-028)."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create target inside project
        target_file = project_root / "target.txt"
        target_file.write_text("content")

        # Create symlink inside project pointing to another file inside project
        symlink_path = project_root / "link"
        symlink_path.symlink_to(target_file)

        # Should not raise ValueError
        result = validate_path_boundary(symlink_path, project_root)

        assert result.is_absolute()
        assert result.is_relative_to(project_root)

    def test_nested_path_within_boundary(self, tmp_path):
        """Test deeply nested paths within boundary are accepted."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create deeply nested path
        nested_path = project_root / "a" / "b" / "c" / "d" / "file.txt"
        nested_path.parent.mkdir(parents=True)
        nested_path.write_text("content")

        result = validate_path_boundary(nested_path, project_root)

        assert result.is_absolute()
        assert result.is_relative_to(project_root)

    def test_resolve_relative_path(self, tmp_path):
        """Test that relative paths are resolved correctly."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        file_path = project_root / "file.txt"
        file_path.write_text("content")

        # Use a Path without calling resolve()
        unresolved_path = Path(str(file_path))

        result = validate_path_boundary(unresolved_path, project_root)

        # Result should be absolute
        assert result.is_absolute()
        assert result == file_path.resolve()

    def test_symlink_chain_escaping_boundary(self, tmp_path):
        """Test that symlink chains escaping boundary are rejected."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create target outside project
        outside_target = tmp_path / "outside" / "secret.txt"
        outside_target.parent.mkdir()
        outside_target.write_text("secret")

        # Create intermediate symlink outside project
        intermediate_link = tmp_path / "outside" / "link1"
        intermediate_link.symlink_to(outside_target)

        # Create symlink inside project pointing to intermediate
        symlink_path = project_root / "link2"
        symlink_path.symlink_to(intermediate_link)

        with pytest.raises(ValueError) as exc_info:
            validate_path_boundary(symlink_path, project_root)

        assert "symlink" in str(exc_info.value).lower()


class TestSafeJsonDumps:
    """Tests for safe_json_dumps function (T055 - US4)."""

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-012
    """
    def test_serializes_valid_dict(self):
        """Test that valid dictionaries are serialized normally."""
        data = {"status": "success", "count": 42, "items": ["a", "b", "c"]}
        result = safe_json_dumps(data, indent=2)

        assert '"status": "success"' in result
        assert '"count": 42' in result
        assert result.startswith("{")
        assert result.endswith("}")

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-012
    """
    def test_handles_unserializable_datetime(self):
        """Test that datetime objects cause graceful error (T055 - FR-012)."""
        from datetime import datetime

        data = {"timestamp": datetime.now(), "message": "test"}

        result = safe_json_dumps(data)

        # Should return error JSON instead of crashing
        assert '"status": "error"' in result
        assert '"message": "JSON serialization error"' in result
        assert "not JSON serializable" in result or "Object of type" in result

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-012
    """
    def test_handles_unserializable_path(self):
        """Test that Path objects cause graceful error (FR-012)."""
        from pathlib import Path

        data = {"path": Path("/tmp/test"), "status": "ok"}

        result = safe_json_dumps(data)

        # Should return error JSON
        assert '"status": "error"' in result
        assert '"message": "JSON serialization error"' in result

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-012
    """
    def test_handles_custom_class(self):
        """Test that custom class instances cause graceful error."""
        class CustomClass:
            def __init__(self):
                self.value = 42

        data = {"custom": CustomClass(), "message": "test"}

        result = safe_json_dumps(data)

        # Should return error JSON
        assert '"status": "error"' in result
        assert "JSON serialization error" in result

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-012
    """
    def test_preserves_indent_parameter(self):
        """Test that indent parameter is passed through correctly."""
        data = {"a": 1, "b": 2}

        result_no_indent = safe_json_dumps(data)
        result_with_indent = safe_json_dumps(data, indent=2)

        # Indented version should have newlines
        assert "\n" in result_with_indent
        assert len(result_with_indent) > len(result_no_indent)

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-012
    """
    def test_handles_nested_unserializable(self):
        """Test handling of unserializable objects nested in data structure."""
        from datetime import datetime

        data = {
            "status": "ok",
            "nested": {
                "timestamp": datetime.now(),
                "count": 5
            }
        }

        result = safe_json_dumps(data)

        # Should detect error in nested structure
        assert '"status": "error"' in result


class TestErrorMessageSanitization:
    """Tests for error message sanitization (T069 - US6)."""

    """
    @spec 001
    @testType unit
    @userStory US6
    @functionalReq FR-017
    """
    def test_sanitizes_windows_paths(self):
        """Test that Windows paths are removed from error messages."""
        error = ValueError("File not found: C:\\Users\\username\\project\\file.txt")
        result = handle_error(error, "test", log_to_stderr=False)

        assert "C:\\Users\\username\\project\\file.txt" not in result
        assert "[path]" in result

    """
    @spec 001
    @testType unit
    @userStory US6
    @functionalReq FR-017
    """
    def test_sanitizes_unix_paths(self):
        """Test that Unix paths are removed from error messages."""
        error = FileNotFoundError("/home/user/project/src/file.py")
        result = handle_error(error, "test", log_to_stderr=False)

        assert "/home/user/project" not in result
        assert "[path]" in result

    """
    @spec 001
    @testType unit
    @userStory US6
    @functionalReq FR-017
    """
    def test_preserves_error_type_and_context(self):
        """Test that error type and context are preserved."""
        error = ValueError("Invalid input")
        result = handle_error(error, "config_init", log_to_stderr=False)

        assert "ValueError" in result
        assert "config_init" in result
        assert "Invalid input" in result


class TestEnforceResponseLimit:
    """Tests for enforce_response_limit function (T055 - US4)."""

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-010
    """
    def test_short_response_unchanged(self):
        """Test that responses under limit are returned unchanged."""
        short_response = "This is a short response"
        result = enforce_response_limit(short_response)

        assert result == short_response
        assert "truncated" not in result.lower()

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-010
    """
    def test_long_response_truncated(self):
        """Test that responses over 25K are truncated."""
        # Create response longer than 25K chars
        long_response = "A" * 30000

        result = enforce_response_limit(long_response)

        assert len(result) <= 25000
        assert "truncated" in result.lower()
        assert "25,000 character limit" in result

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-010
    """
    def test_truncation_includes_helpful_tip(self):
        """Test that truncated responses include helpful tip."""
        long_response = "X" * 26000

        result = enforce_response_limit(long_response)

        assert "Tip:" in result or "reduce output" in result.lower()

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-010
    """
    def test_custom_limit_parameter(self):
        """Test that custom limit parameter works."""
        response = "A" * 1000

        # Use smaller custom limit
        result = enforce_response_limit(response, limit=500)

        assert len(result) <= 500
        assert "truncated" in result.lower()

    """
    @spec 001
    @testType unit
    @userStory US4
    @functionalReq FR-010
    """
    def test_exactly_at_limit_not_truncated(self):
        """Test that response exactly at limit is not truncated."""
        response = "B" * 25000

        result = enforce_response_limit(response)

        assert result == response
        assert "truncated" not in result.lower()
