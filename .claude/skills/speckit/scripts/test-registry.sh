#!/usr/bin/env bash
set -e

# ==============================================================================
# Test Registry Management Script (Full Implementation)
# ==============================================================================
# Tracks individual tests with full metadata from JSDoc tags.
#
# Features:
# - Individual test tracking (not just counts)
# - JSDoc tag parsing (@spec, @userStory, @functionalReq, etc.)
# - Real health metrics (orphaned, retirement candidates)
# - Spec ownership tracking
# - Retirement detection
#
# Usage: test-registry.sh <command> [options]
# Commands: init, scan, report, spec, retire, validate, export-for-plan
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Configuration
REGISTRY_FILE="test-registry.json"
PARSER_SCRIPT="$SCRIPT_DIR/parse-test-file-universal.ts"
TAGGER_SCRIPT="$SCRIPT_DIR/add-test-tags-universal.ts"
JSON_MODE=false
COMMAND=""
SPEC_NUMBER=""
FILTER_TAG=""

# ==============================================================================
# Help Message
# ==============================================================================
show_help() {
    cat << 'EOF'
Test Registry Management (Multi-Language)

USAGE:
    test-registry.sh <command> [options]

COMMANDS:
    init                    Initialize new test registry file
    bootstrap [--spec NUM]  Auto-tag existing tests (brownfield projects)
    scan                    Scan codebase and update test registry
    report                  Show pyramid metrics, health, and issues
    spec <number>           Show tests for specific spec (e.g., spec 001)
    retire [--filter TAG]   List retirement candidate tests
    validate                Validate all tests have required metadata tags
    export-for-plan         Export test data for speckit workflow
    self-check              Run self-diagnostic tests

OPTIONS:
    --json                  Output in JSON format
    --filter <tag>          Filter tests by metadata tag (retire command only)
    --help, -h              Show this help message

EXAMPLES:
    # Initialize registry
    test-registry.sh init

    # Auto-tag existing tests (brownfield setup)
    test-registry.sh bootstrap --spec 001

    # Scan codebase and update registry
    test-registry.sh scan

    # Show full report
    test-registry.sh report

    # Show tests for spec 001
    test-registry.sh spec 001

    # List retirement candidates (default: @retirementCandidate)
    test-registry.sh retire

    # List tests with @mockDependent tag
    test-registry.sh retire --filter mockDependent

    # List tests with @slow tag
    test-registry.sh retire --filter slow

    # Validate metadata tags
    test-registry.sh validate

    # Export for plan.md generation
    test-registry.sh export-for-plan --json

SUPPORTED LANGUAGES:
    - Python (.py): test_*.py, *_test.py
    - JavaScript/TypeScript (.js, .ts, .jsx, .tsx): *.test.*, *.spec.*
    - Go (.go): *_test.go
    - Rust (.rs): *_test.rs

REGISTRY FILE:
    Location: <repo-root>/test-registry.json
    Contains: Individual test metadata with tags

REQUIRES:
    - bun (for universal parser)
    - jq (for JSON processing)

STATUS:
    ✅ FULLY IMPLEMENTED - Multi-Language
    Last Updated: 2025-11-14

EOF
}

# ==============================================================================
# Parse Arguments
# ==============================================================================
parse_args() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                exit 0
                ;;
            --json)
                JSON_MODE=true
                shift
                ;;
            init|scan|report|validate|export-for-plan|self-check)
                COMMAND="$1"
                shift
                ;;
            bootstrap)
                COMMAND="bootstrap"
                shift
                # Capture optional --spec argument
                if [[ $# -gt 0 && "$1" == "--spec" ]]; then
                    shift
                    if [[ $# -gt 0 ]]; then
                        SPEC_NUMBER="$1"
                        shift
                    else
                        echo "Error: --spec requires a spec number" >&2
                        exit 1
                    fi
                fi
                ;;
            spec)
                COMMAND="spec"
                shift
                if [[ $# -gt 0 ]]; then
                    SPEC_NUMBER="$1"
                    shift
                else
                    echo "Error: spec command requires spec number" >&2
                    exit 1
                fi
                ;;
            retire)
                COMMAND="retire"
                shift
                # Capture optional --filter argument
                if [[ $# -gt 0 && "$1" == "--filter" ]]; then
                    shift
                    if [[ $# -gt 0 ]]; then
                        FILTER_TAG="$1"
                        shift
                    else
                        echo "Error: --filter requires a tag name" >&2
                        exit 1
                    fi
                fi
                ;;
            *)
                echo "Error: Unknown argument '$1'" >&2
                show_help
                exit 1
                ;;
        esac
    done

    if [[ -z "$COMMAND" ]]; then
        echo "Error: No command specified" >&2
        show_help
        exit 1
    fi
}

# ==============================================================================
# Utility Functions
# ==============================================================================

get_registry_path() {
    local repo_root
    repo_root="$(get_repo_root)"
    echo "$repo_root/$REGISTRY_FILE"
}

registry_exists() {
    local registry_path
    registry_path="$(get_registry_path)"
    [[ -f "$registry_path" ]]
}

check_dependencies() {
    if ! command -v bun &> /dev/null; then
        echo "Error: bun not found. Install from https://bun.sh" >&2
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo "Error: jq not found. Install jq for JSON processing" >&2
        exit 1
    fi

    if [[ ! -f "$PARSER_SCRIPT" ]]; then
        echo "Error: Parser script not found: $PARSER_SCRIPT" >&2
        exit 1
    fi
}

# ==============================================================================
# Commands
# ==============================================================================

cmd_init() {
    local registry_path
    registry_path="$(get_registry_path)"

    if registry_exists; then
        if [[ "$JSON_MODE" == "true" ]]; then
            echo '{"error":"Registry already exists","path":"'"$registry_path"'"}'
        else
            echo "Error: Registry already exists at $registry_path" >&2
        fi
        exit 1
    fi

    local timestamp
    timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    cat > "$registry_path" << EOF
{
  "version": "1.0.0",
  "lastUpdated": "$timestamp",
  "totalTests": 0,
  "pyramid": {
    "unit": 0,
    "integration": 0,
    "e2e": 0,
    "ratios": {
      "unit": 0.0,
      "integration": 0.0,
      "e2e": 0.0
    },
    "target": {
      "unit": 0.70,
      "integration": 0.20,
      "e2e": 0.10
    },
    "status": "PASS"
  },
  "health": {
    "orphanedTests": 0,
    "slowTests": 0,
    "retirementCandidates": 0,
    "untrackedTests": 0
  },
  "tests": []
}
EOF

    if [[ "$JSON_MODE" == "true" ]]; then
        echo '{"success":true,"path":"'"$registry_path"'","timestamp":"'"$timestamp"'"}'
    else
        echo "✓ Initialized test registry at $registry_path"
    fi
}

cmd_bootstrap() {
    check_dependencies

    local registry_path repo_root
    registry_path="$(get_registry_path)"
    repo_root="$(get_repo_root)"

    # Check if tagger script exists
    if [[ ! -f "$TAGGER_SCRIPT" ]]; then
        echo "Error: Auto-tagger script not found: $TAGGER_SCRIPT" >&2
        exit 1
    fi

    # Initialize registry if it doesn't exist
    if ! registry_exists; then
        echo "Registry not found. Initializing..."
        cmd_init > /dev/null
    fi

    # Run initial scan to detect untagged tests
    echo "Scanning for existing tests..."
    cmd_scan > /dev/null

    # Check for untagged tests
    local untagged_count
    untagged_count=$(jq -r '.health.orphanedTests' "$registry_path")

    if [[ "$untagged_count" -eq 0 ]]; then
        echo "✓ All tests are already tagged. No bootstrap needed."
        exit 0
    fi

    echo "Found $untagged_count untagged tests"

    # Determine spec number
    local spec_arg=""
    if [[ -n "$SPEC_NUMBER" ]]; then
        spec_arg="--spec $SPEC_NUMBER"
        echo "Tagging tests with @spec $SPEC_NUMBER..."
    else
        echo "Inferring spec numbers from file paths..."
    fi

    # Run auto-tagger (dry-run first)
    echo ""
    echo "Preview of changes (dry-run):"
    echo "========================================"
    bun "$TAGGER_SCRIPT" 2>&1 || true
    echo "========================================"
    echo ""

    # Confirm with user
    read -p "Apply these changes? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Bootstrap cancelled."
        exit 0
    fi

    # Run auto-tagger with --write
    echo "Applying tags..."
    bun "$TAGGER_SCRIPT" --write

    # Re-scan to update registry
    echo ""
    echo "Rescanning with updated tags..."
    cmd_scan > /dev/null

    # Show final results
    local tagged_count
    tagged_count=$(jq -r '.health.orphanedTests' "$registry_path")
    local success_count=$((untagged_count - tagged_count))

    echo ""
    echo "✓ Bootstrap complete!"
    echo "  Tagged: $success_count tests"
    if [[ "$tagged_count" -gt 0 ]]; then
        echo "  Remaining untagged: $tagged_count tests"
        echo ""
        echo "Note: Some tests could not be auto-tagged. Manual tagging may be required."
    fi

    # Show updated report
    echo ""
    cmd_report
}

cmd_scan() {
    check_dependencies

    local registry_path repo_root
    registry_path="$(get_registry_path)"
    repo_root="$(get_repo_root)"

    if ! registry_exists; then
        if [[ "$JSON_MODE" == "true" ]]; then
            echo '{"error":"Registry not found. Run: test-registry.sh init"}'
        else
            echo "Error: Registry not found. Run: test-registry.sh init" >&2
        fi
        exit 1
    fi

    # Find all test files across multiple languages (exclude node_modules, dist, build, etc.)
    local test_files=()
    while IFS= read -r -d '' file; do
        test_files+=("$file")
    done < <(find "$repo_root" -type f \( \
        -name "*.test.ts" -o -name "*.test.tsx" -o \
        -name "*.spec.ts" -o -name "*.spec.tsx" -o \
        -name "*.test.js" -o -name "*.test.jsx" -o \
        -name "*.spec.js" -o -name "*.spec.jsx" -o \
        -name "test_*.py" -o -name "*_test.py" -o \
        -name "*_test.go" -o \
        -name "*_test.rs" \
        \) \
        -not -path "*/node_modules/*" \
        -not -path "*/dist/*" \
        -not -path "*/build/*" \
        -not -path "*/target/*" \
        -not -path "*/.venv/*" \
        -not -path "*/__pycache__/*" \
        -not -path "*/.next/*" \
        -print0 2>/dev/null)

    # Parse each test file and collect metadata
    local all_tests_json="[]"

    for file in "${test_files[@]}"; do
        # Call TypeScript parser
        local file_tests
        file_tests=$(bun "$PARSER_SCRIPT" "$file" --json 2>/dev/null || echo "[]")

        # Merge into all_tests_json
        all_tests_json=$(echo "$all_tests_json $file_tests" | jq -s 'add')
    done

    # Calculate counts from individual tests
    local total_tests
    total_tests=$(echo "$all_tests_json" | jq 'length')

    local unit_count
    unit_count=$(echo "$all_tests_json" | jq '[.[] | select(.type == "unit")] | length')

    local integration_count
    integration_count=$(echo "$all_tests_json" | jq '[.[] | select(.type == "integration")] | length')

    local e2e_count
    e2e_count=$(echo "$all_tests_json" | jq '[.[] | select(.type == "e2e")] | length')

    # Calculate ratios using awk (more portable than bc)
    local unit_ratio integration_ratio e2e_ratio
    if [[ $total_tests -gt 0 ]]; then
        unit_ratio=$(awk "BEGIN {printf \"%.2f\", $unit_count / $total_tests}")
        integration_ratio=$(awk "BEGIN {printf \"%.2f\", $integration_count / $total_tests}")
        e2e_ratio=$(awk "BEGIN {printf \"%.2f\", $e2e_count / $total_tests}")
    else
        unit_ratio="0.00"
        integration_ratio="0.00"
        e2e_ratio="0.00"
    fi

    # Check pyramid health using awk for float comparison
    local pyramid_status="PASS"
    if (( $(awk "BEGIN {print ($unit_ratio < 0.60)}") )); then
        pyramid_status="WARN"
    fi
    if (( $(awk "BEGIN {print ($integration_ratio > 0.30)}") )); then
        pyramid_status="WARN"
    fi
    if (( $(awk "BEGIN {print ($e2e_ratio > 0.15)}") )); then
        pyramid_status="WARN"
    fi

    # Calculate health metrics
    local orphaned_count
    orphaned_count=$(echo "$all_tests_json" | jq '[.[] | select(.specNumber == null)] | length')

    local retirement_count
    retirement_count=$(echo "$all_tests_json" | jq '[.[] | select(.retirementCandidate == true)] | length')

    local slow_count
    slow_count=$(echo "$all_tests_json" | jq '[.[] | select(.slow == true)] | length')

    local timestamp
    timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    # Build registry JSON - write directly to file to avoid arg list limits
    # First write the tests array to avoid passing huge JSON as argument
    echo "$all_tests_json" > "${registry_path}.tests.tmp"

    # Build metadata structure and merge with tests array
    jq -n \
        --argjson total "$total_tests" \
        --argjson unit "$unit_count" \
        --argjson integration "$integration_count" \
        --argjson e2e "$e2e_count" \
        --arg unit_ratio "$unit_ratio" \
        --arg integration_ratio "$integration_ratio" \
        --arg e2e_ratio "$e2e_ratio" \
        --arg status "$pyramid_status" \
        --argjson orphaned "$orphaned_count" \
        --argjson retirement "$retirement_count" \
        --argjson slow "$slow_count" \
        --arg timestamp "$timestamp" \
        --slurpfile tests "${registry_path}.tests.tmp" \
        '{
            version: "1.0.0",
            lastUpdated: $timestamp,
            totalTests: $total,
            pyramid: {
                unit: $unit,
                integration: $integration,
                e2e: $e2e,
                ratios: {
                    unit: ($unit_ratio | tonumber),
                    integration: ($integration_ratio | tonumber),
                    e2e: ($e2e_ratio | tonumber)
                },
                target: {
                    unit: 0.70,
                    integration: 0.20,
                    e2e: 0.10
                },
                status: $status
            },
            health: {
                orphanedTests: $orphaned,
                slowTests: $slow,
                retirementCandidates: $retirement,
                untrackedTests: 0
            },
            tests: $tests[0]
        }' > "$registry_path"

    # Clean up temp file
    rm -f "${registry_path}.tests.tmp"

    if [[ "$JSON_MODE" == "true" ]]; then
        cat "$registry_path"
    else
        echo "✓ Scanned ${#test_files[@]} test files"
        echo "✓ Total tests: $total_tests"
        echo "✓ Pyramid: Unit=$unit_count ($unit_ratio), Integration=$integration_count ($integration_ratio), E2E=$e2e_count ($e2e_ratio)"
        echo "✓ Status: $pyramid_status"
        echo "✓ Health: Orphaned=$orphaned_count, Retirement=$retirement_count, Slow=$slow_count"
        echo "✓ Updated registry at $registry_path"

        # Warn about untagged tests (brownfield projects)
        if [[ "$orphaned_count" -gt 0 ]]; then
            echo ""
            echo "⚠ Found $orphaned_count untagged tests (no @spec tag)"
            echo "  To auto-tag them, run:"
            echo "    test-registry.sh bootstrap --spec <number>"
        fi
    fi
}

cmd_report() {
    local registry_path
    registry_path="$(get_registry_path)"

    if ! registry_exists; then
        if [[ "$JSON_MODE" == "true" ]]; then
            echo '{"error":"Registry not found. Run: test-registry.sh init"}'
        else
            echo "Error: Registry not found. Run: test-registry.sh init" >&2
        fi
        exit 1
    fi

    if [[ "$JSON_MODE" == "true" ]]; then
        cat "$registry_path"
    else
        # Parse and display human-readable report
        local registry
        registry=$(cat "$registry_path")

        local total unit integration e2e status orphaned retirement slow

        total=$(echo "$registry" | jq -r '.totalTests')
        unit=$(echo "$registry" | jq -r '.pyramid.unit')
        integration=$(echo "$registry" | jq -r '.pyramid.integration')
        e2e=$(echo "$registry" | jq -r '.pyramid.e2e')
        status=$(echo "$registry" | jq -r '.pyramid.status')
        orphaned=$(echo "$registry" | jq -r '.health.orphanedTests')
        retirement=$(echo "$registry" | jq -r '.health.retirementCandidates')
        slow=$(echo "$registry" | jq -r '.health.slowTests')

        local unit_pct integration_pct e2e_pct
        if [[ $total -gt 0 ]]; then
            unit_pct=$(awk "BEGIN {printf \"%.1f%%\", ($unit / $total) * 100}")
            integration_pct=$(awk "BEGIN {printf \"%.1f%%\", ($integration / $total) * 100}")
            e2e_pct=$(awk "BEGIN {printf \"%.1f%%\", ($e2e / $total) * 100}")
        else
            unit_pct="0.0%"
            integration_pct="0.0%"
            e2e_pct="0.0%"
        fi

        cat << EOF

Test Registry Report
====================

Total Tests: $total

Test Pyramid:
  Unit:        $unit ($unit_pct) [Target: 70%]
  Integration: $integration ($integration_pct) [Target: 20%]
  E2E:         $e2e ($e2e_pct) [Target: 10%]

Pyramid Status: $status

Health Metrics:
  Orphaned Tests:          $orphaned (no spec ownership)
  Retirement Candidates:   $retirement (flagged for removal)
  Slow Tests:              $slow (long execution time)

EOF

        if [[ "$status" == "WARN" ]]; then
            echo "⚠ Pyramid ratios outside target ranges"
        elif [[ "$status" == "PASS" ]]; then
            echo "✓ Pyramid ratios within target ranges"
        fi

        if [[ $orphaned -gt 0 ]]; then
            echo "⚠ $orphaned tests have no spec ownership"
        fi

        if [[ $retirement -gt 0 ]]; then
            echo "ℹ $retirement tests marked for retirement"
        fi
    fi
}

cmd_spec() {
    if [[ -z "$SPEC_NUMBER" ]]; then
        echo "Error: Spec number required" >&2
        exit 1
    fi

    local registry_path
    registry_path="$(get_registry_path)"

    if ! registry_exists; then
        if [[ "$JSON_MODE" == "true" ]]; then
            echo '{"error":"Registry not found"}'
        else
            echo "Error: Registry not found. Run: test-registry.sh scan" >&2
        fi
        exit 1
    fi

    # Format spec number with leading zeros
    local formatted_spec
    formatted_spec=$(printf "%03d" "$SPEC_NUMBER")

    # Filter tests by spec number
    local spec_tests
    spec_tests=$(jq --arg spec "$formatted_spec" '[.tests[] | select(.specNumber == $spec)]' "$registry_path")

    local count
    count=$(echo "$spec_tests" | jq 'length')

    if [[ "$JSON_MODE" == "true" ]]; then
        echo "$spec_tests"
    else
        if [[ $count -eq 0 ]]; then
            echo "No tests found for spec $formatted_spec"
            exit 0
        fi

        echo "Spec $formatted_spec Tests:"
        echo ""
        echo "$spec_tests" | jq -r '.[] | "  [\(.type)] \(.file):\(.lineNumber)\n    \(.describePath | join(" > ")) > \(.testName)"'
        echo ""
        echo "Total: $count tests"
    fi
}

cmd_retire() {
    local registry_path
    registry_path="$(get_registry_path)"

    if ! registry_exists; then
        if [[ "$JSON_MODE" == "true" ]]; then
            echo '{"error":"Registry not found"}'
        else
            echo "Error: Registry not found. Run: test-registry.sh scan" >&2
        fi
        exit 1
    fi

    # Build jq filter based on FILTER_TAG global variable
    local jq_filter
    if [[ -n "$FILTER_TAG" ]]; then
        # Filter by specific metadata tag
        jq_filter="[.tests[] | select(.$FILTER_TAG == true)]"
    else
        # Default: show @retirementCandidate tests
        jq_filter='[.tests[] | select(.retirementCandidate == true)]'
    fi

    # Get retirement candidates
    local candidates
    candidates=$(jq "$jq_filter" "$registry_path")

    local count
    count=$(echo "$candidates" | jq 'length')

    if [[ "$JSON_MODE" == "true" ]]; then
        echo "$candidates"
    else
        if [[ $count -eq 0 ]]; then
            if [[ -n "$FILTER_TAG" ]]; then
                echo "No tests found with @$FILTER_TAG tag"
            else
                echo "No retirement candidates found"
            fi
            exit 0
        fi

        if [[ -n "$FILTER_TAG" ]]; then
            echo "Tests with @$FILTER_TAG tag:"
        else
            echo "Retirement Candidates:"
        fi
        echo ""
        echo "$candidates" | jq -r '.[] | "  - \(.file):\(.lineNumber) - \(.testName)"'
        echo ""
        echo "Total: $count"
    fi
}

cmd_validate() {
    check_dependencies

    local repo_root
    repo_root="$(get_repo_root)"

    # Find all test files across multiple languages (exclude node_modules, dist, build, etc.)
    local test_files=()
    while IFS= read -r -d '' file; do
        test_files+=("$file")
    done < <(find "$repo_root" -type f \( \
        -name "*.test.ts" -o -name "*.test.tsx" -o \
        -name "*.spec.ts" -o -name "*.spec.tsx" -o \
        -name "*.test.js" -o -name "*.test.jsx" -o \
        -name "*.spec.js" -o -name "*.spec.jsx" -o \
        -name "test_*.py" -o -name "*_test.py" -o \
        -name "*_test.go" -o \
        -name "*_test.rs" \
        \) \
        -not -path "*/node_modules/*" \
        -not -path "*/dist/*" \
        -not -path "*/build/*" \
        -not -path "*/target/*" \
        -not -path "*/.venv/*" \
        -not -path "*/__pycache__/*" \
        -not -path "*/.next/*" \
        -print0 2>/dev/null)

    local missing_tags=()
    local total_tests=0

    for file in "${test_files[@]}"; do
        # Parse file and check for @spec tags
        local file_tests
        file_tests=$(bun "$PARSER_SCRIPT" "$file" --json 2>/dev/null || echo "[]")

        local tests_without_spec
        tests_without_spec=$(echo "$file_tests" | jq '[.[] | select(.specNumber == null)]')

        local count
        count=$(echo "$tests_without_spec" | jq 'length')

        if [[ $count -gt 0 ]]; then
            missing_tags+=("$file")
        fi

        total_tests=$((total_tests + $(echo "$file_tests" | jq 'length')))
    done

    if [[ "$JSON_MODE" == "true" ]]; then
        jq -n \
            --argjson total "$total_tests" \
            --argjson missing "${#missing_tags[@]}" \
            --argjson files "$(printf '%s\n' "${missing_tags[@]}" | jq -R . | jq -s .)" \
            '{totalTests: $total, filesMissingTags: $missing, files: $files}'
    else
        if [[ ${#missing_tags[@]} -eq 0 ]]; then
            echo "✓ All $total_tests tests have valid JSDoc tags"
            exit 0
        else
            echo "✗ ${#missing_tags[@]} files have tests missing @spec tags:"
            for file in "${missing_tags[@]}"; do
                echo "  - $file"
            done
            exit 1
        fi
    fi
}

cmd_export_for_plan() {
    local registry_path
    registry_path="$(get_registry_path)"

    if ! registry_exists; then
        if [[ "$JSON_MODE" == "true" ]]; then
            echo '{"error":"Registry not found. Run: test-registry.sh scan"}'
        else
            echo "Error: Registry not found. Run: test-registry.sh scan" >&2
        fi
        exit 1
    fi

    local registry
    registry=$(cat "$registry_path")

    local total unit integration e2e status

    total=$(echo "$registry" | jq -r '.totalTests')
    unit=$(echo "$registry" | jq -r '.pyramid.unit')
    integration=$(echo "$registry" | jq -r '.pyramid.integration')
    e2e=$(echo "$registry" | jq -r '.pyramid.e2e')
    status=$(echo "$registry" | jq -r '.pyramid.status')

    if [[ "$JSON_MODE" == "true" ]]; then
        jq -n \
            --argjson total "$total" \
            --argjson unit "$unit" \
            --argjson integration "$integration" \
            --argjson e2e "$e2e" \
            --arg status "$status" \
            '{
                existingTests: {
                    total: $total,
                    unit: $unit,
                    integration: $integration,
                    e2e: $e2e,
                    pyramidStatus: $status
                },
                recommendations: {
                    focusOn: "integration",
                    avoidDuplication: true,
                    retireBeforeAdding: true
                }
            }'
    else
        cat << EOF

Existing Test Coverage
======================

Total: $total tests
  - Unit: $unit
  - Integration: $integration
  - E2E: $e2e

Pyramid Status: $status

Recommendations for plan.md:
  - Focus new tests on contract/integration layer
  - Retire mock-dependent tests before adding Tauri tests
  - Maintain pyramid ratios (70/20/10)

EOF
    fi
}

cmd_self_check() {
    echo "Running self-check..."
    echo ""

    local errors=0
    local warnings=0
    local repo_root
    repo_root="$(get_repo_root)"

    # ==============================================================================
    # 1. Dependency checks
    # ==============================================================================
    echo "Checking dependencies..."

    if ! command -v bun &> /dev/null; then
        echo "  ✗ bun not found"
        ((errors++))
    else
        echo "  ✓ bun found"
    fi

    if ! command -v jq &> /dev/null; then
        echo "  ✗ jq not found"
        ((errors++))
    else
        echo "  ✓ jq found"
    fi

    if [[ ! -f "$PARSER_SCRIPT" ]]; then
        echo "  ✗ Parser script not found: $PARSER_SCRIPT"
        ((errors++))
    else
        echo "  ✓ Parser script found"
    fi

    echo ""

    # ==============================================================================
    # 2. Feature verification - Parser extracts JSDoc tags
    # ==============================================================================
    echo "Verifying parser extracts JSDoc tags..."

    # Find a test file to verify (exclude node_modules, dist, build)
    local test_file
    test_file=$(find "$repo_root" -type f \( -name "*.test.tsx" -o -name "*.test.ts" \) \
        -not -path "*/node_modules/*" \
        -not -path "*/dist/*" \
        -not -path "*/build/*" \
        -not -path "*/.next/*" | head -1)

    if [[ -z "$test_file" ]]; then
        echo "  ⚠ No test files found to verify parser"
        ((warnings++))
    else
        local parser_output
        parser_output=$(bun "$PARSER_SCRIPT" "$test_file" --json 2>&1)
        local parser_exit=$?

        if [[ $parser_exit -ne 0 ]]; then
            echo "  ✗ Parser failed to run on test file"
            ((errors++))
        else
            # Check if output is valid JSON
            if echo "$parser_output" | jq empty 2>/dev/null; then
                local has_tests
                has_tests=$(echo "$parser_output" | jq 'length > 0')

                if [[ "$has_tests" == "true" ]]; then
                    local has_spec
                    has_spec=$(echo "$parser_output" | jq '.[0].specNumber != null')

                    if [[ "$has_spec" == "true" ]]; then
                        echo "  ✓ Parser extracts JSDoc tags correctly"
                    else
                        echo "  ✗ Parser does not extract @spec tags"
                        ((errors++))
                    fi
                else
                    echo "  ⚠ Parser returned no tests from test file"
                    ((warnings++))
                fi
            else
                echo "  ✗ Parser output is not valid JSON"
                ((errors++))
            fi
        fi
    fi

    echo ""

    # ==============================================================================
    # 3. Feature verification - Registry exists and has test data
    # ==============================================================================
    echo "Verifying registry tracks individual tests..."

    local registry_path
    registry_path="$(get_registry_path)"

    if ! registry_exists; then
        echo "  ⚠ Registry not initialized (run: test-registry.sh init)"
        ((warnings++))
    else
        local registry_content
        registry_content=$(cat "$registry_path")

        # Check if registry has valid structure
        if echo "$registry_content" | jq empty 2>/dev/null; then
            local total_tests
            total_tests=$(echo "$registry_content" | jq '.totalTests')

            local tests_array_length
            tests_array_length=$(echo "$registry_content" | jq '.tests | length')

            if [[ "$total_tests" == "$tests_array_length" ]]; then
                echo "  ✓ Registry tracks $total_tests individual tests"
            else
                echo "  ✗ Registry totalTests ($total_tests) doesn't match tests array length ($tests_array_length)"
                ((errors++))
            fi

            # Check if test objects have required fields
            local first_test_has_fields
            first_test_has_fields=$(echo "$registry_content" | jq '.tests[0] | has("id") and has("file") and has("specNumber") and has("type")')

            if [[ "$first_test_has_fields" == "true" ]]; then
                echo "  ✓ Registry tests have required metadata fields"
            else
                echo "  ✗ Registry tests missing required metadata"
                ((errors++))
            fi
        else
            echo "  ✗ Registry JSON is invalid"
            ((errors++))
        fi
    fi

    echo ""

    # ==============================================================================
    # 4. Feature verification - Report command shows metrics
    # ==============================================================================
    echo "Verifying report command shows metrics..."

    if ! registry_exists; then
        echo "  ⚠ Skipped (registry not initialized)"
        ((warnings++))
    else
        local report_output
        report_output=$(cmd_report 2>&1)
        local report_exit=$?

        if [[ $report_exit -ne 0 ]]; then
            echo "  ✗ Report command failed"
            ((errors++))
        else
            # Check if report contains expected sections
            if echo "$report_output" | grep -q "Pyramid Status"; then
                echo "  ✓ Report shows test pyramid metrics"
            else
                echo "  ✗ Report missing test pyramid metrics"
                ((errors++))
            fi

            if echo "$report_output" | grep -q "Health Metrics"; then
                echo "  ✓ Report shows health metrics"
            else
                echo "  ✗ Report missing health metrics"
                ((errors++))
            fi
        fi
    fi

    echo ""

    # ==============================================================================
    # 5. Feature verification - Detects retirement candidates
    # ==============================================================================
    echo "Verifying retirement candidate detection..."

    if ! registry_exists; then
        echo "  ⚠ Skipped (registry not initialized)"
        ((warnings++))
    else
        # Test default behavior (no filter)
        local retirement_json
        JSON_MODE=true retirement_json=$(cmd_retire 2>&1)
        local retire_exit=$?

        if [[ $retire_exit -ne 0 ]]; then
            echo "  ✗ Retire command failed (default)"
            ((errors++))
        else
            if echo "$retirement_json" | jq empty 2>/dev/null; then
                echo "  ✓ Retirement candidate detection works (default)"
            else
                echo "  ✗ Retire command output is not valid JSON (default)"
                ((errors++))
            fi
        fi

        # Test --filter flag with mockDependent
        FILTER_TAG="mockDependent"
        local mock_json
        JSON_MODE=true mock_json=$(cmd_retire 2>&1)
        local mock_exit=$?
        FILTER_TAG=""  # Reset

        if [[ $mock_exit -ne 0 ]]; then
            echo "  ✗ Retire command failed (--filter mockDependent)"
            ((errors++))
        else
            if echo "$mock_json" | jq empty 2>/dev/null; then
                echo "  ✓ Retire --filter mockDependent works"
            else
                echo "  ✗ Retire --filter output is not valid JSON"
                ((errors++))
            fi
        fi

        # Test --filter flag with slow
        FILTER_TAG="slow"
        local slow_json
        JSON_MODE=true slow_json=$(cmd_retire 2>&1)
        local slow_exit=$?
        FILTER_TAG=""  # Reset

        if [[ $slow_exit -ne 0 ]]; then
            echo "  ✗ Retire command failed (--filter slow)"
            ((errors++))
        else
            if echo "$slow_json" | jq empty 2>/dev/null; then
                echo "  ✓ Retire --filter slow works"
            else
                echo "  ✗ Retire --filter output is not valid JSON"
                ((errors++))
            fi
        fi
    fi

    echo ""

    # ==============================================================================
    # Summary
    # ==============================================================================
    echo "Self-check summary:"
    echo "  Errors: $errors"
    echo "  Warnings: $warnings"
    echo ""

    if [[ $errors -eq 0 ]]; then
        if [[ $warnings -gt 0 ]]; then
            echo "⚠ Self-check passed with warnings"
            exit 0
        else
            echo "✓ Self-check passed - all documented features verified"
            exit 0
        fi
    else
        echo "✗ Self-check failed with $errors errors"
        echo ""
        echo "This means documented features do NOT match actual implementation."
        echo "DO NOT commit code claiming these features work until self-check passes."
        exit 1
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    parse_args "$@"

    case "$COMMAND" in
        init)
            cmd_init
            ;;
        bootstrap)
            cmd_bootstrap
            ;;
        scan)
            cmd_scan
            ;;
        report)
            cmd_report
            ;;
        spec)
            cmd_spec
            ;;
        retire)
            cmd_retire
            ;;
        validate)
            cmd_validate
            ;;
        export-for-plan)
            cmd_export_for_plan
            ;;
        self-check)
            cmd_self_check
            ;;
        *)
            echo "Error: Unknown command '$COMMAND'" >&2
            exit 1
            ;;
    esac
}

main "$@"
