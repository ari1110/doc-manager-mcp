"""Workflow orchestration modules for doc-manager.

This package contains high-level workflow orchestration functions that
coordinate multiple tools to accomplish complex documentation tasks.

Available workflows:
- bootstrap: Create fresh documentation for a project from scratch
- migrate: Restructure existing documentation to a new organization
- sync: Keep documentation aligned with code changes
"""

from .bootstrap import bootstrap
from .migrate import migrate
from .sync import sync

__all__ = ["bootstrap", "migrate", "sync"]
