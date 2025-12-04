"""Internal tools for doc-manager (not exposed via MCP).

This package contains internal implementation tools that are used by
the public MCP tools but are not directly exposed to users:

- baselines: Baseline loading utilities (load_repo_baseline, etc.)
- bootstrap: Create fresh documentation structure (called by docmgr_init)
- config: Configuration file management (called by docmgr_init)
- memory: Memory system initialization (called by docmgr_init)
- changes: Change detection logic (called by docmgr_detect_changes)
- dependencies: Dependency tracking (called by docmgr_init and docmgr_update_baseline)
"""

from .baselines import (
    check_baseline_compatibility,
    get_baseline_version,
    load_repo_baseline,
)
from .bootstrap import bootstrap
from .changes import map_changes
from .config import initialize_config
from .dependencies import load_dependencies, track_dependencies
from .memory import initialize_memory

__all__ = [
    "bootstrap",
    "check_baseline_compatibility",
    "get_baseline_version",
    "initialize_config",
    "initialize_memory",
    "load_dependencies",
    "load_repo_baseline",
    "map_changes",
    "track_dependencies",
]
