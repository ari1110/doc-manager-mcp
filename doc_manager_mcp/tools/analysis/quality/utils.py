"""Utility functions for quality assessment."""

import re


def remove_code_blocks(content: str) -> str:
    """Remove fenced code blocks from content to avoid false positives."""
    # Simple regex removal is fine for this use case (no need for line numbers)
    code_block_pattern = r'^```.*?^```'
    return re.sub(code_block_pattern, '', content, flags=re.MULTILINE | re.DOTALL)
