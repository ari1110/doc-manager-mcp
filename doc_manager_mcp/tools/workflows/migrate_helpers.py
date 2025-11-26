"""Helper functions for documentation migration."""

import shutil
import subprocess
from pathlib import Path
from typing import TypedDict

from doc_manager_mcp.indexing.transforms.links import (
    compute_link_mappings,
    extract_frontmatter,
    generate_toc,
    preserve_frontmatter,
    rewrite_links_in_content,
    update_or_insert_toc,
)


class TransformResult(TypedDict):
    """Result from transforming a markdown file."""
    method: str
    links_rewritten: bool
    toc_generated: bool


class ProcessResult(TypedDict):
    """Result from processing a single file during migration."""
    old_file: Path
    new_file: Path
    method: str
    links_rewritten: bool
    toc_generated: bool


def rewrite_links(
    body: str,
    new_file: Path,
    existing_docs: Path,
    new_docs: Path,
    project_path: Path
) -> tuple[str, bool]:
    """Rewrite links in markdown content.

    Args:
        body: Markdown content (without frontmatter)
        new_file: New file path
        existing_docs: Old documentation directory
        new_docs: New documentation directory
        project_path: Project root path

    Returns:
        Tuple of (updated body, links_were_rewritten)
    """
    link_mappings = compute_link_mappings(
        body,
        new_file,
        existing_docs,
        new_docs,
        project_path
    )

    if link_mappings:
        body = rewrite_links_in_content(body, link_mappings)
        return body, True

    return body, False


def add_toc(body: str, has_toc_marker: bool) -> tuple[str, bool]:
    """Add or regenerate table of contents.

    Args:
        body: Markdown content (without frontmatter)
        has_toc_marker: Whether content has <!-- TOC --> marker

    Returns:
        Tuple of (updated body, toc_was_generated)
    """
    if has_toc_marker:
        toc = generate_toc(body, max_depth=3)
        body = update_or_insert_toc(body, toc)
        return body, True

    return body, False


def process_markdown_file(
    old_file: Path,
    new_file: Path,
    existing_docs: Path,
    new_docs: Path,
    project_path: Path,
    *,
    rewrite_links_enabled: bool,
    regenerate_toc: bool,
    use_git: bool,
    dry_run: bool
) -> TransformResult:
    """Process a markdown file with optional transformations.

    Args:
        old_file: Source file path
        new_file: Destination file path
        existing_docs: Old documentation directory
        new_docs: New documentation directory
        project_path: Project root path
        rewrite_links_enabled: Whether to rewrite links
        regenerate_toc: Whether to regenerate TOC
        use_git: Whether to use git operations
        dry_run: Whether this is a dry run

    Returns:
        Dict with keys: method (str), links_rewritten (bool), toc_generated (bool)
    """
    content = old_file.read_text(encoding='utf-8')

    # Extract frontmatter
    frontmatter_dict, body = extract_frontmatter(content)

    # Track changes
    links_rewritten = False
    toc_generated = False

    # Rewrite links if enabled
    if rewrite_links_enabled:
        body, links_rewritten = rewrite_links(
            body,
            new_file,
            existing_docs,
            new_docs,
            project_path
        )

    # Regenerate TOC if enabled
    if regenerate_toc:
        has_toc_marker = '<!-- TOC -->' in content
        body, toc_generated = add_toc(body, has_toc_marker)

    # Reconstruct with frontmatter
    if frontmatter_dict:
        final_content = preserve_frontmatter(frontmatter_dict, body)
    else:
        final_content = body

    # Write file if not dry run
    method = "preview"  # Default for dry run
    if not dry_run:
        new_file.write_text(final_content, encoding='utf-8')

        # For markdown files with transformations, use git rm + git add
        # (Git will detect this as a rename with modifications)
        if use_git:
            try:
                # Stage new file
                subprocess.run(  # noqa: S603
                    ['git', 'add', str(new_file)],  # noqa: S607
                    cwd=project_path,
                    check=True,
                    capture_output=True
                )
                # Remove old file from git
                subprocess.run(  # noqa: S603
                    ['git', 'rm', str(old_file)],  # noqa: S607
                    cwd=project_path,
                    check=True,
                    capture_output=True
                )
                method = "git mv"
            except subprocess.CalledProcessError:
                # Git operations failed, but file is already copied
                method = "copy"
        else:
            method = "copy"

    return {
        "method": method,
        "links_rewritten": links_rewritten,
        "toc_generated": toc_generated
    }


def process_single_file(
    old_file: Path,
    existing_docs: Path,
    new_docs: Path,
    project_path: Path,
    *,
    rewrite_links_enabled: bool,
    regenerate_toc: bool,
    use_git: bool,
    dry_run: bool
) -> ProcessResult:
    """Process a single file (markdown or non-markdown) for migration.

    Args:
        old_file: Source file path
        existing_docs: Old documentation directory
        new_docs: New documentation directory
        project_path: Project root path
        rewrite_links_enabled: Whether to rewrite links
        regenerate_toc: Whether to regenerate TOC
        use_git: Whether to use git operations
        dry_run: Whether this is a dry run

    Returns:
        Dict with keys: old_file, new_file, method, links_rewritten, toc_generated
    """
    relative_path = old_file.relative_to(existing_docs)
    new_file = new_docs / relative_path

    # Create parent directories if not dry run
    if not dry_run:
        new_file.parent.mkdir(parents=True, exist_ok=True)

    # Process markdown files with link rewriting/TOC
    if old_file.suffix.lower() in ['.md', '.markdown']:
        result = process_markdown_file(
            old_file,
            new_file,
            existing_docs,
            new_docs,
            project_path,
            rewrite_links_enabled=rewrite_links_enabled,
            regenerate_toc=regenerate_toc,
            use_git=use_git,
            dry_run=dry_run
        )
        method = result["method"]
        links_rewritten = result["links_rewritten"]
        toc_generated = result["toc_generated"]
    else:
        # Non-markdown files: use git mv if preserving history, else copy
        method = "preview"
        links_rewritten = False
        toc_generated = False

        if not dry_run:
            if use_git:
                try:
                    # Use git mv for non-markdown files
                    subprocess.run(  # noqa: S603
                        ['git', 'mv', str(old_file), str(new_file)],  # noqa: S607
                        cwd=project_path,
                        check=True,
                        capture_output=True
                    )
                    method = "git mv"
                except subprocess.CalledProcessError:
                    # Fallback to regular copy if git mv fails
                    shutil.copy2(old_file, new_file)
                    method = "copy"
            else:
                shutil.copy2(old_file, new_file)
                method = "copy"

    return {
        "old_file": old_file,
        "new_file": new_file,
        "method": method,
        "links_rewritten": links_rewritten,
        "toc_generated": toc_generated
    }
