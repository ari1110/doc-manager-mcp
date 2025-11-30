# Workflow Standard Operating Procedures

Detailed procedures for common documentation management workflows.

## WF1: Health Check

**Purpose**: Quick assessment of documentation sync status.

**When to Use**: User asks about doc status, at session start, before major work.

### Procedure

```
Step 1: Check Initialization
├── Look for .doc-manager/ directory
├── If missing → Offer to initialize (exit this workflow)
└── If present → Continue

Step 2: Detect Changes
├── Run: docmgr_detect_changes(mode="checksum")
├── Capture: changed_files, affected_docs
└── Note: days since last baseline update

Step 3: Report Status
├── Format: Status Report template
├── Include: sync status, counts, recommendations
└── Offer: /doc-sync or /doc-quality as next steps

Step 4: Exit
└── Wait for user decision
```

### Example Output

```markdown
## Documentation Status

**Project**: my-project | **Platform**: mkdocs
**Last Sync**: 3 days ago | **Status**: out_of_sync

| Metric | Count |
|--------|-------|
| Changed code files | 8 |
| Affected doc files | 5 |

### Recommended Actions
1. Run /doc-sync to update documentation
2. Focus on: docs/api.md, docs/guide.md

### Quick Commands
- /doc-sync - Full sync workflow
- /doc-quality - Quality assessment
```

---

## WF2: Full Sync

**Purpose**: Synchronize documentation with code changes.

**When to Use**: User requests sync, significant code changes detected, pre-release.

### Procedure

```
Step 1: Detect Changes
├── Run: docmgr_detect_changes(mode="checksum", include_semantic=true)
├── Capture: changed files by category, symbol changes
└── Calculate: total scope

Step 2: Analyze Scope
├── <15 files → Single batch
├── 15-50 files → Batch into groups of 10-15
└── >50 files → Warn user, get confirmation before proceeding

Step 3: For Each Batch
│
├── 3a: Read Changed Code
│   ├── Read source files in batch
│   └── Understand changes (new functions, modified signatures, etc.)
│
├── 3b: Delegate to doc-writer
│   ├── Provide: Context, Platform, File list, Conventions
│   └── Request: Update docs, validate before returning
│
├── 3c: Receive Results
│   ├── Review completion report
│   └── Note any failures
│
├── 3d: Validate
│   └── Run: docmgr_validate_docs(check_links=true, check_assets=true, check_snippets=true)
│
├── 3e: Assess Quality
│   ├── Run: docmgr_assess_quality
│   └── Check for "Poor" scores
│
└── 3f: Quality Gate
    ├── All Fair or better → Proceed to next batch
    ├── Any Poor → Provide feedback, request revision
    └── After 3 iterations still Poor → Escalate to user

Step 4: Confirm Baseline Update
├── Ask: "Documentation updated. Update baseline to mark as synced?"
├── If yes → Run: docmgr_update_baseline
└── If no → Report completion without baseline update

Step 5: Report Completion
└── Summary: files updated, quality scores, baseline status
```

### Batching Strategy

```
Total Files | Strategy
-----------|----------
1-14       | Single batch
15-30      | 2 batches (15, remainder)
31-45      | 3 batches (15, 15, remainder)
46-50      | 4 batches (12-13 each)
>50        | Warn user first, then batch by 15
```

### Quality Feedback Template

```
Quality assessment found issues:

**Accuracy** (score: poor):
- docs/api.md:45 - Parameter type should be dict, not str
- docs/api.md:67 - Return type missing

**Clarity** (score: fair):
- docs/guide.md:23 - Add code example for this section

Please revise these sections. Focus on Accuracy issues first.
```

---

## WF3: Quality Assessment

**Purpose**: Comprehensive evaluation of documentation quality.

**When to Use**: User requests quality check, pre-release audit, periodic health check.

### Procedure

```
Step 1: Run Assessment
├── Run: docmgr_assess_quality (all 7 criteria)
└── Capture: scores and findings per criterion

Step 2: Run Validation
├── Run: docmgr_validate_docs (all checks enabled)
└── Capture: broken links, missing assets, snippet issues

Step 3: Compile Report
├── Overall assessment (excellent/good/fair/poor)
├── Per-criterion breakdown with issue counts
├── Specific issues with file:line references
├── Validation results
└── Prioritized recommendations

Step 4: Offer Resolution
├── If issues found → Offer to fix via doc-writer delegation
└── If clean → Confirm good status, offer baseline update if needed
```

### Report Template

```markdown
## Quality Assessment

**Overall**: fair

### Scores by Criterion
| Criterion | Score | Issues |
|-----------|-------|--------|
| Relevance | good | 0 |
| Accuracy | poor | 3 |
| Purposefulness | good | 0 |
| Uniqueness | fair | 2 |
| Consistency | fair | 4 |
| Clarity | poor | 5 |
| Structure | good | 0 |

### Validation Results
- **Links**: 45 checked, 2 broken
- **Assets**: 12 checked, 0 missing
- **Code Snippets**: 23 checked, 1 syntax error

### Critical Issues (Poor Scores)

**Accuracy**:
- docs/api.md:45 - `process_data()` return type is `Result`, not `dict`
- docs/api.md:89 - Missing parameter `timeout` added in v2.0
- docs/api.md:102 - Exception `TimeoutError` not documented

**Clarity**:
- docs/guide.md:12-45 - No code examples in Getting Started
- docs/guide.md:67 - Installation steps unclear
- docs/api.md:150 - Complex function needs usage example
- docs/config.md:23 - Configuration options need descriptions
- docs/config.md:45 - Missing default values

### Recommendations
1. **High Priority**: Fix Accuracy issues in docs/api.md
2. **High Priority**: Add code examples to docs/guide.md
3. **Medium**: Resolve broken links
4. **Medium**: Fix code snippet syntax error

Would you like me to help fix these issues?
```

---

## WF4: Release Readiness

**Purpose**: Determine if documentation is ready for release.

**When to Use**: Pre-release check, merge to main, version tagging.

### Procedure

```
Step 1: Check Sync Status
├── Run: docmgr_sync(mode="check")
├── If out of sync → WARN: "Documentation out of sync. Recommend running /doc-sync first."
└── Capture: changed files count

Step 2: Assess Quality
├── Run: docmgr_assess_quality
└── Capture: all scores

Step 3: Validate
├── Run: docmgr_validate_docs
└── Capture: critical issues (broken links, etc.)

Step 4: Evaluate Readiness
│
├── READY if:
│   ├── Accuracy is Good
│   ├── No Poor scores
│   └── No critical validation failures
│
├── READY WITH NOTES if:
│   ├── Accuracy is Fair or better
│   ├── Max 1 Fair score in other criteria
│   └── Minor validation issues only
│
└── NOT READY if:
    ├── Accuracy is Poor
    ├── 2+ Poor scores
    └── Critical validation failures (broken links to key resources)

Step 5: Report Recommendation
├── Clear verdict: READY / READY WITH NOTES / NOT READY
├── Reasoning: specific issues affecting decision
└── If NOT READY: specific actions needed
```

### Readiness Report Template

```markdown
## Release Readiness: NOT READY

### Blocking Issues
1. **Accuracy: Poor** - 3 type mismatches in API documentation
2. **Validation**: 2 broken links to critical resources

### Required Actions
1. Fix docs/api.md accuracy issues (lines 45, 89, 102)
2. Fix broken links:
   - docs/guide.md:23 → ../api/auth.md (file moved)
   - docs/guide.md:67 → https://example.com/setup (404)

### After Fixing
Run `/doc-quality` to re-assess, then `/doc-sync` to update baseline.

Would you like me to help fix these issues now?
```

---

## WF5: Project Setup

**Purpose**: Initialize doc-manager for a new project.

**When to Use**: First-time setup, user requests initialization.

### Procedure

```
Step 1: Detect Platform
├── Run: docmgr_detect_platform
├── Capture: detected platform, confidence, alternatives
└── If multiple detected → Present options to user

Step 2: Present Findings
├── Show: detected platform
├── Show: proposed configuration (docs_path, sources, excludes)
└── Ask: "Does this look correct? Any adjustments?"

Step 3: Get Confirmation
├── If user confirms → Proceed
├── If user adjusts → Update configuration
└── If user cancels → Exit

Step 4: Initialize
├── Run: docmgr_init(mode="existing", platform=confirmed_platform, ...)
└── Capture: created files

Step 5: Report Completion
├── What was created (.doc-manager/, config, baselines)
├── Next steps (run /doc-status, /doc-quality)
└── Quick reference to commands
```

### Setup Report Template

```markdown
## Documentation Management Initialized

**Platform**: mkdocs
**Docs Path**: docs/
**Sources**: src/**/*.py

### Created
- `.doc-manager.yml` - Configuration
- `.doc-manager/memory/repo-baseline.json` - File tracking
- `.doc-manager/memory/symbol-baseline.json` - Symbol tracking
- `.doc-manager/memory/dependencies.json` - Doc dependencies

### Next Steps
1. Run `/doc-status` to see current sync state
2. Run `/doc-quality` for initial quality assessment
3. Run `/doc-sync` if updates are needed

### Quick Commands
| Command | Purpose |
|---------|---------|
| /doc-status | Check sync status |
| /doc-sync | Sync docs with code |
| /doc-quality | Quality assessment |
```

---

## WF6: Config Tuning

**Purpose**: Optimize doc-manager configuration for project needs.

**When to Use**: After setup when accuracy is low, when project type doesn't match strategy, when adding new source directories, when framework symbols inflate coverage.

### Procedure

```
Step 1: Assess Current State
├── Run: docmgr_assess_quality
├── Capture: api_coverage percentage, undocumented symbols count
├── Read: .doc-manager.yml to check current config
└── Note: any existing api_coverage settings

Step 2: Identify Project Type
├── Check pyproject.toml/package.json for dependencies
├── Look for indicators:
│   ├── MCP Server → mcp dependency, FastMCP imports
│   ├── Library → __all__ exports, pip installable
│   ├── CLI → argparse/click/typer
│   └── Application → framework configs
└── Classify: library | mcp_server | cli | application

Step 3: Analyze Coverage Issues
├── If coverage is low (<50%):
│   ├── Check if framework symbols are included
│   ├── Identify which preset would help
│   └── Check if strategy matches project type
├── If coverage is 0%:
│   ├── Check if all_only strategy + no __all__
│   └── Determine if this is correct for project type
└── List specific symbols inflating count

Step 4: Recommend Changes
├── Strategy recommendation based on project type:
│   ├── Library → all_then_underscore
│   ├── MCP Server → all_only
│   ├── CLI → all_only or underscore_only
│   └── Application → all_only
├── Preset recommendation based on dependencies:
│   ├── pydantic in deps → suggest pydantic preset
│   ├── django in deps → suggest django preset
│   ├── pytest in deps → suggest pytest preset
│   └── etc.
└── Present options to user with rationale

Step 5: Apply Changes
├── If user approves → Edit .doc-manager.yml
├── Update api_coverage section:
│   ├── strategy: recommended_strategy
│   ├── preset: recommended_preset
│   └── exclude_symbols: [custom patterns if needed]
└── Run: docmgr_update_baseline

Step 6: Verify Improvement
├── Run: docmgr_assess_quality again
├── Compare: old coverage vs new coverage
├── Check: undocumented symbols list makes sense
└── Report: improvement summary
```

### Config Tuning Report Template

```markdown
## Config Tuning Results

**Project Type**: MCP Server
**Previous Coverage**: 26% (52/199 symbols)
**New Coverage**: 0% (0/0 public symbols)

### Changes Applied

```yaml
api_coverage:
  preset: pydantic
  strategy: all_only  # Changed from all_then_underscore
```

### Rationale

This is an MCP server - users interact via MCP protocol, not Python imports.
Using `all_only` strategy correctly reflects that there's no public Python API.

### Symbols Now Excluded

Framework symbols filtered by pydantic preset:
- Config, model_config, validators (7 symbols)

Internal symbols filtered by all_only strategy:
- Functions not in __all__ (192 symbols)

### Verification

Quality assessment now accurately reflects documentation state.
```

### Common Tuning Scenarios

#### Scenario A: Framework Symbols Inflating Count

**Symptom**: 30% coverage, many Pydantic/Django/etc. symbols undocumented

**Solution**:
```yaml
api_coverage:
  preset: pydantic  # or django, fastapi, etc.
```

#### Scenario B: MCP Server Showing Internal APIs

**Symptom**: 25% coverage on MCP server, internal functions listed

**Solution**:
```yaml
api_coverage:
  strategy: all_only
```

#### Scenario C: Test Symbols Included

**Symptom**: test_* and Test* functions in undocumented list

**Solution**:
```yaml
api_coverage:
  preset: pytest
  # OR add custom excludes:
  exclude_symbols:
    - "test_*"
    - "Test*"
```

#### Scenario D: Multiple Frameworks

**Symptom**: Using FastAPI + SQLAlchemy, need multiple presets

**Solution**:
```yaml
api_coverage:
  preset: fastapi  # Base preset
  exclude_symbols:
    # Additional SQLAlchemy patterns
    - "metadata"
    - "__table__"
    - "__tablename__"
```

### Troubleshooting

**Coverage didn't change after config update**:
1. Ensure `docmgr_update_baseline` was run
2. Check that pattern syntax is correct (fnmatch, not regex)
3. Verify preset name is spelled correctly

**Coverage is now 0% unexpectedly**:
1. Check if `all_only` strategy is set
2. Verify if `__all__` is defined in modules
3. For libraries, consider switching to `all_then_underscore`

**Preset not filtering expected symbols**:
1. Check exact symbol names vs preset patterns
2. Some patterns use wildcards (test_*), some are exact (Config)
3. Consider adding custom exclude_symbols for edge cases
