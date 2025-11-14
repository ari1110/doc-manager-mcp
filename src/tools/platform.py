"""Platform detection tools for doc-manager."""

from pathlib import Path
import json
from typing import List, Dict, Any

from ..models import DetectPlatformInput
from ..constants import ResponseFormat
from ..utils import detect_project_language, handle_error


def _check_root_configs(project_path: Path) -> List[Dict[str, Any]]:
    """Check root-level configuration files (fast path)."""
    detected = []

    # Hugo detection
    if (project_path / "hugo.toml").exists() or (project_path / "hugo.yaml").exists() or (project_path / "config.toml").exists():
        detected.append({
            "platform": "hugo",
            "confidence": "high",
            "evidence": ["Found Hugo configuration file in project root"]
        })

    # Docusaurus detection
    if (project_path / "docusaurus.config.js").exists() or (project_path / "docusaurus.config.ts").exists():
        detected.append({
            "platform": "docusaurus",
            "confidence": "high",
            "evidence": ["Found Docusaurus configuration file in project root"]
        })

    # MkDocs detection
    if (project_path / "mkdocs.yml").exists():
        detected.append({
            "platform": "mkdocs",
            "confidence": "high",
            "evidence": ["Found mkdocs.yml configuration in project root"]
        })

    # Sphinx detection (also checks common doc directories)
    if (project_path / "docs" / "conf.py").exists():
        detected.append({
            "platform": "sphinx",
            "confidence": "high",
            "evidence": ["Found Sphinx conf.py in docs/ directory"]
        })
    elif (project_path / "doc" / "conf.py").exists():
        detected.append({
            "platform": "sphinx",
            "confidence": "high",
            "evidence": ["Found Sphinx conf.py in doc/ directory"]
        })

    # VitePress detection
    if (project_path / ".vitepress" / "config.js").exists() or (project_path / ".vitepress" / "config.ts").exists():
        detected.append({
            "platform": "vitepress",
            "confidence": "high",
            "evidence": ["Found VitePress configuration in .vitepress/ directory"]
        })

    # Jekyll detection
    if (project_path / "_config.yml").exists():
        detected.append({
            "platform": "jekyll",
            "confidence": "high",
            "evidence": ["Found Jekyll _config.yml in project root"]
        })

    return detected


def _check_doc_directories(project_path: Path) -> List[Dict[str, Any]]:
    """Check common documentation directories (targeted search)."""
    detected = []
    doc_dirs = ["docsite", "docs", "documentation", "website", "site"]

    for doc_dir in doc_dirs:
        doc_path = project_path / doc_dir
        if not doc_path.exists() or not doc_path.is_dir():
            continue

        # Hugo in subdirectory
        if (doc_path / "hugo.yaml").exists() or (doc_path / "hugo.toml").exists() or (doc_path / "config.toml").exists():
            detected.append({
                "platform": "hugo",
                "confidence": "high",
                "evidence": [f"Found Hugo configuration in {doc_dir}/ directory"]
            })

        # Docusaurus in subdirectory
        if (doc_path / "docusaurus.config.js").exists() or (doc_path / "docusaurus.config.ts").exists():
            detected.append({
                "platform": "docusaurus",
                "confidence": "high",
                "evidence": [f"Found Docusaurus configuration in {doc_dir}/ directory"]
            })

        # MkDocs in subdirectory
        if (doc_path / "mkdocs.yml").exists():
            detected.append({
                "platform": "mkdocs",
                "confidence": "high",
                "evidence": [f"Found mkdocs.yml in {doc_dir}/ directory"]
            })

        # Sphinx in subdirectory
        if (doc_path / "conf.py").exists():
            detected.append({
                "platform": "sphinx",
                "confidence": "high",
                "evidence": [f"Found Sphinx conf.py in {doc_dir}/ directory"]
            })

        # VitePress in subdirectory
        vitepress_path = doc_path / ".vitepress"
        if (vitepress_path / "config.js").exists() or (vitepress_path / "config.ts").exists():
            detected.append({
                "platform": "vitepress",
                "confidence": "high",
                "evidence": [f"Found VitePress configuration in {doc_dir}/.vitepress/ directory"]
            })

    return detected


def _check_dependencies(project_path: Path) -> List[Dict[str, Any]]:
    """Parse dependency files to detect platforms from dependencies."""
    detected = []

    # Check package.json for Node.js projects
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                if "docusaurus" in deps or "@docusaurus/core" in deps:
                    detected.append({
                        "platform": "docusaurus",
                        "confidence": "medium",
                        "evidence": ["Found Docusaurus in package.json dependencies"]
                    })
                elif "vitepress" in deps:
                    detected.append({
                        "platform": "vitepress",
                        "confidence": "medium",
                        "evidence": ["Found VitePress in package.json dependencies"]
                    })
        except Exception:
            pass

    # Check requirements.txt or setup.py for Python projects
    requirements_txt = project_path / "requirements.txt"
    if requirements_txt.exists():
        try:
            with open(requirements_txt, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                if "mkdocs" in content:
                    detected.append({
                        "platform": "mkdocs",
                        "confidence": "medium",
                        "evidence": ["Found mkdocs in requirements.txt"]
                    })
                elif "sphinx" in content:
                    detected.append({
                        "platform": "sphinx",
                        "confidence": "medium",
                        "evidence": ["Found sphinx in requirements.txt"]
                    })
        except Exception:
            pass

    # Check setup.py for Sphinx (common in Python projects)
    setup_py = project_path / "setup.py"
    if setup_py.exists() and not detected:  # Only if nothing else detected
        try:
            with open(setup_py, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                # Prefer Sphinx for setup.py-based projects (setuptools pattern)
                if "sphinx" in content or "setuptools" in content:
                    detected.append({
                        "platform": "sphinx",
                        "confidence": "low",
                        "evidence": ["Found setup.py (Sphinx is common for setuptools-based Python projects)"]
                    })
        except Exception:
            pass

    # Check go.mod for Go projects
    go_mod = project_path / "go.mod"
    if go_mod.exists():
        try:
            with open(go_mod, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                if "hugo" in content:
                    detected.append({
                        "platform": "hugo",
                        "confidence": "medium",
                        "evidence": ["Found hugo reference in go.mod"]
                    })
        except Exception:
            pass

    return detected


async def detect_platform(params: DetectPlatformInput) -> str:
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
            return f"Error: Project path does not exist: {project_path}"

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

        # Determine recommendation
        language = detect_project_language(project_path)
        recommendation = None
        rationale = []

        if detected_platforms:
            # Use detected platform
            recommendation = detected_platforms[0]["platform"]
            rationale.append(f"Detected existing {recommendation} platform")
        else:
            # Recommend based on project characteristics
            if language == "Go":
                recommendation = "hugo"
                rationale.append("Hugo is written in Go and popular in Go ecosystem")
            elif language in ["JavaScript/TypeScript", "Node.js"]:
                recommendation = "docusaurus"
                rationale.append("Docusaurus is React-based and popular in JavaScript ecosystem")
            elif language == "Python":
                recommendation = "mkdocs"
                rationale.append("MkDocs is Python-based and popular in Python ecosystem")
            else:
                recommendation = "hugo"
                rationale.append("Hugo is fast, language-agnostic, and widely adopted")

        # Format response
        if params.response_format == ResponseFormat.JSON:
            result = {
                "detected_platforms": detected_platforms,
                "recommendation": recommendation,
                "rationale": rationale,
                "project_language": language
            }
            return json.dumps(result, indent=2)
        else:
            lines = ["# Documentation Platform Detection", ""]

            if detected_platforms:
                lines.append("## Detected Platforms")
                for platform in detected_platforms:
                    lines.append(f"- **{platform['platform'].upper()}** ({platform['confidence']} confidence)")
                    for evidence in platform['evidence']:
                        lines.append(f"  - {evidence}")
                lines.append("")

            lines.append("## Recommendation")
            lines.append(f"**{recommendation.upper()}**")
            lines.append("")
            lines.append("### Rationale:")
            for reason in rationale:
                lines.append(f"- {reason}")
            lines.append("")
            lines.append(f"### Project Context:")
            lines.append(f"- Primary Language: {language}")

            return "\n".join(lines)

    except Exception as e:
        return handle_error(e, "detect_platform")
