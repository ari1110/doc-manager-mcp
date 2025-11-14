#!/usr/bin/env bash
set -e

# ==============================================================================
# Universal Test Parser (Bash/Regex)
# ==============================================================================
# Parses test files across multiple languages to extract metadata from comments:
# - Test structure (classes, functions, methods)
# - Annotation tags (@spec, @userStory, @functionalReq, etc.)
# - File metadata (path, modification date)
# - Mock dependency detection
#
# Outputs JSON array of test metadata objects.
#
# Supported languages: Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, PHP
#
# Usage:
#   parse-test-file.sh <file-path> [--json]
#
# Output:
#   JSON array of TestMetadata objects
# ==============================================================================

# Parse arguments
FILE_PATH=""
JSON_MODE=true  # Always output JSON

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            cat << 'EOF'
Universal Test Parser

Parses test files to extract metadata from comments/docstrings.

Usage:
    parse-test-file.sh <file-path> [--json]

Arguments:
    <file-path>    Path to test file to parse

Options:
    --json         Output JSON format (default)
    --help, -h     Show this help message

Supported Languages:
    Python (.py), JavaScript (.js), TypeScript (.ts, .tsx),
    Go (.go), Rust (.rs), Java (.java), Ruby (.rb), PHP (.php)

Output Format:
    JSON array of test metadata objects with fields:
    - id, file, type, describePath, testName, lineNumber
    - specNumber, userStories, functionalReqs, testType
    - mockDependent, retirementCandidate, contractTest, slow
    - createdDate, lastModified, tags
EOF
            exit 0
            ;;
        --json)
            JSON_MODE=true
            shift
            ;;
        *)
            if [[ -z "$FILE_PATH" ]]; then
                FILE_PATH="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$FILE_PATH" ]]; then
    echo "Error: File path required" >&2
    echo "Usage: parse-test-file.sh <file-path> [--json]" >&2
    exit 1
fi

if [[ ! -f "$FILE_PATH" ]]; then
    echo "Error: File not found: $FILE_PATH" >&2
    exit 1
fi

# ==============================================================================
# Language Detection
# ==============================================================================
detect_language() {
    local ext="${FILE_PATH##*.}"
    case "$ext" in
        py) echo "python" ;;
        js) echo "javascript" ;;
        jsx) echo "javascript" ;;
        ts) echo "typescript" ;;
        tsx) echo "typescript" ;;
        go) echo "go" ;;
        rs) echo "rust" ;;
        java) echo "java" ;;
        rb) echo "ruby" ;;
        php) echo "php" ;;
        *) echo "unknown" ;;
    esac
}

LANGUAGE=$(detect_language)

if [[ "$LANGUAGE" == "unknown" ]]; then
    echo "Error: Unsupported file extension: ${FILE_PATH##*.}" >&2
    exit 1
fi

# ==============================================================================
# Utility Functions
# ==============================================================================

# Generate unique test ID
generate_test_id() {
    local describe_path="$1"
    local test_name="$2"
    local content="${FILE_PATH}::${describe_path}::${test_name}"
    echo -n "$content" | sha256sum | cut -c1-16
}

# Infer test type from file path
infer_test_type() {
    local path_lower=$(echo "$FILE_PATH" | tr '[:upper:]' '[:lower:]')
    if [[ "$path_lower" =~ /e2e/ || "$path_lower" =~ \.e2e\. || "$path_lower" =~ end-to-end ]]; then
        echo "e2e"
    elif [[ "$path_lower" =~ /integration/ || "$path_lower" =~ \.integration\. ]]; then
        echo "integration"
    else
        echo "unit"
    fi
}

# Detect mock dependencies
detect_mock_dependency() {
    grep -qiE "(mock|stub|fake|spy|double|@patch|jest\.mock|vi\.mock)" "$FILE_PATH" 2>/dev/null && echo "true" || echo "false"
}

# Extract tag value from comment
extract_tag() {
    local comment="$1"
    local tag="$2"
    echo "$comment" | { grep -oP "@${tag}\s+\K[^\n@]+" || true; } | head -1 | sed 's/^[ \t]*//;s/[ \t]*$//'
}

# Extract all values for a tag (for tags that can appear multiple times)
extract_tag_all() {
    local comment="$1"
    local tag="$2"
    echo "$comment" | { grep -oP "@${tag}\s+\K[^\n@]+" || true; } | sed 's/^[ \t]*//;s/[ \t]*$//'
}

# Check if tag exists (for flag tags)
has_tag() {
    local comment="$1"
    local tag="$2"
    echo "$comment" | grep -q "@${tag}" && echo "true" || echo "false"
}

# Get file timestamps
get_created_date() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        stat -f "%B" "$FILE_PATH" | awk '{print strftime("%Y-%m-%dT%H:%M:%S", $1)}'
    else
        stat -c "%W" "$FILE_PATH" 2>/dev/null | awk '{if ($1 == "0") print ""; else print strftime("%Y-%m-%dT%H:%M:%S", $1)}' || echo ""
    fi
}

get_modified_date() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        stat -f "%m" "$FILE_PATH" | awk '{print strftime("%Y-%m-%dT%H:%M:%S", $1)}'
    else
        stat -c "%Y" "$FILE_PATH" | awk '{print strftime("%Y-%m-%dT%H:%M:%S", $1)}'
    fi
}

# ==============================================================================
# Comment Extraction
# ==============================================================================

# Extract comment block above a line number
extract_comment_at_line() {
    local line_num="$1"
    local comment_lines=()
    local current_line=$((line_num - 1))

    # Read backwards from the line to collect comments
    while [[ $current_line -gt 0 ]]; do
        local line=$(sed -n "${current_line}p" "$FILE_PATH")

        # Check if line is a comment based on language
        local is_comment=false
        case "$LANGUAGE" in
            python)
                # Python: # comments or """docstrings"""
                if [[ "$line" =~ ^[[:space:]]*# ]] || [[ "$line" =~ ^[[:space:]]*\"\"\" ]] || [[ "$line" =~ ^[[:space:]]*\'\'\' ]]; then
                    is_comment=true
                fi
                ;;
            javascript|typescript)
                # JS/TS: // or /* */ or /** */
                if [[ "$line" =~ ^[[:space:]]*(//|\*|/\*) ]]; then
                    is_comment=true
                fi
                ;;
            go|rust|java|php)
                # Go/Rust/Java/PHP: // or /* */
                if [[ "$line" =~ ^[[:space:]]*(//|\*|/\*) ]]; then
                    is_comment=true
                fi
                ;;
            ruby)
                # Ruby: #
                if [[ "$line" =~ ^[[:space:]]*# ]]; then
                    is_comment=true
                fi
                ;;
        esac

        if [[ "$is_comment" == true ]]; then
            comment_lines=("$line" "${comment_lines[@]}")
            ((current_line--))
        elif [[ -z "$line" || "$line" =~ ^[[:space:]]*$ ]]; then
            # Skip blank lines
            ((current_line--))
        else
            # Hit non-comment, stop
            break
        fi
    done

    # Join comment lines and clean up
    local comment=$(printf '%s\n' "${comment_lines[@]}")

    # Strip comment markers
    comment=$(echo "$comment" | sed -E 's/^[[:space:]]*(#|\/\/|\*|\/\*\*?|\*\/)//' | sed 's/"""//g' | sed "s/'''//g")

    echo "$comment"
}

# ==============================================================================
# Test Detection (Language-Specific)
# ==============================================================================

# Find all test functions/methods and their line numbers
find_tests() {
    local tests_json="[]"

    case "$LANGUAGE" in
        python)
            find_python_tests
            ;;
        javascript|typescript)
            find_js_ts_tests
            ;;
        go)
            find_go_tests
            ;;
        rust)
            find_rust_tests
            ;;
        java)
            find_java_tests
            ;;
        ruby)
            find_ruby_tests
            ;;
        php)
            find_php_tests
            ;;
    esac
}

# Python: Find test functions and classes
find_python_tests() {
    local line_num=0
    local current_class=""

    while IFS= read -r line; do
        ((line_num++))

        # Check for test class
        if [[ "$line" =~ ^class[[:space:]]+Test[[:alnum:]]* ]]; then
            current_class=$(echo "$line" | grep -oP 'class\s+\K[A-Za-z0-9_]+')
            continue
        fi

        # Check for test function
        if [[ "$line" =~ ^[[:space:]]*(def|async[[:space:]]+def)[[:space:]]+test_ ]]; then
            local test_name=$(echo "$line" | grep -oP '(def|async def)\s+\K[a-z_][a-z0-9_]*')
            process_test "$line_num" "$test_name" "$current_class"
        fi

        # Reset class context if we hit a non-indented line
        if [[ "$line" =~ ^[^[:space:]] && ! "$line" =~ ^class ]]; then
            current_class=""
        fi
    done < "$FILE_PATH"
}

# JavaScript/TypeScript: Find test/it/describe blocks
find_js_ts_tests() {
    local line_num=0
    local describe_stack=()

    while IFS= read -r line; do
        ((line_num++))

        # Match describe("...", ...)
        if [[ "$line" =~ describe[[:space:]]*\( ]]; then
            local describe_name=$(echo "$line" | grep -oP "describe\s*\(\s*[\"'\`]\K[^\"'\`]+" | head -1)
            if [[ -n "$describe_name" ]]; then
                describe_stack+=("$describe_name")
            fi
        fi

        # Match test("...", ...) or it("...", ...)
        if [[ "$line" =~ (test|it)[[:space:]]*\( ]]; then
            local test_name=$(echo "$line" | grep -oP "(test|it)\s*\(\s*[\"'\`]\K[^\"'\`]+" | head -1)
            if [[ -n "$test_name" ]]; then
                local describe_path=$(IFS='::'; echo "${describe_stack[*]}")
                process_test "$line_num" "$test_name" "$describe_path"
            fi
        fi

        # Track closing braces (simplified - doesn't handle all cases)
        # This is a limitation of regex-based parsing
    done < "$FILE_PATH"
}

# Go: Find Test functions
find_go_tests() {
    local line_num=0

    while IFS= read -r line; do
        ((line_num++))

        if [[ "$line" =~ ^func[[:space:]]+Test[[:alnum:]]* ]]; then
            local test_name=$(echo "$line" | grep -oP 'func\s+\K[A-Za-z0-9_]+')
            process_test "$line_num" "$test_name" ""
        fi
    done < "$FILE_PATH"
}

# Rust: Find #[test] functions
find_rust_tests() {
    local line_num=0
    local has_test_attr=false

    while IFS= read -r line; do
        ((line_num++))

        # Check for #[test] attribute
        if [[ "$line" =~ \#\[test\] ]]; then
            has_test_attr=true
            continue
        fi

        # Check for test function (with or without attribute)
        if [[ "$line" =~ ^[[:space:]]*fn[[:space:]]+test_ ]] || [[ "$has_test_attr" == true && "$line" =~ ^[[:space:]]*fn[[:space:]]+ ]]; then
            local test_name=$(echo "$line" | grep -oP 'fn\s+\K[a-z_][a-z0-9_]*')
            process_test "$line_num" "$test_name" ""
            has_test_attr=false
        fi
    done < "$FILE_PATH"
}

# Java: Find @Test methods
find_java_tests() {
    local line_num=0
    local has_test_annotation=false
    local current_class=""

    while IFS= read -r line; do
        ((line_num++))

        # Check for test class
        if [[ "$line" =~ class[[:space:]]+[A-Z] ]]; then
            current_class=$(echo "$line" | grep -oP 'class\s+\K[A-Za-z0-9_]+')
            continue
        fi

        # Check for @Test annotation
        if [[ "$line" =~ @Test ]]; then
            has_test_annotation=true
            continue
        fi

        # Check for test method
        if [[ "$has_test_annotation" == true && "$line" =~ (public|private|protected)?[[:space:]]*(void|[A-Z]) ]] || [[ "$line" =~ test[A-Z] ]]; then
            local test_name=$(echo "$line" | grep -oP '(void|[A-Z][a-z0-9_]*)\s+\K[a-z][a-zA-Z0-9_]*(?=\s*\()')
            if [[ -n "$test_name" ]]; then
                process_test "$line_num" "$test_name" "$current_class"
            fi
            has_test_annotation=false
        fi
    done < "$FILE_PATH"
}

# Ruby: Find test_ methods or RSpec it/describe blocks
find_ruby_tests() {
    local line_num=0

    while IFS= read -r line; do
        ((line_num++))

        # RSpec: it "..." or test "..."
        if [[ "$line" =~ (it|test)[[:space:]]+[\"|\'] ]]; then
            local test_name=$(echo "$line" | grep -oP "(it|test)\s+[\"']\K[^\"']+" | head -1)
            if [[ -n "$test_name" ]]; then
                process_test "$line_num" "$test_name" ""
            fi
        fi

        # Minitest: def test_
        if [[ "$line" =~ def[[:space:]]+test_ ]]; then
            local test_name=$(echo "$line" | grep -oP 'def\s+\K[a-z_][a-z0-9_]*')
            process_test "$line_num" "$test_name" ""
        fi
    done < "$FILE_PATH"
}

# PHP: Find @test methods or test* methods
find_php_tests() {
    local line_num=0
    local has_test_annotation=false

    while IFS= read -r line; do
        ((line_num++))

        # Check for @test annotation
        if [[ "$line" =~ @test ]]; then
            has_test_annotation=true
            continue
        fi

        # Check for test method
        if [[ "$has_test_annotation" == true && "$line" =~ function[[:space:]]+ ]] || [[ "$line" =~ function[[:space:]]+test ]]; then
            local test_name=$(echo "$line" | grep -oP 'function\s+\K[a-z][a-zA-Z0-9_]*')
            if [[ -n "$test_name" ]]; then
                process_test "$line_num" "$test_name" ""
            fi
            has_test_annotation=false
        fi
    done < "$FILE_PATH"
}

# ==============================================================================
# Test Processing
# ==============================================================================

# Global array to collect test metadata
declare -a TESTS_ARRAY

# Process a single test and extract metadata
process_test() {
    local line_num="$1"
    local test_name="$2"
    local describe_path="$3"

    # Extract comment before test
    local comment=$(extract_comment_at_line "$line_num")

    # Extract tags from comment
    local spec_number=$(extract_tag "$comment" "spec")
    local user_stories=$(extract_tag_all "$comment" "userStory" | jq -R . | jq -s .)
    local functional_reqs=$(extract_tag_all "$comment" "functionalReq" | jq -R . | jq -s .)
    local test_type=$(extract_tag "$comment" "testType")
    local mock_dependent=$(has_tag "$comment" "mockDependent")
    local retirement_candidate=$(has_tag "$comment" "retirementCandidate")
    local contract_test=$(has_tag "$comment" "contractTest")
    local slow=$(has_tag "$comment" "slow")

    # If no explicit mock tag, check file-level
    if [[ "$mock_dependent" == "false" ]]; then
        mock_dependent=$(detect_mock_dependency)
    fi

    # Infer test type if not explicit
    if [[ -z "$test_type" ]]; then
        test_type=$(infer_test_type)
    fi

    # Generate test ID
    local test_id=$(generate_test_id "$describe_path" "$test_name")

    # Get file dates
    local created_date=$(get_created_date)
    local modified_date=$(get_modified_date)

    # Build describe path array
    local describe_array="[]"
    if [[ -n "$describe_path" ]]; then
        describe_array=$(echo "$describe_path" | tr '::' '\n' | jq -R . | jq -s .)
    fi

    # Extract custom tags (all tags that aren't standard ones)
    local custom_tags=$(echo "$comment" | { grep -oP '@\K[a-zA-Z][a-zA-Z0-9_]*' | grep -vE '^(spec|userStory|functionalReq|testType|mockDependent|retirementCandidate|contractTest|slow)$' || true; } | jq -R . | jq -s .)

    # Build JSON object
    local test_obj=$(jq -n \
        --arg id "$test_id" \
        --arg file "$FILE_PATH" \
        --arg type "$test_type" \
        --argjson describePath "$describe_array" \
        --arg testName "$test_name" \
        --argjson lineNumber "$line_num" \
        --arg specNumber "${spec_number:-null}" \
        --argjson userStories "$user_stories" \
        --argjson functionalReqs "$functional_reqs" \
        --arg testType "${test_type:-null}" \
        --argjson mockDependent "$mock_dependent" \
        --argjson retirementCandidate "$retirement_candidate" \
        --argjson contractTest "$contract_test" \
        --argjson slow "$slow" \
        --arg createdDate "${created_date:-}" \
        --arg lastModified "$modified_date" \
        --argjson tags "$custom_tags" \
        '{
            id: $id,
            file: $file,
            type: $type,
            describePath: $describePath,
            testName: $testName,
            lineNumber: $lineNumber,
            specNumber: (if $specNumber == "null" then null else $specNumber end),
            userStories: $userStories,
            functionalReqs: $functionalReqs,
            testType: (if $testType == "null" then null else $testType end),
            mockDependent: $mockDependent,
            retirementCandidate: $retirementCandidate,
            contractTest: $contractTest,
            slow: $slow,
            createdDate: $createdDate,
            lastModified: $lastModified,
            tags: $tags
        }')

    # Add to array
    TESTS_ARRAY+=("$test_obj")
}

# ==============================================================================
# Main Execution
# ==============================================================================

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo "Error: jq not found. Please install jq for JSON processing" >&2
    exit 1
fi

# Find and process all tests
find_tests

# Build final JSON array
if [[ ${#TESTS_ARRAY[@]} -eq 0 ]]; then
    echo "[]"
else
    # Combine all test objects into a single JSON array
    printf '%s\n' "${TESTS_ARRAY[@]}" | jq -s '.'
fi
