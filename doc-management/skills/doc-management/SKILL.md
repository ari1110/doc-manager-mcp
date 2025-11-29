---
name: doc-management
description: This skill should be used when the user asks to "check docs", "sync documentation", "validate docs", "assess quality", "setup documentation", or mentions "release", "deploy", "merge", or "quality checks". Provides gentle reminders about documentation health through the doc-manager MCP server without auto-running heavy workflows.
---

# Doc-Management Skill

Documentation lifecycle management for software projects through the doc-manager MCP server. This skill coordinates between specialized agents (doc-expert agent, doc-writer agent) to provide gentle documentation reminders and workflow assistance.

## Instructions

### 1. Recognize Trigger Conditions

Activate when the user mentions:
- Documentation-related terms: "documentation", "docs", "doc sync", "doc status"
- Quality checks: "validate docs", "check docs", "doc quality"
- Workflow operations: "sync documentation", "update baseline", "doc migration"
- Release context: "release", "deploy", "merge" (gentle reminder)
- Setup: "setup documentation", "init docs"

### 2. Provide Gentle Reminders (Do NOT Auto-Run)

**Critical rule**: NEVER auto-run heavy workflows. Always suggest and ask.

**When user mentions release/deploy/merge**:
- Offer documentation health check
- Suggest quick commands (/doc-status, /doc-sync, /doc-quality)
- Let user decide when to run

**When user asks about documentation status**:
- Present options (quick check vs full validation vs quality assessment)
- Wait for user to choose
- Do not assume what they want

**When user mentions code changes**:
- Mention documentation updates might be needed
- Offer to help document changes
- Suggest running later with /doc-sync if user is busy

### 3. Delegate to Appropriate Agent

**Use doc-expert agent for**:
- Complex tasks requiring orchestration
- Project setup and initialization
- Quality assessment and validation
- Sync workflow management
- Documentation migrations
- Baseline updates

**Use doc-writer agent for**:
- Simple content creation (when clearly just writing)
- Updating specific documentation files
- Creating examples or guides

**Typical flow**: User request → doc-expert agent → doc-expert delegates to doc-writer agent → doc-expert agent validates

### 4. Coordinate Workflows

**For setup tasks**:
```
User wants setup → doc-expert agent (detects platform, initializes config)
```

**For sync tasks**:
```
User wants sync → doc-expert agent (detects changes, delegates to doc-writer agent, validates, updates baseline)
```

**For quality tasks**:
```
User wants quality check → doc-expert agent (runs assessment, presents findings)
```

**For content tasks**:
```
User wants specific docs written → doc-expert agent or doc-writer agent (depending on complexity)
```

### 5. Handle Edge Cases

**If documentation not initialized**:
- Detect .doc-manager/ directory absence
- Suggest initialization
- Offer to run doc-expert agent setup workflow

**If large-scale changes detected (50+ files)**:
- Warn user about processing time
- Mention batching strategy (10-15 files at a time)
- Ask for confirmation before proceeding

**If quality criteria conflicts**:
- Present conflicting improvements to user
- Ask which criterion to prioritize
- Don't auto-fix if changes harm other criteria

### 6. Provide Actionable Feedback

**Always include**:
- Clear context (why this is relevant)
- Quick options (slash commands or simple requests)
- Opt-out path ("or run this later...")

**Example format**:
```
Documentation Note: {context}

Quick options:
- /doc-status - Quick health check
- /doc-sync - Full sync workflow
- /doc-quality - Quality assessment

Or say "{simple request}" to proceed.
```

### 7. Use Available Tools

**Quick Commands**:
- `/doc-status` - Fast health check
- `/doc-sync` - Full sync workflow
- `/doc-quality` - Quality assessment

**MCP Tools** (via agents):
- `docmgr_init` - Setup (expert only)
- `docmgr_detect_changes` - Change detection (expert and writer)
- `docmgr_validate_docs` - Validation (expert and writer)
- `docmgr_assess_quality` - Quality assessment (expert only)
- `docmgr_update_baseline` - Baseline updates (expert only)
- `docmgr_sync` - Orchestrated sync (expert only)
- `docmgr_migrate` - Migration (expert only)

## Examples

### Example 1: User Mentions Release

**User says**: "I'm preparing for the v2.0 release"

**Your response**:
```
Before the v2.0 release, would you like me to run a documentation audit? I can check:
- Sync status (docs vs code)
- Validation (broken links, missing assets)
- Quality (7-criteria assessment)

Just say 'check docs' or use /doc-quality for a full assessment.
```

**Then**: Wait for user decision, invoke appropriate agent/command when requested

---

### Example 2: User Asks About Documentation Status

**User says**: "How's my documentation looking?"

**Your response**:
```
I can help you assess your documentation. Would you like me to:
1. Run a quick health check (doc-expert agent check status)
2. Full validation with quality assessment (doc-expert agent assess quality)
3. See what needs updating based on recent code changes (doc-expert agent detect changes)

Which would you prefer?
```

**Then**: Based on choice, invoke doc-expert agent with appropriate task

---

### Example 3: User Wants to Update Documentation

**User says**: "Update documentation for the new authentication system"

**Your response**:
```
I'll help document the authentication system.

doc-expert agent Please analyze the authentication system changes and coordinate documentation updates with doc-writer agent.

This will:
1. Detect what changed in the auth system
2. Identify which docs need updates
3. Draft the documentation
4. Validate and assess quality
5. Update baselines when ready

Proceeding...
```

**Flow**: doc-expert agent detects changes → delegates to doc-writer agent → validates quality → updates baseline

---

### Example 4: User Asks to Setup Documentation Management

**User says**: "Set up documentation management"

**Your response**:
```
doc-expert agent Please set up documentation management for this project.

This will:
1. Detect the documentation platform
2. Initialize doc-manager configuration
3. Create baselines for tracking changes
4. Recommend next steps

Proceeding...
```

**Flow**: doc-expert agent detects platform → initializes → creates baselines → reports completion

---

### Example 5: Documentation Not Initialized

**User says**: "Check doc status"

**Condition**: .doc-manager/ doesn't exist

**Your response**:
```
Documentation management isn't set up yet for this project. Would you like me to initialize it?

doc-expert agent can:
- Detect your documentation platform
- Create configuration
- Set up baseline tracking

Say 'setup docs' to proceed.
```

---

### Example 6: Large-Scale Changes

**Condition**: doc-expert agent detects 50+ changed files  

**Your response**:
```
I've detected 50+ files with changes. This is a large update that will be batched into groups of 10-15 files for manageable processing.

Expected time: 10-15 minutes
Progress will be checkpointed after each batch.

Proceed with documentation sync?
```

**Then**: Wait for confirmation, invoke doc-expert agent with sync workflow if approved

---

### Example 7: Simple Content Request

**User says**: "Add a quickstart guide for the CLI"

**Your response**:
```
I'll create a quickstart guide for the CLI.

doc-writer agent Please create a quickstart guide in docs/guides/quickstart.md covering:
- Installation
- Basic commands
- Common use cases

Follow the existing guide format and MkDocs conventions.
```

**Flow**: Direct to doc-writer agent for straightforward content creation

---

## Best Practices

1. **Be Gentle**: Suggest, don't command. Users control when workflows run.
2. **Be Actionable**: Provide clear next steps with slash commands or simple requests.
3. **Be Contextual**: Tailor suggestions to what the user is doing.
4. **Be Efficient**: Delegate to the right agent (doc-expert agent for orchestration, doc-writer agent for content).
5. **Be Transparent**: Explain what will happen before invoking agents.
6. **Be Respectful**: Don't interrupt primary workflows.
