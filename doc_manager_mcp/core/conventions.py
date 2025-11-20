"""Convention loading and validation utilities."""

import re
from pathlib import Path
from typing import Any

import yaml

from doc_manager_mcp.models import DocumentationConventions


def load_conventions(project_path: Path) -> DocumentationConventions | None:
    """Load conventions from project's .doc-manager directory.

    Args:
        project_path: Path to project root

    Returns:
        Parsed conventions or None if file doesn't exist

    Examples:
        >>> conventions = load_conventions(Path('/path/to/project'))
        >>> if conventions and conventions.style.headings.case:
        ...     print(f"Use {conventions.style.headings.case} for headings")
    """
    conventions_path = project_path / ".doc-manager" / "memory" / "doc-conventions.yml"

    if not conventions_path.exists():
        return None

    try:
        with open(conventions_path, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        return DocumentationConventions(**data)
    except Exception:
        # If parsing fails, return None rather than crashing
        return None


def validate_against_conventions(
    content: str,
    conventions: DocumentationConventions,
    file_path: str | None = None
) -> list[dict[str, Any]]:
    """Validate markdown content against conventions.

    Args:
        content: Markdown content to validate
        conventions: Parsed convention rules
        file_path: Optional file path for error reporting

    Returns:
        List of violations, each containing:
            - rule: Rule that was violated
            - line: Line number (if applicable)
            - message: Description of violation
            - severity: 'error' or 'warning'

    Examples:
        >>> conventions = DocumentationConventions()
        >>> violations = validate_against_conventions('```\\ncode\\n```', conventions)
        >>> violations[0]['rule']
        'require_code_language'
    """
    violations = []
    lines = content.split('\n')

    # Check code block language requirement
    if conventions.style.code.block_language_required:
        in_code_block = False

        for i, line in enumerate(lines, 1):
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Starting a code block
                    in_code_block = True

                    # Check if language is specified
                    language = line.strip()[3:].strip()
                    if not language:
                        violations.append({
                            'rule': 'block_language_required',
                            'line': i,
                            'message': 'Code block missing language specification',
                            'severity': 'error',
                            'file': file_path
                        })
                else:
                    # Ending a code block
                    in_code_block = False

    # Check alt text requirement
    if conventions.quality.images.require_alt_text:
        # Match markdown images: ![alt](url)
        image_pattern = r'!\[([^\]]*)\]\([^\)]+\)'

        for i, line in enumerate(lines, 1):
            for match in re.finditer(image_pattern, line):
                alt_text = match.group(1).strip()
                if not alt_text:
                    violations.append({
                        'rule': 'require_alt_text',
                        'line': i,
                        'message': 'Image missing descriptive alt text',
                        'severity': 'error',
                        'file': file_path
                    })

    # Check heading case (if specified)
    if conventions.style.headings.case:
        heading_pattern = r'^(#{1,6})\s+(.+)$'

        for i, line in enumerate(lines, 1):
            match = re.match(heading_pattern, line)
            if match:
                heading_text = match.group(2).strip()

                # Skip if heading contains code or special formatting
                if '`' in heading_text or heading_text.startswith('['):
                    continue

                is_valid = _check_heading_case(heading_text, conventions.style.headings.case)

                if not is_valid:
                    violations.append({
                        'rule': 'heading_case',
                        'line': i,
                        'message': f'Heading does not match {conventions.style.headings.case} convention',
                        'severity': 'warning',
                        'file': file_path
                    })

    # Check heading hierarchy (if strict)
    if conventions.structure.heading_hierarchy == "strict":
        violations.extend(_check_heading_hierarchy(lines, file_path))

    # Check max heading depth
    if conventions.structure.max_heading_depth:
        heading_pattern = r'^(#{1,6})\s+'
        for i, line in enumerate(lines, 1):
            match = re.match(heading_pattern, line)
            if match:
                depth = len(match.group(1))
                if depth > conventions.structure.max_heading_depth:
                    violations.append({
                        'rule': 'max_heading_depth',
                        'line': i,
                        'message': f'Heading depth {depth} exceeds maximum {conventions.structure.max_heading_depth}',
                        'severity': 'warning',
                        'file': file_path
                    })

    return violations


def _check_heading_case(heading: str, required_case: str) -> bool:
    """Check if heading matches required case style.

    Args:
        heading: Heading text to check
        required_case: 'sentence_case', 'title_case', 'lower', or 'upper'

    Returns:
        True if heading matches case requirement
    """
    # Remove leading/trailing whitespace
    heading = heading.strip()

    # Skip headings with special characters or numbers at start
    if not heading or not heading[0].isalpha():
        return True

    if required_case == 'sentence_case':
        # First word capitalized, rest lowercase (except proper nouns)
        words = heading.split()
        if not words:
            return True
        # First word should start with capital
        if not words[0][0].isupper():
            return False
        return True

    elif required_case == 'title_case':
        # All major words capitalized
        # Simple check: most words start with uppercase
        words = [w for w in heading.split() if len(w) > 3]  # Ignore short words
        if not words:
            return True
        capitalized = sum(1 for w in words if w[0].isupper())
        return capitalized / len(words) >= 0.7

    elif required_case == 'lower':
        # All lowercase (except proper nouns/acronyms)
        return heading.islower() or any(c.isupper() for c in heading if c.isalpha())

    elif required_case == 'upper':
        # All uppercase
        return heading.isupper()

    return True


def _check_heading_hierarchy(lines: list[str], file_path: str | None = None) -> list[dict[str, Any]]:
    """Check for heading hierarchy violations (skipped levels).

    Args:
        lines: Document lines
        file_path: Optional file path for error reporting

    Returns:
        List of hierarchy violations
    """
    violations = []
    heading_pattern = r'^(#{1,6})\s+'
    previous_depth = 0

    for i, line in enumerate(lines, 1):
        match = re.match(heading_pattern, line)
        if match:
            depth = len(match.group(1))

            # Check if we skipped a level (e.g., H1 -> H3)
            if previous_depth > 0 and depth > previous_depth + 1:
                violations.append({
                    'rule': 'heading_hierarchy',
                    'line': i,
                    'message': f'Heading hierarchy violation: skipped from H{previous_depth} to H{depth}',
                    'severity': 'warning',
                    'file': file_path
                })

            previous_depth = depth

    return violations


def get_convention_summary(conventions: DocumentationConventions) -> str:
    """Generate human-readable summary of conventions.

    Args:
        conventions: Parsed conventions

    Returns:
        Formatted string summarizing active conventions

    Examples:
        >>> conventions = DocumentationConventions()
        >>> summary = get_convention_summary(conventions)
        >>> 'sentence_case' in summary
        True
    """
    parts = []

    if conventions.style.headings.case:
        parts.append(f"- Headings: {conventions.style.headings.case}")

    if conventions.style.code.block_language_required:
        parts.append("- Code blocks: language specification required")

    if conventions.quality.images.require_alt_text:
        parts.append("- Images: descriptive alt text required")

    if conventions.quality.links.validate_links:
        parts.append("- Links: must be valid and up-to-date")

    if conventions.structure.max_heading_depth:
        parts.append(f"- Max heading depth: H{conventions.structure.max_heading_depth}")

    if conventions.structure.heading_hierarchy == "strict":
        parts.append("- Heading hierarchy: strict (no level skipping)")

    if conventions.terminology.avoid:
        parts.append(f"- Avoid {len(conventions.terminology.avoid)} terms")

    if conventions.terminology.preferred:
        parts.append(f"- {len(conventions.terminology.preferred)} preferred terms defined")

    if not parts:
        return "No specific conventions defined"

    return "\n".join(parts)
