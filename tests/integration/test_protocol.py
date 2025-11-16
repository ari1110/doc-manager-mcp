
import pytest
from pathlib import Path

from src.models import TrackDependenciesInput, ValidateDocsInput
from src.constants import ResponseFormat
from src.tools.dependencies import track_dependencies
from src.tools.validation import validate_docs


@pytest.mark.asyncio
class TestResponseSizeLimits:
    """Test that response size limits are enforced (T054 - US4)."""

    async def test_large_dependency_graph_truncated(self, tmp_path):
        """Test that large dependency graphs are truncated to 25K chars (FR-010).

        This test creates a project with many files to generate a large
        dependency graph that exceeds the response limit.
        """
        project_dir = tmp_path / "large_project"
        project_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Create many documentation files with references
        # Each file references multiple source files
        for i in range(100):
            doc_content = f"# Documentation {i}\n\n"
            # Add many references to create large dependency graph
            for j in range(50):
                doc_content += f"See `src/module{j}.py` for details.\n"
                doc_content += f"Function `function_{j}()` in module{j}.\n"
                doc_content += f"Class `Class{j}` implementation.\n"

            doc_file = docs_dir / f"doc{i}.md"
            doc_file.write_text(doc_content)

        # Track dependencies - should generate large output
        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(project_dir),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Verify response is limited to ~25K characters
        assert len(result) <= 25000, (
            f"Response exceeds 25K limit: {len(result)} characters"
        )

        # Verify truncation message is present if truncated
        if "Response truncated" in result:
            assert "25,000 character limit" in result
            assert "Tip:" in result or "reduce output" in result

    async def test_large_validation_report_truncated(self, tmp_path):
        """Test that large validation reports are truncated (FR-010)."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create many files with issues to generate large validation report
        for i in range(200):
            content = f"# Doc {i}\n\n"
            # Add many broken links
            for j in range(20):
                content += f"[Broken link {j}](./nonexistent{j}.md)\n"
            (docs_dir / f"doc{i}.md").write_text(content)

        result = await validate_docs(ValidateDocsInput(
            project_path=str(tmp_path),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Verify response is limited
        assert len(result) <= 25000, (
            f"Response exceeds 25K limit: {len(result)} characters"
        )

    async def test_small_responses_not_truncated(self, tmp_path):
        """Test that small responses are not unnecessarily truncated."""
        project_dir = tmp_path / "small_project"
        project_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Create just a few small files
        (docs_dir / "index.md").write_text("# Index\n\nWelcome")
        (docs_dir / "guide.md").write_text("# Guide\n\nInstructions")

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(project_dir),
            docs_path="docs",
            response_format=ResponseFormat.MARKDOWN
        ))

        # Small responses should not be truncated
        assert "Response truncated" not in result
        assert len(result) < 25000

    async def test_json_responses_also_limited(self, tmp_path):
        """Test that JSON responses are also size-limited."""
        project_dir = tmp_path / "large_project"
        project_dir.mkdir()

        docs_dir = project_dir / "docs"
        docs_dir.mkdir()

        # Create many files
        for i in range(150):
            content = f"# Doc {i}\n\n"
            for j in range(30):
                content += f"Reference to `file{j}.py`\n"
            (docs_dir / f"doc{i}.md").write_text(content)

        result = await track_dependencies(TrackDependenciesInput(
            project_path=str(project_dir),
            docs_path="docs",
            response_format=ResponseFormat.JSON
        ))

        # JSON responses should also be limited
        assert len(result) <= 25000, (
            f"JSON response exceeds 25K limit: {len(result)} characters"
        )
