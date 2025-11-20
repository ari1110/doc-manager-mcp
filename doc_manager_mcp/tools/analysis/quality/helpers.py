"""Helper functions for quality.py to prevent file bloat."""

from pathlib import Path
from typing import Any

from ....utils import is_public_symbol


def check_list_formatting_consistency(
    docs_path: Path
) -> dict[str, Any]:
    """Check consistency of list formatting across documentation.

    Detects if project uses - vs * vs + for unordered lists.

    Returns:
        Dict with majority_marker, inconsistent_files, consistency_score
    """
    import re

    markdown_files = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        markdown_files.extend(docs_path.glob(pattern))

    if not markdown_files:
        return {
            "majority_marker": None,
            "inconsistent_files": [],
            "consistency_score": 1.0,
            "marker_counts": {}
        }

    # Count list markers across all files
    marker_counts = {"-": 0, "*": 0, "+": 0}
    file_markers = {}  # Track which markers each file uses

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Remove code blocks to avoid counting code examples
            code_block_pattern = r'^```.*?^```'
            content_without_code = re.sub(code_block_pattern, '', content, flags=re.MULTILINE | re.DOTALL)

            # Pattern for unordered list items at start of line
            # Match: "- item", "* item", "+ item" (with optional leading spaces)
            file_marker_counts = {"-": 0, "*": 0, "+": 0}

            for marker in ["-", "*", "+"]:
                # Escape marker for regex if needed
                escaped_marker = re.escape(marker)
                # Match marker at start of line (with optional indentation) followed by space
                pattern = rf'^\s*{escaped_marker}\s+'
                matches = re.findall(pattern, content_without_code, re.MULTILINE)
                count = len(matches)
                marker_counts[marker] += count
                file_marker_counts[marker] = count

            # Record which markers this file uses
            if sum(file_marker_counts.values()) > 0:
                file_markers[str(md_file.relative_to(docs_path))] = file_marker_counts

        except Exception:  # noqa: S112
            # Skip files that can't be read
            continue

    # Determine majority marker
    majority_marker = max(marker_counts, key=lambda k: marker_counts[k])
    total_markers = sum(marker_counts.values())

    if total_markers == 0:
        return {
            "majority_marker": None,
            "inconsistent_files": [],
            "consistency_score": 1.0,
            "marker_counts": marker_counts
        }

    # Find files using different markers
    inconsistent_files = []
    for file_path, markers in file_markers.items():
        # File is inconsistent if it uses a non-majority marker
        if markers[majority_marker] == 0 and sum(markers.values()) > 0:
            # This file doesn't use the majority marker at all
            used_marker = max(markers, key=markers.get)
            inconsistent_files.append({
                "file": file_path,
                "uses": used_marker,
                "count": markers[used_marker]
            })

    # Calculate consistency score
    majority_count = marker_counts[majority_marker]
    consistency_score = majority_count / total_markers if total_markers > 0 else 1.0

    return {
        "majority_marker": majority_marker,
        "inconsistent_files": inconsistent_files,
        "consistency_score": round(consistency_score, 2),
        "marker_counts": marker_counts
    }


def check_heading_case_consistency(
    docs_path: Path
) -> dict[str, Any]:
    """Check consistency of heading capitalization style.

    Detects if project uses Title Case vs Sentence case.

    Returns:
        Dict with majority_style, inconsistent_files, consistency_score
    """
    from ....indexing.parsers.markdown import MarkdownParser

    parser = MarkdownParser()
    markdown_files = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        markdown_files.extend(docs_path.glob(pattern))

    if not markdown_files:
        return {
            "majority_style": None,
            "inconsistent_files": [],
            "consistency_score": 1.0,
            "style_counts": {}
        }

    style_counts = {"title_case": 0, "sentence_case": 0}
    file_styles = {}  # Track which style each file predominantly uses

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            headers = parser.extract_headers(content)

            if not headers:
                continue

            file_style_counts = {"title_case": 0, "sentence_case": 0}

            for header in headers:
                text = header["text"].strip()

                # Skip empty headers or headers with only special chars
                if not text or not any(c.isalpha() for c in text):
                    continue

                # Skip headers that are all caps (like "API" or "TODO")
                if text.isupper():
                    continue

                # Classify as title case or sentence case
                style = _classify_heading_style(text)
                style_counts[style] += 1
                file_style_counts[style] += 1

            # Record predominant style for this file
            if sum(file_style_counts.values()) > 0:
                predominant_style = max(file_style_counts, key=lambda k: file_style_counts[k])
                file_styles[str(md_file.relative_to(docs_path))] = {
                    "style": predominant_style,
                    "counts": file_style_counts
                }

        except Exception:  # noqa: S112
            # Skip files that can't be read
            continue

    # Determine majority style
    total_headings = sum(style_counts.values())

    if total_headings == 0:
        return {
            "majority_style": None,
            "inconsistent_files": [],
            "consistency_score": 1.0,
            "style_counts": style_counts
        }

    majority_style = max(style_counts, key=lambda k: style_counts[k])

    # Find files using different style
    inconsistent_files = []
    for file_path, file_info in file_styles.items():
        if file_info["style"] != majority_style:
            inconsistent_files.append({
                "file": file_path,
                "style": file_info["style"],
                "counts": file_info["counts"]
            })

    # Calculate consistency score
    majority_count = style_counts[majority_style]
    consistency_score = majority_count / total_headings if total_headings > 0 else 1.0

    return {
        "majority_style": majority_style,
        "inconsistent_files": inconsistent_files,
        "consistency_score": round(consistency_score, 2),
        "style_counts": style_counts
    }


def _classify_heading_style(heading: str) -> str:
    """Classify a heading as title_case or sentence_case.

    Title case: Most major words are capitalized
    Sentence case: Only first word and proper nouns are capitalized
    """
    words = heading.split()

    if len(words) == 0:
        return "sentence_case"

    # Count capitalized words (excluding first word)
    capitalized_count = 0
    total_significant_words = 0

    # Articles and short words that should be lowercase in title case
    minor_words = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to", "by", "in", "of", "with"}

    for i, word in enumerate(words):
        # Skip first word (always capitalized in both styles)
        if i == 0:
            continue

        # Skip words without letters
        if not any(c.isalpha() for c in word):
            continue

        # Clean word of punctuation for checking
        clean_word = ''.join(c for c in word if c.isalpha())

        if not clean_word:
            continue

        # Skip minor words in the analysis (they can be lowercase in title case)
        if clean_word.lower() in minor_words:
            continue

        total_significant_words += 1

        # Check if word starts with capital
        if clean_word[0].isupper():
            capitalized_count += 1

    # If no significant words to analyze, default to sentence case
    if total_significant_words == 0:
        return "sentence_case"

    # If more than 50% of significant words are capitalized, it's title case
    capitalization_ratio = capitalized_count / total_significant_words

    return "title_case" if capitalization_ratio > 0.5 else "sentence_case"


def detect_multiple_h1s(
    docs_path: Path
) -> list[dict[str, Any]]:
    """Detect files with multiple H1 headers.

    Best practice: Each markdown file should have exactly one H1.

    Args:
        docs_path: Path to documentation directory

    Returns:
        List of files with multiple H1s (file, h1_count, h1_texts)
    """
    from ....indexing.parsers.markdown import MarkdownParser

    parser = MarkdownParser()
    issues = []

    # Find all markdown files
    markdown_files = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        markdown_files.extend(docs_path.glob(pattern))

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Extract all headers
            headers = parser.extract_headers(content)

            # Filter for H1s only
            h1_headers = [h for h in headers if h["level"] == 1]

            # Report files with 0 or >1 H1s
            if len(h1_headers) != 1:
                issues.append({
                    "file": str(md_file.relative_to(docs_path)),
                    "h1_count": len(h1_headers),
                    "h1_texts": [h["text"] for h in h1_headers]
                })

        except Exception:  # noqa: S112
            # Skip files that can't be read
            continue

    return issues


def detect_undocumented_apis(
    project_path: Path,
    docs_path: Path
) -> list[dict[str, Any]]:
    """Detect public APIs without documentation.

    Compares codebase public symbols against documented references.

    Args:
        project_path: Root directory of the project
        docs_path: Documentation directory path

    Returns:
        List of undocumented symbols (name, type, file, line)
    """
    import re

    from ....indexing import SymbolIndexer
    from ....indexing.parsers.markdown import MarkdownParser

    # Step 1: Get all public symbols from codebase
    try:
        indexer = SymbolIndexer()
        indexer.index_project(project_path)
        all_symbols = indexer.get_all_symbols()
    except Exception as e:
        import sys
        print(f"Warning: Failed to index project symbols: {e}", file=sys.stderr)
        return []

    # Filter to only public symbols based on language conventions
    public_symbols = [symbol for symbol in all_symbols if is_public_symbol(symbol)]

    # Step 2: Scan documentation for symbol references
    documented_symbols = set()
    parser = MarkdownParser()

    # Find all markdown files
    markdown_files = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        markdown_files.extend(docs_path.glob(pattern))

    # Extract documented symbols from all markdown files
    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Extract inline code references
            inline_codes = parser.extract_inline_code(content)
            for code_span in inline_codes:
                code_text = code_span["text"]

                # Match function references: functionName(), ClassName.MethodName()
                if match := re.match(r'^(?:([A-Z][a-zA-Z0-9]*)\.)?(([A-Z][a-zA-Z0-9]*)|([a-z_][a-zA-Z0-9_]*))\(\)$', code_text):
                    # Extract function/method name (group 2 is full match, group 3 or 4 is name)
                    func_name = match.group(3) or match.group(4)
                    documented_symbols.add(func_name)

                # Match class/type references: ClassName
                elif match := re.match(r'^([A-Z][a-zA-Z0-9]+)$', code_text):
                    class_name = match.group(1)
                    # Exclude common acronyms
                    if len(class_name) > 2 and class_name not in ['API', 'CLI', 'HTTP', 'HTTPS', 'URL', 'JSON', 'XML', 'HTML', 'CSS']:
                        documented_symbols.add(class_name)

            # Extract function signatures from markdown headings
            # Pattern: ## functionName(...) or ### ClassName.methodName(...)
            heading_pattern = r'^#+\s+(?:([A-Z][a-zA-Z0-9]*)\.)?(([A-Z][a-zA-Z0-9]*)|([a-z_][a-zA-Z0-9_]*))\s*\([^)]*\)'
            for match in re.finditer(heading_pattern, content, re.MULTILINE):
                func_name = match.group(3) or match.group(4)
                documented_symbols.add(func_name)

        except Exception:  # noqa: S112
            continue  # Skip files that can't be read

    # Step 3: Compare and find undocumented symbols
    undocumented = []
    for symbol in public_symbols:
        if symbol.name not in documented_symbols:
            undocumented.append({
                "name": symbol.name,
                "type": symbol.type.value,
                "file": symbol.file,
                "line": symbol.line
            })

    return undocumented


def calculate_documentation_coverage(
    project_path: Path,
    docs_path: Path
) -> dict[str, Any]:
    """Calculate percentage of documented symbols.

    Args:
        project_path: Path to project root
        docs_path: Path to documentation directory

    Returns:
        Dict with total_symbols, documented_symbols, coverage_percentage, breakdown_by_type
    """
    import re
    import sys

    from ....indexing import SymbolIndexer
    from ....indexing.parsers.markdown import MarkdownParser

    # Index all symbols in the project
    try:
        indexer = SymbolIndexer()
        indexer.index_project(project_path)
        all_symbols = indexer.get_all_symbols()
    except Exception as e:
        print(f"Warning: Failed to index project symbols: {e}", file=sys.stderr)
        return {
            "error": str(e),
            "total_symbols": 0,
            "documented_symbols": 0,
            "coverage_percentage": 0.0,
            "breakdown_by_type": {}
        }

    # Filter to only public symbols based on language conventions
    public_symbols = [symbol for symbol in all_symbols if is_public_symbol(symbol)]

    if not public_symbols:
        return {
            "total_symbols": 0,
            "documented_symbols": 0,
            "coverage_percentage": 0.0,
            "breakdown_by_type": {},
            "note": "No public symbols found in project"
        }

    # Scan documentation for symbol references
    parser = MarkdownParser()
    documented_symbols = set()

    # Find all markdown files
    markdown_files = []
    for pattern in ["**/*.md", "**/*.markdown"]:
        markdown_files.extend(docs_path.glob(pattern))

    for md_file in markdown_files:
        try:
            with open(md_file, encoding='utf-8') as f:
                content = f.read()

            # Extract inline code references
            inline_codes = parser.extract_inline_code(content)
            for code_span in inline_codes:
                code_text = code_span["text"]

                # Match function references: functionName(), ClassName.MethodName()
                if match := re.match(r'^(?:([A-Z][a-zA-Z0-9]*)\.)?(([A-Z][a-zA-Z0-9]*)|([a-z_][a-zA-Z0-9_]*))\(\)$', code_text):
                    func_name = match.group(3) or match.group(4)
                    documented_symbols.add(func_name)

                # Match class/type references: ClassName
                elif match := re.match(r'^([A-Z][a-zA-Z0-9]+)$', code_text):
                    class_name = match.group(1)
                    if len(class_name) > 2 and class_name not in ['API', 'CLI', 'HTTP', 'HTTPS', 'URL', 'JSON', 'XML', 'HTML', 'CSS']:
                        documented_symbols.add(class_name)

            # Extract function signatures from markdown headings
            heading_pattern = r'^#+\s+(?:([A-Z][a-zA-Z0-9]*)\.)?(([A-Z][a-zA-Z0-9]*)|([a-z_][a-zA-Z0-9_]*))\s*\([^)]*\)'
            for match in re.finditer(heading_pattern, content, re.MULTILINE):
                func_name = match.group(3) or match.group(4)
                documented_symbols.add(func_name)

            # Extract code blocks (check for symbol usage in examples)
            code_blocks = parser.extract_code_blocks(content)
            for block in code_blocks:
                # Simple token-based extraction - check if symbol name appears
                for symbol in public_symbols:
                    if symbol.name in block["code"]:
                        documented_symbols.add(symbol.name)

        except Exception:  # noqa: S112
            continue  # Skip files that can't be read

    # Match documented references to actual symbols
    documented_count = 0
    breakdown = {}

    for symbol in public_symbols:
        symbol_type = str(symbol.type.value)
        if symbol_type not in breakdown:
            breakdown[symbol_type] = {"total": 0, "documented": 0}

        breakdown[symbol_type]["total"] += 1

        if symbol.name in documented_symbols:
            documented_count += 1
            breakdown[symbol_type]["documented"] += 1

    # Calculate percentages
    total = len(public_symbols)
    coverage_pct = (documented_count / total * 100) if total > 0 else 0.0

    # Calculate percentages by type
    for _type_name, counts in breakdown.items():
        counts["coverage_percentage"] = round(
            counts["documented"] / counts["total"] * 100 if counts["total"] > 0 else 0.0,
            1
        )

    return {
        "total_symbols": total,
        "documented_symbols": documented_count,
        "coverage_percentage": round(coverage_pct, 1),
        "breakdown_by_type": breakdown
    }
