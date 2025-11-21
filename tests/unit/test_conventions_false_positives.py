"""Tests for convention validation false positive fixes.

This test suite ensures that content INSIDE code blocks is never validated
as markdown, preventing false positives from comments, examples, and teaching content.
"""

import pytest

from doc_manager_mcp.core.conventions import validate_against_conventions
from doc_manager_mcp.models import DocumentationConventions


@pytest.fixture
def strict_conventions():
    """Create conventions with all strict rules enabled."""
    return DocumentationConventions(
        style={
            "headings": {"case": "sentence_case", "consistency_required": True},
            "code": {"inline_format": "backticks", "block_language_required": True},
            "voice": {"person": "third", "active_voice_preferred": True}
        },
        structure={
            "require_intro": True,
            "require_toc": {"enabled": False, "min_length": 500},
            "max_heading_depth": 3,
            "heading_hierarchy": "strict"
        },
        quality={
            "sentences": {"max_length": 25, "min_length": 3},
            "paragraphs": {"max_length": 150},
            "links": {"validate_links": True},
            "images": {"require_alt_text": True},
            "code": {"validate_syntax": False}
        },
        terminology={"preferred": {}, "avoid": []}
    )


def test_code_block_content_not_validated(strict_conventions):
    """Ensure content inside fenced code blocks is never validated as markdown.

    This is the core test for the false positive fix.
    """
    content = '''# Real Heading

```yaml
# .doc-manager.yml (This is NOT a heading - it's a comment in YAML)
platform: mkdocs
sources:
  - src/**/*.py
```

![Real Image](test.png)

```markdown
![Fake Image](fake.png)
```

## Another Real Heading
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    # Should find 0 heading violations from code block comments
    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    assert len(heading_violations) == 0, f"Found {len(heading_violations)} heading violations in code blocks"

    # Should find 0 image violations from code block examples
    image_violations = [v for v in violations if v['rule'] == 'require_alt_text']
    assert len(image_violations) == 0, f"Found {len(image_violations)} image violations in code blocks"

    # Should find 0 hierarchy violations from code block content
    hierarchy_violations = [v for v in violations if v['rule'] == 'heading_hierarchy']
    assert len(hierarchy_violations) == 0, f"Found {len(hierarchy_violations)} hierarchy violations in code blocks"


def test_indented_code_blocks_not_validated(strict_conventions):
    """Ensure indented code blocks (4 spaces) are also excluded from validation."""
    content = '''# Main Heading

Normal paragraph.

    # This is indented code in Python
    def foo():
        # Another comment that looks like H1
        pass

Back to normal text.
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    # Should only find violations for "Main Heading" if any
    assert len(heading_violations) == 0, f"Indented code block content was validated: {heading_violations}"


def test_nested_code_blocks_in_teaching_examples(strict_conventions):
    """Ensure nested code blocks (markdown examples) are handled correctly."""
    content = '''# How to write code blocks

Use triple backticks to create code blocks:

````markdown
```yaml
# .doc-manager.yml
platform: mkdocs
```
````

## Another Section
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    # The YAML comment inside the nested block should NOT trigger violations
    assert len(heading_violations) == 0, f"Nested code block content was validated: {heading_violations}"


def test_multiple_code_blocks_with_comments(strict_conventions):
    """Test that ALL code blocks are properly excluded, not just the first one."""
    content = '''# Configuration Guide

## YAML Config

```yaml
# .doc-manager.yml
platform: mkdocs
```

## Shell Scripts

```bash
# scripts/check.sh
#!/bin/bash
echo "test"
```

## Python Example

```python
# main.py
def main():
    # Run checks
    pass
```
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    # None of the comments in any of the 3 code blocks should trigger violations
    assert len(heading_violations) == 0, f"Found {len(heading_violations)} violations from comments in code blocks"


def test_code_blocks_without_language_tags_still_excluded(strict_conventions):
    """Even code blocks missing language tags should have their content excluded from validation."""
    content = '''# Test Document

```
# This comment is in an unlabeled code block
![](image.png)
```

Real content here.
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    # Should flag the missing language tag
    lang_violations = [v for v in violations if v['rule'] == 'block_language_required']
    assert len(lang_violations) == 1, "Should flag missing language tag"

    # But should NOT flag the comment or image inside the code block
    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    assert len(heading_violations) == 0, "Content in unlabeled code block should still be excluded"

    image_violations = [v for v in violations if v['rule'] == 'require_alt_text']
    assert len(image_violations) == 0, "Images in unlabeled code block should be excluded"


def test_real_violations_still_detected(strict_conventions):
    """Ensure that REAL violations outside code blocks are still properly detected."""
    content = '''# Good Heading

```python
# This is fine - it's in a code block
```

## bad heading case

![](missing-alt-text.png)

#### Skipped from H2 to H4
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    # Should find the real heading case violation
    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    assert len(heading_violations) >= 1, f"Should detect real heading case violation, found: {heading_violations}"

    # Should find the real missing alt text
    image_violations = [v for v in violations if v['rule'] == 'require_alt_text']
    assert len(image_violations) == 1, "Should detect real missing alt text"

    # Should find the real hierarchy violation
    hierarchy_violations = [v for v in violations if v['rule'] == 'heading_hierarchy']
    assert len(hierarchy_violations) == 1, "Should detect real hierarchy violation (H2 -> H4)"


def test_code_block_boundaries_precise(strict_conventions):
    """Test that code block boundaries are detected precisely."""
    content = '''# Before Code Block
Text before.

```yaml
# Inside code block
key: value
```

# After Code Block

Text after with ![](image.png)
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    # Should NOT flag the comment inside code block
    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    assert all('Inside code block' not in str(v) for v in heading_violations), \
        "Code block comment was incorrectly validated"

    # SHOULD flag the missing alt text outside code block
    image_violations = [v for v in violations if v['rule'] == 'require_alt_text']
    assert len(image_violations) == 1, "Should detect image outside code block"


def test_edge_case_empty_code_blocks(strict_conventions):
    """Test that empty code blocks don't cause issues."""
    content = '''# Test

```python
```

## Section
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    # Should not crash and should work normally
    lang_violations = [v for v in violations if v['rule'] == 'block_language_required']
    assert len(lang_violations) == 0, "Labeled empty code block should be fine"


def test_unclosed_code_blocks_handled_gracefully(strict_conventions):
    """Test that unclosed code blocks at EOF are handled without crashes."""
    content = '''# Test

```python
# Code that continues to end of file
def foo():
    pass
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    # Should not crash - markdown-it-py handles this
    assert isinstance(violations, list), "Should return violations list without crashing"

    # The comment inside the unclosed block should still be excluded
    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    assert all('Code that continues' not in str(v) for v in heading_violations), \
        "Content in unclosed code block should be excluded"


def test_code_blocks_with_attributes(strict_conventions):
    """Test that code blocks with attributes like {.line-numbers} are handled."""
    content = '''# Test

```python {.line-numbers}
# Comment with attribute syntax
def foo():
    pass
```
'''
    violations = validate_against_conventions(content, strict_conventions, "test.md")

    heading_violations = [v for v in violations if v['rule'] == 'heading_case']
    assert len(heading_violations) == 0, "Code block with attributes should exclude content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
