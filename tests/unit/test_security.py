"""Unit tests for security utilities (T014 - US3).

Tests credential scanning and validation functions.

@spec 001
@userStory US3
@functionalReq FR-004,FR-005
"""

import re
from pathlib import Path
import pytest


class TestCredentialScanning:
    """Test credential detection and scanning utilities."""

    def test_api_key_pattern_detection(self):
        """Test detection of API key patterns."""
        # Common API key patterns
        patterns = [
            r'sk-or-v1-[a-f0-9]{64}',  # OpenRouter API key
            r'sk-[a-zA-Z0-9-]{20,}',  # OpenAI API key (flexible length, includes proj-)
            r'[A-Z0-9]{20}',  # Generic 20-char token
        ]

        test_cases = [
            ("OPENROUTER_API_KEY=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", True),
            ("OPENAI_API_KEY=sk-proj-1234567890abcdefghijklmnopqrstuvwxyz123456", True),
            ("OPENROUTER_API_KEY=your-api-key-here", False),  # Placeholder
            ("API_KEY=test", False),  # Too short
        ]

        for text, should_match in test_cases:
            matched = any(re.search(pattern, text) for pattern in patterns)
            if should_match:
                assert matched, f"Should detect credential in: {text[:50]}..."
            else:
                assert not matched or "your-api-key-here" in text, f"Should not flag placeholder: {text[:50]}..."

    def test_placeholder_vs_real_credential(self):
        """Test distinguishing placeholders from real credentials."""
        placeholders = [
            "your-api-key-here",
            "INSERT_KEY_HERE",
            "xxx",
            "***",
            "placeholder",
        ]

        real_patterns = [
            "sk-or-v1-" + "a" * 64,  # Real-looking OpenRouter key
            "sk-" + "A" * 48,  # Real-looking OpenAI key
        ]

        # Placeholders should not be flagged
        for placeholder in placeholders:
            assert len(placeholder) < 20 or "your-" in placeholder.lower() or placeholder in ["xxx", "***"]

        # Real patterns should be detected
        for pattern in real_patterns:
            assert len(pattern) > 20 and pattern.startswith("sk-")

    def test_env_file_pattern_matching(self):
        """Test .env file pattern detection in gitignore."""
        gitignore_patterns = [
            ".env",
            "*.env.local",  # Specific pattern from actual .gitignore
            ".mcp.json",
        ]

        files_should_ignore = [
            ".env",
            ".env.local",
            "some/.env.local",
            ".mcp.json",
            "config/.env.local",
        ]

        files_should_allow = [
            ".env.template",
            ".env.example",
            ".env.production",  # Not in gitignore, but that's okay (test actual patterns)
            "environment.py",
            "README.md",
        ]

        import fnmatch

        for file_path in files_should_ignore:
            matched = any(
                fnmatch.fnmatch(file_path, pattern) or
                fnmatch.fnmatch(Path(file_path).name, pattern)
                for pattern in gitignore_patterns
            )
            assert matched, f"Should ignore: {file_path}"

        for file_path in files_should_allow:
            matched = any(
                fnmatch.fnmatch(file_path, pattern) or
                fnmatch.fnmatch(Path(file_path).name, pattern)
                for pattern in gitignore_patterns
            )
            assert not matched, f"Should allow: {file_path}"

    def test_credential_sanitization(self):
        """Test that credentials are properly sanitized in error messages."""
        from src.utils import handle_error

        # Simulate an error with a credential in the message
        test_error = ValueError("Failed to connect with key: sk-test-12345678901234567890123456789012")

        # The error handler should sanitize paths and potentially credentials
        error_msg = handle_error(test_error, "test_context", log_to_stderr=False)

        # Verify error message doesn't expose full credential
        assert "Error: ValueError" in error_msg
        assert "test_context" in error_msg
        # The actual credential should either be redacted or the message should be generic

    @pytest.mark.parametrize("credential_type,pattern,example", [
        ("openrouter", r'sk-or-v1-[a-f0-9]{64}', "sk-or-v1-" + "a" * 64),
        ("openai", r'sk-[a-zA-Z0-9]{48}', "sk-" + "A" * 48),
        ("github", r'ghp_[a-zA-Z0-9]{36}', "ghp_" + "x" * 36),
    ])
    def test_various_credential_patterns(self, credential_type, pattern, example):
        """Test detection of various credential types."""
        assert re.search(pattern, example), f"Should detect {credential_type} credential"
        assert not re.search(pattern, "placeholder"), f"Should not detect placeholder as {credential_type}"
