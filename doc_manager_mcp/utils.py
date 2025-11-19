"""Utility functions for doc-manager MCP server."""

import fnmatch
import hashlib
import os
import platform
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml


def calculate_checksum(file_path: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""

async def run_git_command(cwd: Path, *args, check_git_available: bool = True) -> str | None:
    """Run a git command and return output.

    Args:
        cwd: Working directory for git command
        *args: Git command arguments (e.g., "status", "--short")
        check_git_available: Whether to check git binary availability first

    Returns:
        Command output if successful, None otherwise

    Raises:
        RuntimeError: If git binary is not found (T018 - FR-002)

    Security:
        - Uses array form to prevent command injection
        - 30-second timeout to prevent hangs
        - Git availability check with clear error message
    """
    import asyncio
    import shutil

    # Check if git is available in PATH (T018)
    if check_git_available:
        if shutil.which('git') is None:
            raise RuntimeError(
                "Git is required but not found. Please install git and ensure it's in your PATH. "
                "Visit https://git-scm.com/downloads for installation instructions."
            )

    try:
        # Security: Using array form with hardcoded "git" binary and validated args
        # to prevent command injection. All args are from trusted internal sources.
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,  # Prevent hanging on Windows
        )

        # 30-second timeout (T019)
        stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode == 0:
            return stdout.decode().strip()
        else:
            return None
    except FileNotFoundError as err:
        # Git binary not found even after check
        raise RuntimeError("Git is required but not found. Please install git.") from err
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None

def detect_project_language(project_path: Path) -> str:
    """Detect primary programming language of project."""
    language_indicators = {
        "go.mod": "Go",
        "package.json": "JavaScript/TypeScript",
        "Cargo.toml": "Rust",
        "requirements.txt": "Python",
        "setup.py": "Python",
        "pom.xml": "Java",
        "build.gradle": "Java",
        "Gemfile": "Ruby",
        "composer.json": "PHP"
    }

    for file, language in language_indicators.items():
        if (project_path / file).exists():
            return language

    return "Unknown"

def find_docs_directory(project_path: Path) -> Path | None:
    """Find documentation directory in project."""
    common_doc_dirs = ["docs", "doc", "documentation", "docsite", "website/docs"]

    for dir_name in common_doc_dirs:
        doc_path = project_path / dir_name
        if doc_path.exists() and doc_path.is_dir():
            return doc_path

    return None

def load_config(project_path: Path) -> dict[str, Any] | None:
    """Load .doc-manager.yml configuration."""
    config_path = project_path / ".doc-manager.yml"
    if not config_path.exists():
        return None

    try:
        with open(config_path, encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None

def save_config(project_path: Path, config: dict[str, Any]) -> bool:
    """Save .doc-manager.yml configuration."""
    config_path = project_path / ".doc-manager.yml"
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception:
        return False

def handle_error(e: Exception, context: str = "", log_to_stderr: bool = True) -> str:
    """Consistent error formatting across all tools.

    Args:
        e: Exception that occurred
        context: Context where error occurred (e.g., tool name, operation)
        log_to_stderr: Whether to log error to stderr (default: True per FR-015)

    Returns:
        Formatted error message string (sanitized per FR-017)
    """
    import sys
    from datetime import datetime

    # Format error message without sensitive paths (FR-017)
    error_msg = f"Error: {type(e).__name__}"
    if context:
        error_msg += f" in {context}"

    # Sanitize error message - remove full paths
    error_str = str(e)
    # Remove Windows paths (C:\..., R:\...)
    import re
    error_str = re.sub(r'[A-Z]:\\[^\s]+', '[path]', error_str)
    # Remove Unix paths (/home/..., /usr/...)
    error_str = re.sub(r'/[\w/]+/[\w/]+', '[path]', error_str)

    error_msg += f": {error_str}"

    # Log to stderr (FR-015: errors must be logged, not silent)
    if log_to_stderr:
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] {error_msg}", file=sys.stderr)

    return error_msg

def matches_exclude_pattern(path: str, exclude_patterns: list[str]) -> bool:
    """Check if a path matches any of the exclude patterns.

    Args:
        path: Relative path to check (string)
        exclude_patterns: List of glob patterns (e.g., ["**/node_modules", "**/*.log"])

    Returns:
        True if path should be excluded, False otherwise
    """
    # Normalize path separators
    normalized_path = str(Path(path)).replace('\\', '/')

    for pattern in exclude_patterns:
        # Normalize pattern separators
        normalized_pattern = pattern.replace('\\', '/')

        # Handle **/ prefix (matches any depth)
        if normalized_pattern.startswith('**/'):
            pattern_suffix = normalized_pattern[3:]  # Remove **/
            # Check if pattern matches the full path or any part
            if fnmatch.fnmatch(normalized_path, '*/' + pattern_suffix) or \
               fnmatch.fnmatch(normalized_path, pattern_suffix):
                return True
            # Check if any component matches
            parts = normalized_path.split('/')
            for i, _part in enumerate(parts):
                remaining = '/'.join(parts[i:])
                if fnmatch.fnmatch(remaining, pattern_suffix):
                    return True
        # Handle /** suffix (matches directory and contents)
        elif normalized_pattern.endswith('/**'):
            dir_pattern = normalized_pattern[:-3]  # Remove /**
            if normalized_path.startswith(dir_pattern + '/') or normalized_path == dir_pattern:
                return True
        # Regular pattern matching
        else:
            if fnmatch.fnmatch(normalized_path, normalized_pattern):
                return True

    return False


# ============================================================================
# T004: File Locking Utility (FR-018)
# ============================================================================

@contextmanager
def file_lock(file_path: Path, timeout: int = 5, retries: int = 3):
    """Acquire exclusive file lock with timeout and retry (cross-platform).

    Args:
        file_path: Path to file to lock
        timeout: Lock acquisition timeout in seconds (default: 5 per clarification)
        retries: Number of retry attempts (default: 3 per clarification)

    Yields:
        None when lock is acquired

    Raises:
        TimeoutError: If lock cannot be acquired after all retries

    Example:
        with file_lock(baseline_path):
            # Read/write state file safely
            data = json.load(f)
    """

    lock_file_path = file_path.with_suffix(file_path.suffix + '.lock')
    lock_handle = None
    acquired = False

    try:
        for attempt in range(retries):
            try:
                # Create lock file
                lock_handle = open(lock_file_path, 'w')

                # Platform-specific locking
                if platform.system() == 'Windows':
                    import msvcrt
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl  # type: ignore[attr-defined]
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]

                acquired = True
                break  # Lock acquired successfully
            except OSError as e:
                if attempt < retries - 1:
                    # Wait before retry
                    time.sleep(1)
                    continue
                else:
                    # Final attempt failed
                    raise TimeoutError(f"Failed to acquire lock on {file_path.name} after {retries} attempts ({timeout}s timeout)") from e

        yield  # Lock held, execute critical section

    finally:
        # Always release lock
        if acquired and lock_handle:
            try:
                if platform.system() == 'Windows':
                    import msvcrt
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl  # type: ignore[attr-defined]
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
            except Exception:  # noqa: S110
                # Best effort release - failures during cleanup are non-critical
                pass

        if lock_handle:
            lock_handle.close()

        # Remove lock file
        try:
            if lock_file_path.exists():
                lock_file_path.unlink()
        except Exception:  # noqa: S110
            # Best effort cleanup - lock file removal failures are non-critical
            pass


# ============================================================================
# T006: Path Validation Utility (FR-001, FR-003, FR-020, FR-025, FR-028)
# ============================================================================

def safe_resolve(path: Path, max_depth: int | None = None) -> Path:
    """Safely resolve path with recursion depth limit (FR-020).

    Args:
        path: Path to resolve
        max_depth: Maximum symlink resolution depth (default: MAX_RECURSION_DEPTH from constants)

    Returns:
        Resolved path

    Raises:
        RecursionError: If symlink resolution exceeds max_depth

    Note:
        Prevents infinite loops from circular symlinks by limiting resolution depth.
    """
    from .constants import MAX_RECURSION_DEPTH

    if max_depth is None:
        max_depth = MAX_RECURSION_DEPTH

    # Track symlink resolution depth
    current_path = path
    depth = 0

    while current_path.is_symlink() and depth < max_depth:
        current_path = Path(os.readlink(current_path))
        if not current_path.is_absolute():
            current_path = path.parent / current_path
        depth += 1

    if depth >= max_depth and current_path.is_symlink():
        raise RecursionError(
            f"Symlink resolution exceeded maximum depth ({max_depth})\n"
            f"→ Check for circular symlinks or reduce symlink chain length."
        )

    return current_path.resolve()


def validate_path_boundary(path: Path, project_root: Path) -> Path:
    """Validate path stays within project boundary (prevents path traversal).

    Args:
        path: Path to validate
        project_root: Project root directory (security boundary)

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path escapes project boundary or is a malicious symlink

    Security:
        - Detects and rejects symlinks that escape boundary (FR-003)
        - Prevents path traversal attacks (FR-001)
        - Verifies resolved path stays within boundary (FR-025)
    """
    # Check if it's a symlink before resolution (FR-028)
    if path.is_symlink():
        # Resolve and verify target stays within boundary
        resolved = path.resolve()
        try:
            # Check if resolved path is relative to project root
            resolved.relative_to(project_root.resolve())
        except ValueError as err:
            raise ValueError(f"Symlink escapes project boundary: {path.name} points outside project root") from err
    else:
        # Regular path resolution
        resolved = path.resolve()

    # Verify resolved path is within project boundary (FR-025)
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError as err:
        raise ValueError(f"Path escapes project boundary: {path.name} is outside project root") from err

    return resolved


# ============================================================================
# T007: Resource Limit Enforcement Utilities (FR-019, FR-020, FR-021)
# ============================================================================

class ResourceLimits:
    """Enforce resource limits to prevent exhaustion attacks.

    Attributes:
        max_files: Maximum files to process (default: 10,000 per FR-019)
        max_depth: Maximum recursion depth (default: 100 per FR-020)
        timeout: Operation timeout in seconds (default: 60 per FR-021)
    """

    def __init__(self, max_files: int = 10000, max_depth: int = 100, timeout: int = 60):
        self.max_files = max_files
        self.max_depth = max_depth
        self.timeout = timeout
        self.file_count = 0
        self.current_depth = 0

    def check_file_count(self) -> None:
        """Check if file count limit exceeded.

        Raises:
            ValueError: If file count exceeds limit
        """
        if self.file_count >= self.max_files:
            raise ValueError(f"File count limit exceeded: {self.file_count} >= {self.max_files}")

    def increment_file_count(self) -> None:
        """Increment file counter and check limit."""
        self.file_count += 1
        self.check_file_count()

    def check_depth(self, depth: int) -> None:
        """Check if recursion depth limit exceeded.

        Args:
            depth: Current recursion depth

        Raises:
            ValueError: If depth exceeds limit
        """
        if depth >= self.max_depth:
            raise ValueError(f"Recursion depth limit exceeded: {depth} >= {self.max_depth}")


@contextmanager
def operation_timeout(seconds: int = 60):
    """Set timeout for blocking operations (Unix/Windows compatible).

    Args:
        seconds: Timeout in seconds (default: 60 per FR-021)

    Yields:
        None

    Raises:
        TimeoutError: If operation exceeds timeout

    Example:
        with operation_timeout(60):
            # Long-running file operation
            process_files()
    """
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation exceeded {seconds}s timeout")

    # Unix-like systems support SIGALRM
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)  # type: ignore[attr-defined]
        signal.alarm(seconds)  # type: ignore[attr-defined]
        try:
            yield
        finally:
            signal.alarm(0)  # type: ignore[attr-defined]
            signal.signal(signal.SIGALRM, old_handler)  # type: ignore[attr-defined]
    else:
        # Windows doesn't support SIGALRM - use threading.Timer as fallback
        import threading
        timer = threading.Timer(seconds, lambda: (_ for _ in ()).throw(TimeoutError(f"Operation exceeded {seconds}s timeout")))
        timer.start()
        try:
            yield
        finally:
            timer.cancel()


# ============================================================================
# T008: Response Size Enforcement (FR-010)
# ============================================================================

def enforce_response_limit(response: str | dict, limit: int = 25000) -> str | dict[str, Any]:
    """Truncate response if exceeds CHARACTER_LIMIT.

    Args:
        response: Response string or dict to check
        limit: Character limit (default: 25,000 per constants.py)

    Returns:
        Response truncated if necessary (str) or dict as-is

    Note:
        MCP protocol has response size limits. Large dependency graphs
        or validation reports can exceed limits.

        Dicts are passed through unchanged - FastMCP handles JSON serialization
        and size limits. Only strings (markdown) need truncation.
    """
    # If dict, return as-is (FastMCP will serialize it)
    if isinstance(response, dict):
        return response

    # String handling (existing logic)
    if len(response) <= limit:
        return response

    # Leave room for truncation marker (126 characters total)
    truncation_message = (
        "\n\n[Response truncated - exceeded 25,000 character limit]"
        "\n[Tip: Request specific sections or use filters to reduce output size]"
    )
    truncated = response[:limit - len(truncation_message)]
    truncated += truncation_message

    return truncated


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize object to JSON with error handling (T050 - FR-012).

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps (e.g., indent=2)

    Returns:
        JSON string or error message if serialization fails

    Note:
        Prevents crashes from unserializable objects (e.g., datetime, Path, custom classes).
        Returns a structured error message that's still valid for MCP responses.
    """
    import json

    try:
        return json.dumps(obj, **kwargs)
    except (TypeError, ValueError) as e:
        # JSON serialization failed - return error as JSON
        error_response = {
            "status": "error",
            "message": "JSON serialization error",
            "error": str(e),
            "type": type(e).__name__
        }
        try:
            return json.dumps(error_response, indent=2)
        except Exception:
            # Fallback if even error serialization fails
            return '{"status": "error", "message": "Critical JSON serialization failure"}'
