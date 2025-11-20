"""Analysis tools for doc-manager."""

from .detect_changes import docmgr_detect_changes
from .platform import detect_platform

__all__ = ["detect_platform", "docmgr_detect_changes"]
