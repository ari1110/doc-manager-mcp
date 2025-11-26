"""Link index for O(1) link resolution in validate_docs.

This module provides a link index that enables fast link lookups without
iterating through all markdown files or doing repeated file system operations.

Performance improvement: O(M*L*M) -> O(M*L) where M=files, L=links per file.
"""

from pathlib import Path


class LinkIndex:
    """Index of markdown files for fast link resolution.

    Indexes files by multiple keys:
    - filename: "api.md"
    - stem: "api" (extensionless, Hugo-style)
    - relative path: "reference/api.md"
    - relative path without extension: "reference/api"

    Provides O(1) lookup instead of O(M) iteration or file system checks.
    """

    def __init__(self):
        """Initialize empty link index."""
        self._index: dict[str, Path] = {}
        self._resolved_index: dict[str, Path] = {}  # Reverse index: resolved absolute path -> file path
        self._file_count: int = 0

    def add(self, file_path: Path, docs_root: Path):
        """Add a markdown file to the index with multiple lookup keys.

        Args:
            file_path: Absolute path to markdown file
            docs_root: Documentation root directory
        """
        # Get relative path from docs root
        try:
            rel_path = file_path.relative_to(docs_root)
        except ValueError:
            # File is not within docs_root, skip it
            return

        # Normalize path separators to forward slashes (cross-platform)
        rel_path_str = str(rel_path).replace('\\', '/')

        # Index by various forms for flexible lookups
        # 1. By filename: "api.md"
        self._index[file_path.name] = file_path

        # 2. By stem (Hugo-style extensionless): "api"
        self._index[file_path.stem] = file_path

        # 3. By relative path: "reference/api.md"
        self._index[rel_path_str] = file_path

        # 4. By relative path without extension: "reference/api"
        if file_path.suffix:
            rel_path_no_ext = rel_path_str[:-len(file_path.suffix)]
            self._index[rel_path_no_ext] = file_path

        # 5. Add to reverse index for O(1) absolute path lookups
        try:
            resolved_str = str(file_path.resolve())
            self._resolved_index[resolved_str] = file_path
        except (ValueError, OSError):
            pass  # Skip files that can't be resolved

        self._file_count += 1

    def resolve(self, link_url: str, source_context: Path, docs_root: Path | None = None) -> Path | None:
        """Resolve a link URL to a markdown file using the index.

        Args:
            link_url: Link URL from markdown (e.g., "api.md", "../guide.md", "/reference/cli")
            source_context: Context path for relative links (usually parent directory of source file)
            docs_root: Optional docs root for computing relative paths

        Returns:
            Resolved Path to target file, or None if not found
        """
        # Strip anchor if present
        url_without_anchor = link_url.split('#')[0]
        if not url_without_anchor:
            return None

        # Normalize path separators
        url_without_anchor = url_without_anchor.replace('\\', '/')

        # Try direct lookup first (for simple filename/stem lookups)
        result = self._index.get(url_without_anchor)
        if result:
            return result

        # Handle relative paths (../, ./)
        if url_without_anchor.startswith(('./', '../')) and docs_root:
            # Normalize relative path to docs_root
            try:
                # Compute path and normalize using os.path (no file system I/O)
                import os
                full_path = source_context / url_without_anchor
                normalized_path = os.path.normpath(str(full_path))

                # Get relative path from docs_root (string operation, no I/O)
                try:
                    normalized_docs = os.path.normpath(str(docs_root))

                    # Check if normalized_path starts with docs_root
                    if normalized_path.startswith(normalized_docs):
                        # Remove docs_root prefix and normalize separators
                        rel_str = normalized_path[len(normalized_docs):].lstrip(os.sep).replace('\\', '/')

                        # Try direct lookup
                        result = self._index.get(rel_str)
                        if result:
                            return result

                        # Try with .md extension
                        if not rel_str.endswith('.md'):
                            result = self._index.get(rel_str + '.md')
                            if result:
                                return result

                        # Try without extension
                        if '.' in rel_str:
                            stem_path = rel_str.rsplit('.', 1)[0]
                            result = self._index.get(stem_path)
                            if result:
                                return result

                except (ValueError, IndexError):
                    # Path manipulation failed, skip
                    pass

            except (ValueError, OSError):
                pass

            return None

        # Handle absolute paths from docs root (e.g., "/reference/api.md")
        if url_without_anchor.startswith('/'):
            # Remove leading slash
            url_from_root = url_without_anchor.lstrip('/')

            # Try lookup
            result = self._index.get(url_from_root)
            if result:
                return result

            # Try without extension
            if '.' in url_from_root:
                base = url_from_root.rsplit('.', 1)[0]
                result = self._index.get(base)
                if result:
                    return result

        # Try with .md extension if not present
        if not url_without_anchor.endswith('.md'):
            result = self._index.get(url_without_anchor + '.md')
            if result:
                return result

        return None

    def __len__(self) -> int:
        """Return number of unique files in the index."""
        return self._file_count

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the index."""
        return key in self._index


def build_link_index(docs_root: Path) -> LinkIndex:
    """Build a link index for all markdown files in documentation directory.

    Args:
        docs_root: Documentation root directory

    Returns:
        LinkIndex with all markdown files indexed
    """
    index = LinkIndex()

    # Find all markdown files recursively
    for md_file in docs_root.rglob("*.md"):
        if md_file.is_file():
            index.add(md_file, docs_root)

    return index
