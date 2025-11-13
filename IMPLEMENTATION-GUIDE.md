# Implementation Guide for Remaining Tools

This guide provides step-by-step instructions and code examples for implementing the remaining 7 tools in the doc-manager MCP server.

## Quick Start

1. Copy appropriate template from `templates/tools/`
2. Create new file in `src/tools/`
3. Import and register tool in `server.py`
4. Create tests using `templates/tests/test-template.py`
5. Update README.md with new tool documentation

---

## Tool 1: Quality Assessment (`docmgr_assess_quality`)

**File**: `src/tools/quality.py`
**Model**: `AssessQualityInput` (already defined in `src/models.py`)
**Priority**: High

### Implementation Steps

1. **Set up Vale integration** (optional but recommended):
```bash
# Install Vale CLI
# macOS: brew install vale
# Windows: scoop install vale
# Linux: https://vale.sh/docs/vale-cli/installation/
```

2. **Implement basic quality assessment**:
```python
from ..models import AssessQualityInput
from ..constants import ResponseFormat, QualityCriterion
from ..utils import handle_error, find_docs_directory
import subprocess
from pathlib import Path

async def assess_quality(params: AssessQualityInput) -> str:
    project_path = Path(params.project_path).resolve()
    docs_path = _get_docs_path(project_path, params.docs_path)

    # Criteria to assess (all 7 if not specified)
    criteria = params.criteria or list(QualityCriterion)

    results = {}
    for criterion in criteria:
        results[criterion.value] = await _assess_criterion(
            docs_path,
            criterion
        )

    return _format_quality_report(results, params.response_format)
```

3. **Implement criterion checkers**:
```python
async def _assess_criterion(docs_path: Path, criterion: QualityCriterion) -> Dict:
    if criterion == QualityCriterion.ACCURACY:
        return await _check_accuracy(docs_path)
    elif criterion == QualityCriterion.CONSISTENCY:
        return await _check_consistency_with_vale(docs_path)
    elif criterion == QualityCriterion.CLARITY:
        return await _check_clarity(docs_path)
    # ... implement for all 7 criteria
```

4. **Vale integration example**:
```python
async def _check_consistency_with_vale(docs_path: Path) -> Dict:
    """Run Vale linter for consistency checks."""
    try:
        result = subprocess.run(
            ["vale", "--output=JSON", str(docs_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 or result.returncode == 1:  # 1 means issues found
            issues = json.loads(result.stdout) if result.stdout else {}
            return {
                "score": _calculate_vale_score(issues),
                "issues": issues,
                "tool": "vale"
            }
    except FileNotFoundError:
        # Vale not installed, use basic checks
        return await _check_consistency_basic(docs_path)
```

5. **Register in server.py**:
```python
from src.models import AssessQualityInput
from src.tools.quality import assess_quality

@mcp.tool(
    name="docmgr_assess_quality",
    annotations={
        "title": "Assess Documentation Quality",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_assess_quality(params: AssessQualityInput) -> str:
    """Evaluate documentation against 7 quality criteria."""
    return await assess_quality(params)
```

**Reference**: Use `references/quality-criteria.md` for detailed assessment rubrics.

---

## Tool 2: Validation (`docmgr_validate_docs`)

**File**: `src/tools/validation.py`
**Model**: `ValidateDocsInput` (already defined)
**Priority**: High

### Implementation Steps

1. **Implement link checker**:
```python
async def _check_broken_links(docs_path: Path) -> List[Dict]:
    """Check for broken internal and external links."""
    issues = []

    for md_file in docs_path.rglob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        links = _extract_markdown_links(content)

        for link in links:
            if link.startswith('http'):
                # External link - check if reachable
                if not await _is_url_accessible(link):
                    issues.append({
                        "file": str(md_file.relative_to(docs_path)),
                        "link": link,
                        "type": "broken_external_link"
                    })
            else:
                # Internal link - check if file exists
                target = (md_file.parent / link).resolve()
                if not target.exists():
                    issues.append({
                        "file": str(md_file.relative_to(docs_path)),
                        "link": link,
                        "type": "broken_internal_link"
                    })

    return issues
```

2. **Implement asset validation**:
```python
async def _validate_assets(docs_path: Path, asset_manifest: Dict) -> List[Dict]:
    """Validate image links and alt text."""
    issues = []

    for md_file in docs_path.rglob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        images = _extract_markdown_images(content)

        for img in images:
            # Check alt text
            if not img['alt_text'] or img['alt_text'].strip() == '':
                issues.append({
                    "file": str(md_file.relative_to(docs_path)),
                    "image": img['src'],
                    "type": "missing_alt_text"
                })

            # Check if image exists
            if not img['src'].startswith('http'):
                img_path = (md_file.parent / img['src']).resolve()
                if not img_path.exists():
                    issues.append({
                        "file": str(md_file.relative_to(docs_path)),
                        "image": img['src'],
                        "type": "missing_image_file"
                    })

    return issues
```

3. **Implement code snippet validation**:
```python
async def _validate_code_snippets(docs_path: Path) -> List[Dict]:
    """Extract and validate code snippets."""
    issues = []

    for md_file in docs_path.rglob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        snippets = _extract_code_blocks(content)

        for snippet in snippets:
            lang = snippet['language']
            code = snippet['code']
            line_num = snippet['line']

            # Validate based on language
            if lang == 'python':
                if not _is_valid_python(code):
                    issues.append({
                        "file": str(md_file.relative_to(docs_path)),
                        "line": line_num,
                        "language": lang,
                        "type": "invalid_syntax"
                    })
            # Add validators for other languages

    return issues
```

---

## Tool 3: Change Mapping (`docmgr_map_changes`)

**File**: `src/tools/changes.py`
**Model**: `MapChangesInput` (already defined)
**Priority**: High

### Implementation Steps

1. **Implement checksum comparison**:
```python
async def map_changes(params: MapChangesInput) -> str:
    project_path = Path(params.project_path).resolve()

    # Load previous checksums from memory
    memory = _load_memory(project_path)
    if not memory:
        return "Error: Memory system not initialized. Run docmgr_initialize_memory first."

    old_checksums = memory.get('checksums', {})

    # Calculate current checksums
    new_checksums = {}
    for file_path in project_path.rglob("*"):
        if file_path.is_file():
            relative_path = str(file_path.relative_to(project_path))
            new_checksums[relative_path] = calculate_checksum(file_path)

    # Find changed files
    changed_files = []
    for path, new_sum in new_checksums.items():
        old_sum = old_checksums.get(path)
        if old_sum != new_sum:
            changed_files.append(path)

    # Map to affected docs
    affected_docs = await _map_files_to_docs(changed_files, project_path)

    return _format_mapping_report(affected_docs, params.response_format)
```

2. **Use mapping patterns**:
```python
async def _map_files_to_docs(changed_files: List[str], project_path: Path) -> List[Dict]:
    """Map changed code files to documentation files using patterns."""
    affected_docs = []

    # Load custom mappings from config if available
    config = load_config(project_path)
    custom_mappings = config.get('custom_mappings', []) if config else []

    for file_path in changed_files:
        # Apply patterns from references/doc-mapping-patterns.md

        # CLI command changes
        if file_path.startswith("cmd/"):
            affected_docs.append({
                "file": "docs/reference/command-reference.md",
                "reason": f"CLI command changed: {file_path}",
                "priority": "high",
                "changed_file": file_path
            })

        # API changes
        elif file_path.startswith("internal/") or file_path.startswith("pkg/"):
            affected_docs.append({
                "file": "docs/reference/api.md",
                "reason": f"Internal API changed: {file_path}",
                "priority": "high",
                "changed_file": file_path
            })

        # Configuration changes
        elif "config" in file_path.lower() or file_path.endswith(".yml"):
            affected_docs.append({
                "file": "docs/reference/configuration.md",
                "reason": f"Configuration changed: {file_path}",
                "priority": "high",
                "changed_file": file_path
            })

        # Apply custom mappings
        for mapping in custom_mappings:
            if _matches_pattern(file_path, mapping['pattern']):
                for doc in mapping['docs']:
                    affected_docs.append({
                        "file": doc,
                        "reason": f"Custom mapping: {file_path} → {doc}",
                        "priority": mapping.get('priority', 'medium'),
                        "changed_file": file_path
                    })

    return _deduplicate_docs(affected_docs)
```

**Reference**: Use `references/doc-mapping-patterns.md` for pattern details.

---

## Tool 4: Dependency Tracking (`docmgr_track_dependencies`)

**File**: `src/tools/dependencies.py`
**Model**: `TrackDependenciesInput` (already defined)
**Priority**: Medium

### Implementation Example

```python
async def track_dependencies(params: TrackDependenciesInput) -> str:
    """Build dependency graph of code → docs relationships."""
    project_path = Path(params.project_path).resolve()
    docs_path = _find_docs_directory(project_path)

    if not docs_path:
        return "Error: No documentation directory found"

    dependencies = {}

    # Scan all documentation files
    for doc_file in docs_path.rglob("*.md"):
        content = doc_file.read_text(encoding='utf-8')

        # Extract code references (file paths, function names, etc.)
        references = _extract_code_references(content)

        for ref in references:
            code_file = _resolve_code_reference(ref, project_path)
            if code_file and code_file.exists():
                relative_code = str(code_file.relative_to(project_path))
                relative_doc = str(doc_file.relative_to(project_path))

                if relative_code not in dependencies:
                    dependencies[relative_code] = []
                dependencies[relative_code].append(relative_doc)

    # Save to .doc-manager/dependencies.json
    dep_file = project_path / ".doc-manager" / "dependencies.json"
    dep_file.parent.mkdir(parents=True, exist_ok=True)
    with open(dep_file, 'w') as f:
        json.dump(dependencies, f, indent=2)

    return _format_dependency_report(dependencies, params.response_format)
```

---

## Tool 5-7: Workflows (Bootstrap, Migrate, Sync)

**File**: `src/tools/workflows.py`
**Models**: `BootstrapInput`, `MigrateInput`, `SyncInput` (already defined)
**Priority**: High

### Bootstrap Workflow Example

```python
async def bootstrap(params: BootstrapInput) -> str:
    """Generate fresh documentation from scratch."""
    project_path = Path(params.project_path).resolve()

    workflow_results = {
        "steps_completed": [],
        "overall_status": "in_progress"
    }

    # Step 1: Detect or use specified platform
    if params.platform:
        platform = params.platform.value
    else:
        platform_result = await detect_platform(DetectPlatformInput(
            project_path=str(project_path),
            response_format=ResponseFormat.JSON
        ))
        platform_data = json.loads(platform_result)
        platform = platform_data['recommendation']

    workflow_results["steps_completed"].append({
        "step": "platform_detection",
        "platform": platform
    })

    # Step 2: Create docs structure
    docs_path = project_path / params.docs_path
    await _create_docs_structure(docs_path, platform)

    workflow_results["steps_completed"].append({
        "step": "structure_creation",
        "path": str(docs_path)
    })

    # Step 3: Generate initial content
    await _generate_initial_docs(docs_path, project_path, platform)

    workflow_results["steps_completed"].append({
        "step": "content_generation"
    })

    # Step 4: Initialize memory
    await initialize_memory(InitializeMemoryInput(
        project_path=str(project_path)
    ))

    workflow_results["steps_completed"].append({
        "step": "memory_initialization"
    })

    workflow_results["overall_status"] = "completed"

    return _format_workflow_response(workflow_results, ResponseFormat.MARKDOWN)
```

---

## Testing Each Tool

Use the test template (`templates/tests/test-template.py`) and create comprehensive tests:

```bash
# Create test file
cp templates/tests/test-template.py tests/integration/test_quality.py

# Edit to match your tool
# Run tests
pytest tests/integration/test_quality.py -v
```

---

## Registering Tools in server.py

After implementing each tool:

```python
# In server.py

# 1. Import the model and implementation
from src.models import AssessQualityInput
from src.tools.quality import assess_quality

# 2. Register with @mcp.tool decorator
@mcp.tool(
    name="docmgr_assess_quality",
    annotations={
        "title": "Assess Documentation Quality",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def docmgr_assess_quality(params: AssessQualityInput) -> str:
    """Evaluate documentation against 7 quality criteria."""
    return await assess_quality(params)
```

---

## Vale Configuration Example

Create `.vale.ini` in project root:

```ini
StylesPath = .vale/styles

MinAlertLevel = suggestion

[*.md]
BasedOnStyles = Vale, write-good
```

---

## Common Utilities You'll Need

Add these to `src/utils.py`:

```python
def extract_markdown_links(content: str) -> List[str]:
    """Extract all links from markdown content."""
    import re
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    return [match[1] for match in re.findall(pattern, content)]

def extract_markdown_images(content: str) -> List[Dict]:
    """Extract all images with alt text from markdown."""
    import re
    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    matches = re.findall(pattern, content)
    return [{"alt_text": m[0], "src": m[1]} for m in matches]

def extract_code_blocks(content: str) -> List[Dict]:
    """Extract code blocks with language and line numbers."""
    import re
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    return [{"language": m[0] or "text", "code": m[1]} for m in matches]

async def is_url_accessible(url: str) -> bool:
    """Check if URL is accessible."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(url, timeout=5.0, follow_redirects=True)
            return response.status_code < 400
    except:
        return False
```

---

## Progress Tracking

Update this checklist as you implement:

- [ ] docmgr_assess_quality
- [ ] docmgr_validate_docs
- [ ] docmgr_map_changes
- [ ] docmgr_track_dependencies
- [ ] docmgr_bootstrap
- [ ] docmgr_migrate
- [ ] docmgr_sync

---

**Last Updated**: 2025-01-13
