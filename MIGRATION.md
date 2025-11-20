# Migration Guide: v1.0.x → v1.1.0

This guide helps you migrate from doc-manager v1.0.x to the new 7-tool architecture in v1.1.0.

## Overview

**v1.1.0 introduces a unified, cleaner architecture:**
- 10 tools → 7 tools (10-tool design had overlaps and unclear responsibilities)
- Unified initialization via `docmgr_init`
- Explicit read-only vs write operations
- Atomic baseline updates via `docmgr_update_baseline`
- Mode-based sync (`check` vs `resync`)

## Breaking Changes

### None! 🎉

All v1.0.x tools remain functional with **deprecation warnings**. They will be removed in v2.0.

## Deprecated Tools

| Old Tool (v1.0.x) | Status | Replacement (v1.1.0) |
|-------------------|--------|----------------------|
| `docmgr_initialize_config` | ⚠️ Deprecated | `docmgr_init` (mode="existing") |
| `docmgr_initialize_memory` | ⚠️ Deprecated | `docmgr_init` (mode="existing") |
| `docmgr_bootstrap` | ⚠️ Deprecated | `docmgr_init` (mode="bootstrap") |
| `docmgr_map_changes` | ⚠️ Deprecated | `docmgr_detect_changes` (read-only) or `docmgr_sync` |

## Migration Scenarios

### Scenario 1: Project Initialization

**Old approach (v1.0.x):**
```python
# Step 1: Initialize config
await docmgr_initialize_config({
    "project_path": "/path/to/project",
    "platform": "mkdocs"
})

# Step 2: Initialize memory
await docmgr_initialize_memory({
    "project_path": "/path/to/project"
})

# Step 3: Track dependencies (if needed)
await docmgr_track_dependencies({
    "project_path": "/path/to/project",
    "docs_path": "docs"
})
```

**New approach (v1.1.0):**
```python
# Single unified initialization
await docmgr_init({
    "project_path": "/path/to/project",
    "mode": "existing",
    "platform": "mkdocs",  # optional, auto-detected
    "docs_path": "docs"
})
```

**Benefits:**
- ✅ Single call instead of 2-3
- ✅ Dependency tracking included automatically
- ✅ Atomic operation (all or nothing)
- ✅ Clearer semantics

### Scenario 2: Bootstrap Fresh Documentation

**Old approach (v1.0.x):**
```python
# Bootstrap creates docs + config + memory
await docmgr_bootstrap({
    "project_path": "/path/to/project",
    "platform": "hugo",
    "docs_path": "docs"
})

# Then manually track dependencies
await docmgr_track_dependencies({
    "project_path": "/path/to/project",
    "docs_path": "docs"
})
```

**New approach (v1.1.0):**
```python
# Single call with mode="bootstrap"
await docmgr_init({
    "project_path": "/path/to/project",
    "mode": "bootstrap",
    "platform": "hugo",
    "docs_path": "docs"
})
```

**Benefits:**
- ✅ Dependency tracking included automatically
- ✅ Consistent with `mode="existing"` pattern

### Scenario 3: Change Detection

**Old approach (v1.0.x):**
```python
# map_changes writes to symbol-baseline.json (side effect!)
result = await docmgr_map_changes({
    "project_path": "/path/to/project",
    "mode": "checksum",
    "include_semantic": True
})

# Changes AND baseline update happened (not obvious)
```

**Problems with old approach:**
- ❌ Unclear that baselines are being modified
- ❌ Marked as `readOnlyHint=False` but often used for read-only queries
- ❌ Semantic analysis has side effect (writes baseline)

**New approach (v1.1.0):**
```python
# Detect changes (pure read-only, NEVER writes)
result = await docmgr_detect_changes({
    "project_path": "/path/to/project",
    "mode": "checksum",
    "include_semantic": True  # Still read-only!
})

# Explicitly update baselines when ready
await docmgr_update_baseline({
    "project_path": "/path/to/project",
    "docs_path": "docs"
})
```

**Benefits:**
- ✅ Clear separation: read-only detection vs explicit updates
- ✅ `docmgr_detect_changes` has `readOnlyHint=True` (accurate)
- ✅ No surprise side effects
- ✅ Can detect changes multiple times without affecting baselines

### Scenario 4: Documentation Sync

**Old approach (v1.0.x):**
```python
# Sync with mode="reactive" or mode="proactive"
result = await docmgr_sync({
    "project_path": "/path/to/project",
    "mode": "reactive",  # or "proactive"
    "docs_path": "docs"
})

# Then manually update baselines
await docmgr_initialize_memory({
    "project_path": "/path/to/project"
})
```

**Problems:**
- ❌ Unclear what "reactive" vs "proactive" means
- ❌ Baselines not updated atomically
- ❌ Manual baseline update required

**New approach (v1.1.0):**
```python
# Option 1: Check mode (read-only analysis)
result = await docmgr_sync({
    "project_path": "/path/to/project",
    "mode": "check",
    "docs_path": "docs"
})
# Analyzes changes, validates docs, assesses quality (no baseline updates)

# Option 2: Resync mode (analysis + update baselines)
result = await docmgr_sync({
    "project_path": "/path/to/project",
    "mode": "resync",
    "docs_path": "docs"
})
# Does everything check does + atomically updates all baselines
```

**Benefits:**
- ✅ Clear semantics: `check` = read-only, `resync` = update
- ✅ Atomic baseline updates (all 3 files updated together)
- ✅ No manual baseline refresh needed

## Key Concepts

### Read-Only Guarantee

**v1.1.0 introduces explicit read-only guarantees:**

| Tool | Read-Only? | Writes Baselines? |
|------|------------|-------------------|
| `docmgr_detect_changes` | ✅ Yes | ❌ Never |
| `docmgr_detect_platform` | ✅ Yes | ❌ Never |
| `docmgr_validate_docs` | ✅ Yes | ❌ Never |
| `docmgr_assess_quality` | ✅ Yes | ❌ Never |
| `docmgr_sync` (mode="check") | ✅ Yes | ❌ Never |
| `docmgr_sync` (mode="resync") | ❌ No | ✅ Yes (all 3) |
| `docmgr_update_baseline` | ❌ No | ✅ Yes (all 3) |
| `docmgr_init` | ❌ No | ✅ Yes (creates) |

**Why this matters:**
- You can safely call `docmgr_detect_changes` multiple times without side effects
- Clear when baselines are being modified
- Enables better caching and concurrent operations

### Atomic Baseline Updates

**v1.1.0 updates all 3 baselines atomically:**

1. `repo-baseline.json` (file checksums)
2. `symbol-baseline.json` (TreeSitter code symbols)
3. `dependencies.json` (code-to-docs mappings)

**Old approach (v1.0.x):**
```python
# Each update was separate
await docmgr_initialize_memory(...)  # Updates repo + symbol
await docmgr_track_dependencies(...) # Updates dependencies

# Risk: Inconsistent state if one fails
```

**New approach (v1.1.0):**
```python
# Single atomic update
await docmgr_update_baseline({
    "project_path": "/path/to/project",
    "docs_path": "docs"
})
# All 3 baselines updated together or none
```

## Migration Checklist

### For Existing Scripts/Integrations

- [ ] Replace `docmgr_initialize_config` + `docmgr_initialize_memory` with `docmgr_init(mode="existing")`
- [ ] Replace `docmgr_bootstrap` with `docmgr_init(mode="bootstrap")`
- [ ] Replace `docmgr_map_changes` with `docmgr_detect_changes` (for read-only detection)
- [ ] Update `docmgr_sync` calls to use `mode="check"` or `mode="resync"` (instead of `"reactive"`/`"proactive"`)
- [ ] Add explicit `docmgr_update_baseline` calls after doc updates (instead of `docmgr_initialize_memory`)

### For CI/CD Pipelines

**Old pipeline (v1.0.x):**
```yaml
- name: Detect stale docs
  run: |
    docmgr_map_changes --project-path .
```

**New pipeline (v1.1.0):**
```yaml
- name: Detect stale docs (read-only)
  run: |
    docmgr_detect_changes --project-path . --mode checksum

- name: Sync documentation (if changes detected)
  run: |
    docmgr_sync --project-path . --mode resync --docs-path docs
```

### For MCP Clients

If you're using an MCP client (like Claude Desktop), update tool calls:

**Old:**
```json
{
  "name": "docmgr_initialize_config",
  "arguments": {...}
}
```

**New:**
```json
{
  "name": "docmgr_init",
  "arguments": {
    "mode": "existing",
    ...
  }
}
```

## Testing Your Migration

1. **Install v1.1.0:**
   ```bash
   pip install --upgrade doc-manager-mcp
   ```

2. **Verify backward compatibility:**
   ```bash
   # Old tools should still work (with deprecation warnings)
   pytest tests/
   ```

3. **Test new tools:**
   ```bash
   # Run integration tests for new architecture
   pytest tests/integration/test_7_tool_workflow.py -v
   ```

4. **Check for deprecation warnings:**
   ```python
   # Should see warnings if using old tools
   result = await docmgr_initialize_config(...)
   # Warning: docmgr_initialize_config is deprecated. Use docmgr_init instead.
   ```

## Timeline

- **v1.1.0** (Current): Old tools deprecated but functional
- **v1.2.0** (Planned): Old tools removed, breaking changes for those who didn't migrate
- **v2.0.0** (Future): Clean 7-tool architecture only

**Recommendation:** Migrate before v1.2.0 release.

## Getting Help

- **Issues:** Report migration problems at [GitHub Issues](https://github.com/yourusername/doc-manager/issues)
- **Questions:** Tag with `migration` label
- **Spec Reference:** See `specs/002-tool-architecture-refactor.md` for technical details

## FAQ

### Q: Do I need to migrate immediately?

**A:** No. v1.1.0 maintains backward compatibility. Old tools work with deprecation warnings. But we recommend migrating before v2.0.

### Q: Will my existing baselines work with v1.1.0?

**A:** Yes! Baseline file formats are unchanged. No migration needed.

### Q: What if I like the old `docmgr_map_changes` behavior?

**A:** Use `docmgr_detect_changes` for detection, then `docmgr_update_baseline` to update baselines explicitly. This gives you the same result with clearer semantics.

### Q: Can I mix old and new tools?

**A:** Yes, but not recommended. Stick to one pattern for consistency.

### Q: What about `docmgr_track_dependencies`?

**A:** Still available! It's called automatically by `docmgr_init` and `docmgr_update_baseline`, but you can still call it directly if needed.

## Examples

### Complete Migration Example

**Before (v1.0.x):**
```python
# Initialize
await docmgr_initialize_config({"project_path": "/app"})
await docmgr_initialize_memory({"project_path": "/app"})

# Detect changes
changes = await docmgr_map_changes({
    "project_path": "/app",
    "mode": "checksum"
})

# Sync
await docmgr_sync({
    "project_path": "/app",
    "mode": "reactive"
})
```

**After (v1.1.0):**
```python
# Initialize
await docmgr_init({
    "project_path": "/app",
    "mode": "existing"
})

# Detect changes (read-only)
changes = await docmgr_detect_changes({
    "project_path": "/app",
    "mode": "checksum"
})

# Sync with baseline update
await docmgr_sync({
    "project_path": "/app",
    "mode": "resync"
})
```

---

**Ready to migrate?** Start with replacing initialization calls, then move to change detection and sync. The 7-tool architecture is clearer and more maintainable. You've got this! 🚀
