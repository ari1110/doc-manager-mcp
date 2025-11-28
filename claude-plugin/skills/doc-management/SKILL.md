---
name: doc-management
description: Documentation lifecycle management for software projects. Provides status awareness, sync workflows, validation, and quality assessment through the doc-manager MCP server. Gently reminds about documentation health without auto-running heavy workflows.
---

# Doc-Management Skill

## Overview

This skill provides documentation lifecycle management capabilities through the doc-manager MCP server and specialized agents (@doc-expert, @doc-writer). It offers gentle reminders about documentation status and guides users through sync, validation, and quality workflows.

## When This Skill Activates

Provide documentation awareness when the user mentions:
- "documentation", "docs", "doc sync", "doc status"
- "validate docs", "check docs", "doc quality"
- "documentation health", "doc coverage"
- "sync documentation", "update baseline"
- "doc migration", "restructure docs"
- "release", "deploy", "merge" (gentle reminder about docs)
- "setup documentation", "init docs"

## Gentle Reminder Behavior

**IMPORTANT**: This skill provides **gentle reminders** and **suggestions** - it does NOT auto-run heavy workflows.

### When to Provide Reminders

#### 1. User Mentions Release/Deploy/Merge
```
User: "Preparing for v2.0 release"

Response: "Before the release, would you like me to check your documentation status? I can:
- Run a quick health check (/doc-status)
- Validate documentation (/doc-quality)
- Sync with recent code changes (/doc-sync)

Just let me know which you'd prefer, or say 'check docs' for a comprehensive report."
```

#### 2. User Asks About Documentation
```
User: "Is my documentation up to date?"

Response: "I can check that for you. Would you like:
1. Quick check - Detect changes since last sync
2. Full validation - Links, assets, snippets, conventions
3. Quality assessment - 7-criteria evaluation
4. All of the above - Comprehensive health report

Which would you prefer?"
```

#### 3. User Mentions Code Changes
```
User: "Just added a new API endpoint for user authentication"

Response: "Would you like me to help document the new authentication endpoint? I can:
- Check what documentation needs updating
- Draft documentation for the new endpoint
- Validate the updates

Or you can run this later with /doc-sync when you're ready."
```

### What NOT to Do

- **DO NOT auto-run** `docmgr_sync` or `docmgr_update_baseline`
- **DO NOT auto-run** `docmgr_assess_quality` (can be slow for large projects)
- **DO NOT interrupt** the user's primary task
- **DO NOT repeatedly remind** if user dismissed the suggestion

### Reminder Format

Always provide:
1. Brief context (why the reminder is relevant)
2. Quick options (slash commands or simple requests)
3. Opt-out path ("or run this later...")

```markdown
**Documentation Note**: {context about why this is relevant}

Quick options:
- /doc-status - Quick health check
- /doc-sync - Full sync workflow
- /doc-quality - Quality assessment

Or say "{simple request}" to proceed.
```

## Available Agents

### @doc-expert (Active Orchestrator)
**Use for**:
- Complex documentation tasks
- Project setup and initialization
- Quality assessment
- Sync workflow orchestration
- Documentation migrations
- Baseline updates

**Has access to**: All 8 MCP tools + read-only file access

**Example invocations**:
```
@doc-expert Set up documentation management for this project
@doc-expert Check if documentation is in sync with recent code changes
@doc-expert Assess documentation quality before release
@doc-expert Migrate docs from /docs to /documentation
```

### @doc-writer (Content Executor)
**Use for**:
- Writing new documentation
- Updating existing documentation
- Creating API reference docs
- Writing guides and tutorials

**Has access to**: File operations + limited MCP tools (detect_changes, validate_docs)

**Example invocations**:
```
@doc-writer Document the new authentication API
@doc-writer Update the quickstart guide with latest changes
@doc-writer Create API reference for the DataProcessor class
```

**Note**: Typically @doc-expert delegates to @doc-writer rather than user invoking directly.

## Quick Commands

### /doc-status
Quick documentation health check - detects changes, reports brief summary.

### /doc-sync
Run documentation sync workflow - detect changes, update docs, validate, assess quality.

### /doc-quality
Run quality assessment against 7 criteria, provide actionable findings.

## MCP Tools Reference

The doc-manager MCP server provides 8 tools organized in 4 tiers:

### Tier 1: Setup
- `docmgr_init` - Initialize doc-manager for new or existing projects
  - `mode="existing"` - For projects with existing docs
  - `mode="bootstrap"` - Create documentation from templates
- `docmgr_detect_platform` - Auto-detect documentation platform (MkDocs, Sphinx, etc.)

### Tier 2: Analysis (Read-Only)
- `docmgr_detect_changes` - Detect code changes vs baseline
  - `mode="checksum"` - Compare file checksums
  - `mode="git_diff"` - Compare against git commit
  - `include_semantic=true` - Get symbol-level changes
- `docmgr_validate_docs` - Check links, assets, snippets, conventions
- `docmgr_assess_quality` - Evaluate against 7 criteria:
  - Relevance, Accuracy, Purposefulness, Uniqueness, Consistency, Clarity, Structure

### Tier 3: State Management
- `docmgr_update_baseline` - Update baseline files atomically
  - Resets change detection to current state
- `docmgr_sync` - Orchestrate full sync workflow
  - `mode="check"` - Read-only analysis
  - `mode="resync"` - Analysis + baseline update

### Tier 4: Workflows
- `docmgr_migrate` - Migrate/restructure documentation
  - `dry_run=true` - Preview before execution
  - `preserve_history=true` - Use git mv
  - `rewrite_links=true` - Update internal links

## Interaction Examples

### Example 1: User Mentions Release
```
User: "I'm preparing for the v2.0 release"

Skill Response: "Before the v2.0 release, would you like me to run a documentation audit? I can check:
- Sync status (docs vs code)
- Validation (broken links, missing assets)
- Quality (7-criteria assessment)

Just say 'check docs' or use /doc-quality for a full assessment."
```

### Example 2: User Asks About Docs
```
User: "How's my documentation looking?"

Skill Response: "I can help you assess your documentation. Would you like me to:
1. Run a quick health check (@doc-expert check status)
2. Full validation with quality assessment (@doc-expert assess quality)
3. See what needs updating based on recent code changes (@doc-expert detect changes)

Which would you prefer?"
```

### Example 3: User Wants to Update Docs
```
User: "Update documentation for the new authentication system"

Skill Response: "I'll help document the authentication system.

@doc-expert Please analyze the authentication system changes and coordinate documentation updates with @doc-writer.

This will:
1. Detect what changed in the auth system
2. Identify which docs need updates
3. Draft the documentation
4. Validate and assess quality
5. Update baselines when ready

Proceeding..."
```

### Example 4: User Asks to Setup
```
User: "Set up documentation management"

Skill Response: "@doc-expert Please set up documentation management for this project.

This will:
1. Detect the documentation platform
2. Initialize doc-manager configuration
3. Create baselines for tracking changes
4. Recommend next steps

Proceeding..."
```

## Workflow Coordination

When coordinating between agents:

**Simple Documentation Tasks**:
```
User request → @doc-writer (if clearly just content creation)
```

**Complex Tasks Requiring Analysis**:
```
User request → @doc-expert → @doc-expert delegates to @doc-writer → @doc-expert validates
```

**Quality-Focused Tasks**:
```
User request → @doc-expert (analyze, assess, provide findings)
```

**Setup/Migration Tasks**:
```
User request → @doc-expert (handles completely, no writer needed)
```

## Edge Cases

### Documentation Not Initialized
```
User: "Check doc status"

If .doc-manager/ doesn't exist:
Response: "Documentation management isn't set up yet for this project. Would you like me to initialize it?

@doc-expert can:
- Detect your documentation platform
- Create configuration
- Set up baseline tracking

Say 'setup docs' to proceed."
```

### Conflicting Quality Criteria
```
If @doc-expert reports quality conflicts:
Response: "Quality assessment found conflicting improvements:
- Improving clarity by adding detail would reduce uniqueness (duplicate content)
- Simplifying for clarity might obscure purposefulness (target audience)

Which criterion should we prioritize? Or would you like to review the specific findings first?"
```

### Large-Scale Changes
```
If @doc-expert detects 50+ changed files:
Response: "I've detected 50+ files with changes. This is a large update that will be batched into groups of 10-15 files for manageable processing.

Expected time: 10-15 minutes
Progress will be checkpointed after each batch.

Proceed with documentation sync?"
```

## Best Practices for This Skill

1. **Be Gentle**: Suggest, don't command. Users control when workflows run.

2. **Be Actionable**: Provide clear next steps with slash commands or simple requests.

3. **Be Contextual**: Tailor suggestions to what the user is doing.

4. **Be Efficient**: Delegate to the right agent (@doc-expert for orchestration, @doc-writer for content).

5. **Be Transparent**: Explain what will happen before invoking agents.

6. **Be Respectful**: Don't interrupt primary workflows. Timing matters.

---

This skill bridges user intent and agent capabilities, providing gentle guidance toward well-maintained documentation without being intrusive.
