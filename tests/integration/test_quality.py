"""Integration tests for quality assessment."""

import pytest
from pathlib import Path
from unittest.mock import patch
import sys
from io import StringIO

from src.models import AssessQualityInput
from src.constants import ResponseFormat
from src.tools.quality import assess_quality, _format_quality_report, _calculate_overall_score


@pytest.mark.asyncio
class TestQualityAssessment:
    """Integration tests for quality assessment."""

    async def test_assess_high_quality_docs(self, tmp_path):
        """Test assessing high-quality documentation."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create well-structured documentation
        (docs_dir / "index.md").write_text("""
# Project Documentation

Welcome to our comprehensive project documentation.

## Overview

This project provides tools for documentation management.

## Quick Start

Follow these steps to get started:

1. Install the package
2. Initialize configuration
3. Generate documentation
""")

        (docs_dir / "api.md").write_text("""
# API Reference

## Functions

### initialize_config

Initializes project configuration.

**Parameters:**
- `project_path` (str): Path to project directory
- `platform` (str): Documentation platform to use

**Returns:**
- str: Success message

**Example:**
```python
result = initialize_config("/path/to/project", "mkdocs")
```
""")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "quality assessment" in result.lower()
        # Should have good scores
        assert "excellent" in result.lower() or "good" in result.lower()
    async def test_assess_relevance_criterion(self, tmp_path):
        """Test relevance assessment."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create docs with irrelevant content
        (docs_dir / "random.md").write_text("""
# Random Thoughts

This is just random content that doesn't relate to the project.
Here are my favorite recipes and vacation photos.
""")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "relevance" in result.lower()
    async def test_assess_accuracy_criterion(self, tmp_path):
        """Test accuracy assessment."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create docs with broken references
        (docs_dir / "guide.md").write_text("""
# Installation Guide

Run this command:
```
npm install nonexistent-package
```

Configure the `missing_file.conf` file.
Reference the `UndefinedFunction()` API.
""")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "accuracy" in result.lower()
    async def test_assess_purposefulness_criterion(self, tmp_path):
        """Test purposefulness assessment."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create docs with clear purpose
        (docs_dir / "tutorial.md").write_text("""
# Getting Started Tutorial

**Goal:** Learn how to set up and use the doc-manager tool.

By the end of this tutorial, you will:
- Have a working installation
- Understand core concepts
- Be able to generate documentation

## Prerequisites

Before starting, ensure you have Python 3.10+.

## Step 1: Installation
...
""")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "purposefulness" in result.lower()
    async def test_assess_uniqueness_criterion(self, tmp_path):
        """Test uniqueness assessment (duplicate content detection)."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        duplicate_content = """
# Installation

To install, run:
```
pip install doc-manager
```

Then configure your project.
"""

        # Create duplicate content
        (docs_dir / "install1.md").write_text(duplicate_content)
        (docs_dir / "install2.md").write_text(duplicate_content)

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "uniqueness" in result.lower()
        assert "duplicate" in result.lower()
    async def test_assess_consistency_criterion(self, tmp_path):
        """Test consistency assessment."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create inconsistent documentation
        (docs_dir / "page1.md").write_text("""
# Page One

Use `snake_case` for variables.
Run command: `npm install`
""")

        (docs_dir / "page2.md").write_text("""
# Page Two

Use `camelCase` for variables.
Run command: `yarn add`
""")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "consistency" in result.lower()
    async def test_assess_clarity_criterion(self, tmp_path):
        """Test clarity assessment."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create unclear documentation
        (docs_dir / "unclear.md").write_text("""
# Thing

Do the stuff with the thing and then make it work.
You know what I mean. Just configure it properly.
See that file over there? Update it accordingly.
""")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "clarity" in result.lower()
    async def test_assess_structure_criterion(self, tmp_path):
        """Test structure assessment."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create well-structured docs
        (docs_dir / "index.md").write_text("# Home\n\nWelcome")
        (docs_dir / "guide.md").write_text("# Guide\n\n## Section 1\n\n## Section 2")

        guides_dir = docs_dir / "guides"
        guides_dir.mkdir()
        (guides_dir / "advanced.md").write_text("# Advanced Guide")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "structure" in result.lower()

    async def test_json_output_format(self, tmp_path):
        """Test JSON output format."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "index.md").write_text("# Index")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.JSON
        ))

        assert '"criteria":' in result
        assert '"score":' in result
        assert '"findings":' in result

    async def test_all_criteria_present(self, tmp_path):
        """Test that all 7 criteria are assessed."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("# Test Documentation\n\nContent here.")

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Check all 7 criteria are mentioned
        criteria = [
            "relevance",
            "accuracy",
            "purposefulness",
            "uniqueness",
            "consistency",
            "clarity",
            "structure"
        ]

        for criterion in criteria:
            assert criterion.lower() in result.lower(), f"Missing criterion: {criterion}"

    async def test_empty_docs_directory(self, tmp_path):
        """Test assessment of empty docs directory."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "no files" in result.lower() or "empty" in result.lower()

    async def test_nonexistent_docs_path(self, tmp_path):
        """Test error handling for nonexistent docs path."""
        result = await assess_quality(AssessQualityInput(
            project_path=str(tmp_path),
            docs_path="nonexistent",
            response_format=ResponseFormat.MARKDOWN
        ))

        assert "Error" in result or "not found" in result.lower()


@pytest.mark.asyncio
class TestQualityScoreEdgeCases:

    async def test_invalid_score_logs_warning(self, tmp_path):
        """Test that invalid scores log warnings to stderr and use default."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("# Test\n\nContent here.")

        # Create mock results with invalid score
        mock_results = [
            {
                "criterion": "relevance",
                "score": "invalid_score",  # Invalid score value
                "findings": ["Test finding"],
                "issues": [],
                "metrics": {}
            },
            {
                "criterion": "accuracy",
                "score": "good",
                "findings": [],
                "issues": [],
                "metrics": {}
            }
        ]

        # Capture stderr
        stderr_capture = StringIO()
        original_stderr = sys.stderr

        try:
            sys.stderr = stderr_capture

            # Call _calculate_overall_score which should log the warning
            overall = _calculate_overall_score(mock_results)

            # Restore stderr to read the captured content
            sys.stderr = original_stderr
            stderr_output = stderr_capture.getvalue()

            # Verify warning was logged to stderr
            assert "Warning: Invalid quality score 'invalid_score' for relevance" in stderr_output
            assert "using default 2 (fair)" in stderr_output

            # Verify the calculation still works (invalid score defaults to 2/fair)
            # (2 + 3) / 2 = 2.5 = "good"
            assert overall == "good"

        finally:
            sys.stderr = original_stderr

    async def test_missing_score_displays_na(self, tmp_path):
        """Test that missing scores display as N/A and log warnings."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("# Test\n\nContent here.")

        # Create mock results with missing score (key not present)
        mock_results = [
            {
                "criterion": "relevance",
                # score key completely missing to trigger N/A default
                "findings": ["Test finding"],
                "issues": [],
                "metrics": {}
            },
            {
                "criterion": "accuracy",
                "score": "good",
                "findings": [],
                "issues": [],
                "metrics": {}
            }
        ]

        # Capture stderr
        stderr_capture = StringIO()
        original_stderr = sys.stderr

        try:
            sys.stderr = stderr_capture

            # Format the report which should handle missing scores
            report = _format_quality_report(mock_results, ResponseFormat.MARKDOWN)

            # Restore stderr to read the captured content
            sys.stderr = original_stderr
            stderr_output = stderr_capture.getvalue()

            # Verify warning was logged for missing score in summary
            # (empty score is treated as missing in the summary loop)
            assert "Warning: Missing quality score for relevance, skipping in summary" in stderr_output

            # Verify warning was logged for missing score in display
            # (when get() returns default 'N/A', it triggers the warning)
            assert "Warning: Missing quality score for relevance, displaying as N/A" in stderr_output

            # Verify N/A appears in the report
            assert "**Score:** N/A" in report
            assert "## Relevance" in report

        finally:
            sys.stderr = original_stderr

    async def test_valid_scores_work_correctly(self, tmp_path):
        """Test that valid scores work correctly without warnings."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "test.md").write_text("# Test\n\nContent here.")

        # Create mock results with all valid scores
        mock_results = [
            {
                "criterion": "relevance",
                "score": "excellent",
                "findings": ["Test finding"],
                "issues": [],
                "metrics": {}
            },
            {
                "criterion": "accuracy",
                "score": "good",
                "findings": [],
                "issues": [],
                "metrics": {}
            },
            {
                "criterion": "purposefulness",
                "score": "fair",
                "findings": [],
                "issues": [],
                "metrics": {}
            },
            {
                "criterion": "uniqueness",
                "score": "poor",
                "findings": [],
                "issues": [],
                "metrics": {}
            }
        ]

        # Capture stderr
        stderr_capture = StringIO()
        original_stderr = sys.stderr

        try:
            sys.stderr = stderr_capture

            # Calculate overall score and format report
            overall = _calculate_overall_score(mock_results)
            report = _format_quality_report(mock_results, ResponseFormat.MARKDOWN)

            # Restore stderr to read the captured content
            sys.stderr = original_stderr
            stderr_output = stderr_capture.getvalue()

            # Verify NO warnings were logged
            assert "Warning" not in stderr_output

            # Verify scores are calculated correctly
            # excellent=4, good=3, fair=2, poor=1 -> (4+3+2+1)/4 = 2.5 = "good"
            assert overall == "good"

            # Verify all scores appear correctly in the report
            assert "**Score:** EXCELLENT" in report
            assert "**Score:** GOOD" in report
            assert "**Score:** FAIR" in report
            assert "**Score:** POOR" in report

            # Verify score summary is present
            assert "## Score Summary" in report

        finally:
            sys.stderr = original_stderr
