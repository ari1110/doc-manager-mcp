"""Unit tests for utility functions."""

import pytest
from pathlib import Path
import tempfile
import shutil

from src.utils import (
    calculate_checksum,
    detect_project_language,
    find_docs_directory,
    handle_error
)


class TestCalculateChecksum:
    """Tests for calculate_checksum function."""

    def test_checksum_consistency(self, tmp_path):
        """Test that same content produces same checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        checksum1 = calculate_checksum(test_file)
        checksum2 = calculate_checksum(test_file)

        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 hex length

    def test_checksum_different_content(self, tmp_path):
        """Test that different content produces different checksums."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content A")
        file2.write_text("Content B")

        checksum1 = calculate_checksum(file1)
        checksum2 = calculate_checksum(file2)

        assert checksum1 != checksum2

    def test_checksum_nonexistent_file(self, tmp_path):
        """Test checksum of nonexistent file returns empty string."""
        nonexistent = tmp_path / "nonexistent.txt"
        checksum = calculate_checksum(nonexistent)

        assert checksum == ""


class TestDetectProjectLanguage:
    """Tests for detect_project_language function."""

    def test_detect_go(self, tmp_path):
        """Test Go project detection."""
        (tmp_path / "go.mod").write_text("module example.com/project")
        language = detect_project_language(tmp_path)
        assert language == "Go"

    def test_detect_python_requirements(self, tmp_path):
        """Test Python project detection via requirements.txt."""
        (tmp_path / "requirements.txt").write_text("pytest==7.0.0")
        language = detect_project_language(tmp_path)
        assert language == "Python"

    def test_detect_python_setup(self, tmp_path):
        """Test Python project detection via setup.py."""
        (tmp_path / "setup.py").write_text("from setuptools import setup")
        language = detect_project_language(tmp_path)
        assert language == "Python"

    def test_detect_javascript(self, tmp_path):
        """Test JavaScript project detection."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        language = detect_project_language(tmp_path)
        assert language == "JavaScript/TypeScript"

    def test_detect_rust(self, tmp_path):
        """Test Rust project detection."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')
        language = detect_project_language(tmp_path)
        assert language == "Rust"

    def test_detect_java_maven(self, tmp_path):
        """Test Java project detection via pom.xml."""
        (tmp_path / "pom.xml").write_text('<project></project>')
        language = detect_project_language(tmp_path)
        assert language == "Java"

    def test_detect_java_gradle(self, tmp_path):
        """Test Java project detection via build.gradle."""
        (tmp_path / "build.gradle").write_text('plugins {}')
        language = detect_project_language(tmp_path)
        assert language == "Java"

    def test_detect_ruby(self, tmp_path):
        """Test Ruby project detection."""
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"')
        language = detect_project_language(tmp_path)
        assert language == "Ruby"

    def test_detect_php(self, tmp_path):
        """Test PHP project detection."""
        (tmp_path / "composer.json").write_text('{"require": {}}')
        language = detect_project_language(tmp_path)
        assert language == "PHP"

    def test_detect_unknown(self, tmp_path):
        """Test unknown project returns 'Unknown'."""
        language = detect_project_language(tmp_path)
        assert language == "Unknown"


class TestFindDocsDirectory:
    """Tests for find_docs_directory function."""

    def test_find_docs(self, tmp_path):
        """Test finding 'docs' directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == docs_dir

    def test_find_doc(self, tmp_path):
        """Test finding 'doc' directory."""
        doc_dir = tmp_path / "doc"
        doc_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    def test_find_documentation(self, tmp_path):
        """Test finding 'documentation' directory."""
        doc_dir = tmp_path / "documentation"
        doc_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    def test_find_docsite(self, tmp_path):
        """Test finding 'docsite' directory."""
        doc_dir = tmp_path / "docsite"
        doc_dir.mkdir()
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    def test_find_website_docs(self, tmp_path):
        """Test finding 'website/docs' directory."""
        doc_dir = tmp_path / "website" / "docs"
        doc_dir.mkdir(parents=True)
        found = find_docs_directory(tmp_path)
        assert found == doc_dir

    def test_priority_order(self, tmp_path):
        """Test that 'docs' takes priority over other names."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "documentation").mkdir()
        found = find_docs_directory(tmp_path)
        assert found.name == "docs"

    def test_no_docs_directory(self, tmp_path):
        """Test returns None when no docs directory found."""
        found = find_docs_directory(tmp_path)
        assert found is None


class TestHandleError:
    """Tests for handle_error function."""

    def test_handle_error_with_context(self):
        """Test error handling with context."""
        error = ValueError("test error")
        result = handle_error(error, "test_function")

        assert "Error: ValueError" in result
        assert "test_function" in result
        assert "test error" in result

    def test_handle_error_without_context(self):
        """Test error handling without context."""
        error = ValueError("test error")
        result = handle_error(error)

        assert "Error: ValueError" in result
        assert "test error" in result

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
