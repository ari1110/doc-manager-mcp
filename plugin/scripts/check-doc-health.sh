#!/bin/bash
# check-doc-health.sh
# Silent documentation health check for session start
# Only outputs if significant drift detected (10+ files changed)

# Get the current working directory from environment or use pwd
PROJECT_DIR="${PWD:-$(pwd)}"
DOC_MANAGER_DIR="$PROJECT_DIR/.doc-manager"
BASELINE_FILE="$DOC_MANAGER_DIR/memory/repo-baseline.json"

# Check if doc-manager is initialized
if [ ! -d "$DOC_MANAGER_DIR" ]; then
    # Not initialized - silent exit
    exit 0
fi

# Check if baseline exists
if [ ! -f "$BASELINE_FILE" ]; then
    # No baseline - silent exit
    exit 0
fi

# Get baseline timestamp
BASELINE_MTIME=$(stat -c %Y "$BASELINE_FILE" 2>/dev/null || stat -f %m "$BASELINE_FILE" 2>/dev/null)
if [ -z "$BASELINE_MTIME" ]; then
    exit 0
fi

# Calculate days since last sync
CURRENT_TIME=$(date +%s)
DAYS_SINCE_SYNC=$(( (CURRENT_TIME - BASELINE_MTIME) / 86400 ))

# Count changed files since baseline (simplified check)
# This is a rough estimate - actual change detection uses the MCP tool
CHANGED_COUNT=0

# Try to detect changes using git if available
if command -v git &> /dev/null && [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR" || exit 0

    # Get baseline date in git-friendly format
    BASELINE_DATE=$(date -d "@$BASELINE_MTIME" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -r "$BASELINE_MTIME" "+%Y-%m-%d %H:%M:%S" 2>/dev/null)

    # Count unique files changed since baseline:
    # 1. Files in commits since baseline date (git log --since)
    # 2. Uncommitted changes (staged + unstaged)
    if [ -n "$BASELINE_DATE" ]; then
        CHANGED_COUNT=$(
            {
                # Files changed in commits since baseline
                git log --since="$BASELINE_DATE" --name-only --pretty=format: 2>/dev/null
                # Uncommitted staged changes
                git diff --cached --name-only 2>/dev/null
                # Uncommitted unstaged changes
                git diff --name-only 2>/dev/null
            } | grep -v '^$' | sort -u | wc -l
        )
    fi
fi

# Silent check - only output if significant drift (10+ files OR 7+ days)
if [ "$CHANGED_COUNT" -ge 10 ] || [ "$DAYS_SINCE_SYNC" -ge 7 ]; then
    # Output JSON in Claude Code's SessionStart hook format
    # This injects additionalContext into Claude's session
    cat << EOF
{
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "📋 Documentation drift detected: $CHANGED_COUNT files changed since last sync ($DAYS_SINCE_SYNC days ago). Run /doc-status to check sync status."
    }
}
EOF
fi

# Exit successfully (silent if no significant drift)
exit 0
