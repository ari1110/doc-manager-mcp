"""Platform detection tools for doc-manager."""

import json
import sys
from pathlib import Path
from typing import Any

from doc_manager_mcp.constants import (
    DEFAULT_PLATFORM_RECOMMENDATION,
    DOC_DIRECTORIES,
    LANGUAGE_PLATFORM_RECOMMENDATIONS,
    PLATFORM_MARKERS,
)
from doc_manager_mcp.core import detect_project_language, enforce_response_limit, handle_error
from doc_manager_mcp.models import DetectPlatformInput


def _check_root_configs(project_path: Path) -> list[dict[str, Any]]:
    """Check root-level configuration files using configurable markers."""
    detected = []

    for platform, markers in PLATFORM_MARKERS.items():
        root_configs = markers.get("root_configs", [])
        for config_file in root_configs:
            if (project_path / config_file).exists():
                detected.append({
                    "platform": platform,
                    "confidence": "high",
                    "evidence": [f"Found {platform} configuration file: {config_file}"]
                })
                break  # Only add once per platform

    return detected


def _check_doc_directories(project_path: Path) -> list[dict[str, Any]]:
    """Check common documentation directories using configurable markers."""
    detected = []

    for doc_dir in DOC_DIRECTORIES:
        doc_path = project_path / doc_dir
        if not doc_path.exists() or not doc_path.is_dir():
            continue

        # Check each platform's subdirectory configs
        for platform, markers in PLATFORM_MARKERS.items():
            subdir_configs = markers.get("subdir_configs", [])
            for config_file in subdir_configs:
                if (doc_path / config_file).exists():
                    detected.append({
                        "platform": platform,
                        "confidence": "high",
                        "evidence": [f"Found {platform} configuration in {doc_dir}/{config_file}"]
                    })
                    break  # Only add once per platform per directory

    return detected


def _check_dependencies(project_path: Path) -> list[dict[str, Any]]:
    """Parse dependency files to detect platforms using configurable markers."""
    detected = []

    # Iterate through all platforms and check their dependency markers
    for platform, markers in PLATFORM_MARKERS.items():
        dependencies = markers.get("dependencies", {})

        for dep_file, dep_markers in dependencies.items():
            dep_path = project_path / dep_file
            if not dep_path.exists():
                continue

            try:
                # Special handling for package.json (JSON parsing)
                if dep_file == "package.json":
                    with open(dep_path, encoding='utf-8') as f:
                        data = json.load(f)
                        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                        # Check if any of the markers are in dependencies
                        if any(marker in deps for marker in dep_markers):
                            detected.append({
                                "platform": platform,
                                "confidence": "medium",
                                "evidence": [f"Found {platform} in package.json dependencies"]
                            })
                            break

                # Text-based dependency files (requirements.txt, go.mod, setup.py)
                else:
                    with open(dep_path, encoding='utf-8') as f:
                        content = f.read().lower()

                        # Check if any of the markers are in the file content
                        if any(marker.lower() in content for marker in dep_markers):
                            confidence = "low" if dep_file == "setup.py" else "medium"
                            detected.append({
                                "platform": platform,
                                "confidence": confidence,
                                "evidence": [f"Found {platform} in {dep_file}"]
                            })
                            break

            except Exception as e:
                print(f"Warning: Failed to parse {dep_file}: {e}", file=sys.stderr)

    return detected


async def detect_platform(params: DetectPlatformInput) -> str | dict[str, Any]:
    """Detect and recommend documentation platform for the project.

    This tool uses a multi-stage detection approach:
    1. Check root-level config files (fast path)
    2. Search common documentation directories
    3. Parse dependency files for platform mentions

    Args:
        params (DetectPlatformInput): Validated input parameters containing:
            - project_path (str): Absolute path to project root
            - response_format (ResponseFormat): Output format (markdown or json)

    Returns:
        str: Platform detection results with recommendation and rationale

    Examples:
        - Use when: Choosing a documentation platform for a new project
        - Use when: Migrating from one platform to another
        - Use when: Verifying current platform detection

    Error Handling:
        - Returns error if project_path doesn't exist
        - Returns "unknown" platform if no platform detected
    """
    try:
        project_path = Path(params.project_path).resolve()

        if not project_path.exists():
            return enforce_response_limit(f"Error: Project path does not exist: {project_path}")

        # Multi-stage detection approach
        detected_platforms = []

        # Stage 1: Check root-level configs (fast path)
        root_detections = _check_root_configs(project_path)
        detected_platforms.extend(root_detections)

        # Stage 2: Check common documentation directories (if nothing found)
        if not detected_platforms:
            doc_dir_detections = _check_doc_directories(project_path)
            detected_platforms.extend(doc_dir_detections)

        # Stage 3: Parse dependency files (if still nothing found)
        if not detected_platforms:
            dep_detections = _check_dependencies(project_path)
            detected_platforms.extend(dep_detections)

        # Determine recommendation using configurable mappings
        language = detect_project_language(project_path)
        recommendation = None
        rationale = []

        if detected_platforms:
            # Use detected platform
            recommendation = detected_platforms[0]["platform"]
            rationale.append(f"Detected existing {recommendation} platform")
        else:
            # Recommend based on project language using configurable mappings
            if language in LANGUAGE_PLATFORM_RECOMMENDATIONS:
                recommendation, reason = LANGUAGE_PLATFORM_RECOMMENDATIONS[language]
                rationale.append(reason)
            else:
                # Use default recommendation
                recommendation, reason = DEFAULT_PLATFORM_RECOMMENDATION
                rationale.append(reason)

        # Return structured data
        return {
            "detected_platforms": detected_platforms,
            "recommendation": recommendation,
            "rationale": rationale,
            "project_language": language
        }

    except Exception as e:
        return enforce_response_limit(handle_error(e, "detect_platform"))
