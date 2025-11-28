---
description: Quick documentation health check
---

# Quick Documentation Status Check

Run a quick documentation health check for the current project.

@doc-expert Please provide a quick documentation status check.

This should include:
1. Detect if doc-manager is initialized (check for .doc-manager/)
2. If initialized, run `docmgr_detect_changes` to check for changes since last sync
3. Report brief summary:
   - Project platform
   - Number of changed files
   - Affected documentation files
   - Sync status (in_sync | out_of_sync | unknown)

Format the output concisely:

```
## Documentation Status

**Platform**: {platform}
**Last Sync**: {timestamp or "unknown"}

### Quick Stats
- Changed Files: {count}
- Affected Docs: {count}

### Status: {in_sync | out_of_sync | not_initialized}

### Quick Actions
- /doc-sync - Sync with code changes
- /doc-quality - Full quality assessment
```

If not initialized:
```
## Documentation Status

**Status**: Not initialized

### Setup
Run `@doc-expert Set up documentation management` to initialize.
```
