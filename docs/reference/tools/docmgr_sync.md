# docmgr_sync

Orchestrate complete documentation sync: detect changes, validate, assess quality, optionally update baselines.

## Purpose

High-level orchestration tool that combines change detection, affected documentation mapping, validation, quality assessment, and optional baseline updates in a single operation. Provides comprehensive documentation health report.

## When to use

- After code changes to get complete documentation impact analysis
- After updating documentation to reset baselines
- Regular documentation health checks
- As part of CI/CD pipeline for doc quality gates
- Before releases to ensure doc-code sync

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |
| `mode` | string | No | `"check"` | `"check"` (read-only) or `"resync"` (update baselines) |
| `docs_path` | string | No | `null` | Override docs path from config |

## Output

```json
{
  "status": "sync_complete",
  "mode": "check",
  "timestamp": "2025-11-20T22:30:15.123456",
  "changes": {
    "detected": true,
    "changed_files": {
      "code": ["src/api.py"],
      "documentation": [],
      "asset": [],
      "config": []
    },
    "affected_docs": {
      "docs/api.md": ["src/api.py"]
    }
  },
  "validation": {
    "status": "issues_found",
    "total_issues": 5,
    "errors": 2,
    "warnings": 3
  },
  "quality": {
    "overall_score": "fair",
    "criteria_scores": {
      "relevance": "good",
      "accuracy": "fair",
      "consistency": "good"
    }
  },
  "baseline_updated": false,
  "recommendations": [
    "Update docs/api.md to reflect changes in src/api.py",
    "Fix 2 validation errors before next release",
    "Consider documenting 15 undocumented public APIs"
  ]
}
```

## Examples

### Check mode (read-only analysis)

```python
await mcp.call_tool("docmgr_sync", {
  "project_path": "/path/to/project",
  "mode": "check"
})
```

### Resync mode (analysis + baseline update)

```python
await mcp.call_tool("docmgr_sync", {
  "project_path": "/path/to/project",
  "mode": "resync"
})
```

### Custom docs path

```python
await mcp.call_tool("docmgr_sync", {
  "project_path": "/path/to/project",
  "mode": "check",
  "docs_path": "documentation"
})
```

## Modes explained

### `mode="check"` (default)

**Read-only analysis**

1. Detect code/doc changes (checksum mode)
2. Map changed code to affected docs
3. Run validation checks
4. Assess documentation quality
5. Generate comprehensive report

**Does NOT modify baselines**

**Use when**:
- Checking documentation status after code changes
- Running in CI/CD for quality gates
- Investigating documentation drift
- Before deciding whether to update docs or baselines

### `mode="resync"`

**Full sync with baseline update**

1. Detect code/doc changes (checksum mode)
2. Map changed code to affected docs
3. Run validation checks
4. Assess documentation quality
5. **Update all baselines atomically**
6. Generate comprehensive report

**Modifies baselines** (repo-baseline.json, symbol-baseline.json, dependencies.json)

**Use when**:
- After updating documentation to match code changes
- Resetting baseline to current "clean" state
- After fixing validation issues
- Establishing new baseline after refactoring

## What gets orchestrated

### 1. Change detection
- Runs `docmgr_detect_changes` with checksum mode
- Categorizes changes by type (code, docs, assets, etc.)
- Maps changed code to affected documentation

### 2. Validation
- Runs `docmgr_validate_docs` with default checks
- Reports broken links, missing assets, syntax errors
- Checks convention compliance

### 3. Quality assessment
- Runs `docmgr_assess_quality` with all 7 criteria
- Provides scores and actionable findings
- Identifies quality improvement opportunities

### 4. Baseline update (resync mode only)
- Runs `docmgr_update_baseline`
- Updates all three baseline files atomically
- Resets change detection to current state

## Sync workflow comparison

### Manual workflow (individual tools)
```
1. docmgr_detect_changes → see what changed
2. docmgr_validate_docs → find issues
3. docmgr_assess_quality → check quality
4. docmgr_update_baseline → reset baselines
```

### Automated workflow (sync tool)
```
1. docmgr_sync mode="check" → comprehensive report
   (or mode="resync" to include baseline update)
```

## Notes

- **Mode matters**: `check` is read-only, `resync` modifies baselines
- **Comprehensive**: Combines 3-4 separate tool operations
- **Performance**: Slower than individual tools (runs multiple analyses)
- **Idempotent**: Safe to run multiple times
- **Prerequisites**: Requires `.doc-manager.yml` and baselines
- **Root README**: Includes root README.md if `include_root_readme: true` in config

## Typical workflows

### After code changes

```
1. Make code changes
2. Run docmgr_sync mode="check"
3. Review affected_docs and recommendations
4. Update documentation based on report
5. Run docmgr_sync mode="resync" to update baselines
```

### Regular health checks

```
1. Run docmgr_sync mode="check" weekly/monthly
2. Track quality scores over time
3. Address validation issues
4. Monitor documentation drift
```

### CI/CD integration

```yaml
# Example: GitHub Actions
- name: Check documentation sync
  run: |
    # Fails if docs are out of sync with code
    result=$(docmgr_sync --mode check)
    if [[ $(echo $result | jq '.changes.detected') == "true" ]]; then
      echo "Documentation out of sync with code"
      exit 1
    fi
```

## When to use which tool

| Scenario | Tool | Why |
|----------|------|-----|
| Quick change check only | `docmgr_detect_changes` | Faster, focused |
| Just validation | `docmgr_validate_docs` | Specific check |
| Just quality assessment | `docmgr_assess_quality` | Quality metrics only |
| Just baseline update | `docmgr_update_baseline` | Direct update |
| **Comprehensive analysis** | **`docmgr_sync mode="check"`** | **All-in-one report** |
| **Analysis + baseline update** | **`docmgr_sync mode="resync"`** | **Complete sync** |

## See also

- [docmgr_detect_changes](docmgr_detect_changes.md) - Change detection only
- [docmgr_validate_docs](docmgr_validate_docs.md) - Validation only
- [docmgr_assess_quality](docmgr_assess_quality.md) - Quality assessment only
- [docmgr_update_baseline](docmgr_update_baseline.md) - Baseline update only
- [Workflows guide](../../guides/workflows.md)
