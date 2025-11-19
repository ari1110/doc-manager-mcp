# Test Metadata Schema

**Version:** 2.0.0
**Status:** ✅ Active
**Last Updated:** 2025-11-14

## Overview

All tests must include standardized metadata tags for spec ownership tracking and test lifecycle management. This schema supports multiple programming languages with language-appropriate comment syntax.

**Supported Languages:**
- Python (`.py`)
- JavaScript (`.js`, `.jsx`)
- TypeScript (`.ts`, `.tsx`)
- Go (`.go`)
- Rust (`.rs`)

## Language Support Matrix

| Language | Comment Syntax | Tag Location | Example |
|----------|---------------|--------------|---------|
| **Python** | Docstring `"""..."""` or `#` comments | Above function/class or as first statement | See Python Examples |
| **JavaScript/TypeScript** | JSDoc `/** ... */` | Above function/describe block | See JavaScript Examples |
| **Go** | Line comments `//` | Above function | See Go Examples |
| **Rust** | Doc comments `///` | Above function | See Rust Examples |

## Tag Definitions

### Required Tags

| Tag | Format | Required | Description |
|-----|--------|----------|-------------|
| `@spec` | `@spec <number>` | Yes | Spec number that owns this test (001, 002, 003...) |

### Optional Tags

| Tag | Format | Multiple | Description |
|-----|--------|----------|-------------|
| `@userStory` | `@userStory <code>` | Yes | User story coverage (US1, US2, US10...) |
| `@functionalReq` | `@functionalReq <code>` | Yes | Functional requirement validation (FR-001, FR-031...) |
| `@testType` | `@testType unit\|integration\|e2e` | No | Explicit test type classification |
| `@mockDependent` | `@mockDependent` | No | Flag: test depends on mock API |
| `@retirementCandidate` | `@retirementCandidate` | No | Flag: test marked for planned retirement |
| `@contractTest` | `@contractTest` | No | Flag: test validates API contract parity |
| `@slow` | `@slow` | No | Flag: test has execution time >1s |

## Test Type Classification

If `@testType` not specified, inferred from file path:
- `__tests__/` or `/unit/` → `unit`
- `/integration/` → `integration`
- `/e2e/` or `.e2e.` → `e2e`

## Tag Inheritance

File-level tags apply to all tests in that file. Individual tests can override or add additional tags.

---

## Python Examples

### Basic Test with Tags

```python
"""
@spec 001
@userStory US1
@functionalReq FR-031
@testType unit
"""
def test_authentication():
    """Test user authentication flow."""
    result = authenticate("user", "password")
    assert result == True
```

### Test Class with Tags

```python
class TestWorkspaceList:
    """
    @spec 001
    @userStory US1
    @testType unit
    """

    def test_render_all_workspaces(self, tmp_path):
        """
        @functionalReq FR-031
        """
        workspaces = [
            {"id": "1", "name": "Test 1"},
            {"id": "2", "name": "Test 2"}
        ]
        result = render_workspace_list(workspaces)
        assert len(result) == 2

    def test_empty_state(self):
        """
        @functionalReq FR-034
        @slow
        """
        result = render_workspace_list([])
        assert "no workspaces" in result.lower()
```

### Alternative: Hash Comments

```python
# @spec 001
# @userStory US5
# @testType integration
# @mockDependent
def test_api_integration():
    """Test API integration with mock server."""
    response = mock_api.get("/workspaces")
    assert response.status_code == 200
```

### File-Level Tags (Inheritance)

```python
"""
File-level tags inherited by all tests
@spec 001
@testType integration
@contractTest
"""

import pytest

class TestAPIContracts:
    def test_workspace_creation(self):
        """
        @userStory US2
        """
        # Has: @spec 001, @testType integration, @contractTest, @userStory US2
        pass

    def test_workspace_deletion(self):
        # Has: @spec 001, @testType integration, @contractTest (inherited)
        pass
```

---

## JavaScript/TypeScript Examples

### Basic Test with Tags

```typescript
/**
 * @spec 001
 * @userStory US1
 * @userStory US5
 * @functionalReq FR-031
 * @testType unit
 */
describe('WorkspaceList Component', () => {
  /**
   * @spec 001
   * @userStory US1
   * @functionalReq FR-031
   */
  it('should render all workspaces in the array', () => {
    const workspaces = [
      { id: '1', name: 'Test 1', path: '/test1' },
      { id: '2', name: 'Test 2', path: '/test2' }
    ];

    render(<WorkspaceList workspaces={workspaces} />);

    expect(screen.getByText('Test 1')).toBeInTheDocument();
    expect(screen.getByText('Test 2')).toBeInTheDocument();
  });

  /**
   * @spec 001
   * @userStory US5
   * @functionalReq FR-034
   */
  it('should show empty state when no workspaces', () => {
    render(<WorkspaceList workspaces={[]} />);
    expect(screen.getByText(/no workspaces/i)).toBeInTheDocument();
  });
});
```

### File-Level Tags (Inheritance)

```typescript
/**
 * File-level tags inherited by all tests
 * @spec 001
 * @testType integration
 */

describe('API Contract Tests', () => {
  /**
   * Override/add tags
   * @userStory US2
   * @contractTest
   */
  it('validates workspace creation', () => {
    // Has: @spec 001, @testType integration, @userStory US2, @contractTest
  });

  it('validates workspace deletion', () => {
    // Has: @spec 001, @testType integration (inherited from file)
  });
});
```

---

## Go Examples

### Basic Test with Tags

```go
// @spec 001
// @userStory US1
// @functionalReq FR-031
// @testType unit
func TestAuthentication(t *testing.T) {
    result := Authenticate("user", "password")
    if !result {
        t.Error("Authentication failed")
    }
}
```

### Test with Mock Dependency

```go
// @spec 001
// @userStory US5
// @testType integration
// @mockDependent
func TestAPIIntegration(t *testing.T) {
    mockServer := httptest.NewServer(handler)
    defer mockServer.Close()

    resp, err := http.Get(mockServer.URL + "/workspaces")
    if err != nil {
        t.Fatal(err)
    }
    if resp.StatusCode != 200 {
        t.Errorf("Expected 200, got %d", resp.StatusCode)
    }
}
```

### Benchmark Test

```go
// @spec 001
// @userStory US3
// @testType unit
// @slow
func BenchmarkWorkspaceRendering(b *testing.B) {
    workspaces := generateWorkspaces(1000)
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        RenderWorkspaceList(workspaces)
    }
}
```

---

## Rust Examples

### Basic Test with Tags

```rust
/// @spec 001
/// @userStory US1
/// @functionalReq FR-031
/// @testType unit
#[test]
fn test_authentication() {
    let result = authenticate("user", "password");
    assert_eq!(result, true);
}
```

### Test with Mock Dependency

```rust
/// @spec 001
/// @userStory US5
/// @testType integration
/// @mockDependent
#[test]
fn test_api_integration() {
    let mock_server = MockServer::start();
    let response = Client::new()
        .get(&format!("{}/workspaces", mock_server.url()))
        .send()
        .unwrap();
    assert_eq!(response.status(), 200);
}
```

### Async Test

```rust
/// @spec 001
/// @userStory US2
/// @functionalReq FR-034
/// @testType integration
/// @slow
#[tokio::test]
async fn test_async_workspace_creation() {
    let result = create_workspace("Test Workspace").await;
    assert!(result.is_ok());
}
```

### Test Module with Shared Setup

```rust
#[cfg(test)]
mod workspace_tests {
    use super::*;

    /// @spec 001
    /// @userStory US1
    /// @testType unit
    #[test]
    fn test_workspace_creation() {
        let ws = Workspace::new("Test");
        assert_eq!(ws.name, "Test");
    }

    /// @spec 001
    /// @userStory US1
    /// @testType unit
    #[test]
    fn test_workspace_deletion() {
        let ws = Workspace::new("Test");
        assert!(ws.delete().is_ok());
    }
}
```

---

## Validation

**Enforced by:**
- `test-registry.sh validate` - Checks all tests have valid metadata tags
- Parser: `.claude/skills/speckit/scripts/parse-test-file-universal.ts`

**Validation rules:**
- All test functions/methods must have metadata comment
- Comment must include `@spec` tag
- `@spec` must be 3-digit zero-padded number (001-999)
- No orphaned tests (missing spec ownership)

**Run validation:**
```bash
# Scan all tests and populate registry
test-registry.sh scan

# Validate tag compliance
test-registry.sh validate

# Check for orphaned tests
test-registry.sh report
```

---

## Implementation

**Parser:** `.claude/skills/speckit/scripts/parse-test-file-universal.ts` extracts metadata using tree-sitter AST parsing for all supported languages.

**Auto-Tagger:** `.claude/skills/speckit/scripts/add-test-tags-universal.ts` automatically adds metadata tags to existing tests.

**Registry:** `.claude/skills/speckit/scripts/test-registry.sh` manages test tracking.

**Commands:**
- `test-registry.sh scan` - Update registry from test files (all languages)
- `test-registry.sh report` - Show pyramid metrics and health
- `test-registry.sh spec 001` - List tests for specific spec
- `test-registry.sh retire` - Show tests marked with @retirementCandidate
- `test-registry.sh retire --filter <tag>` - Query tests by any metadata tag
- `test-registry.sh validate` - Check tag compliance

**Retire Command Examples:**
```bash
# Show tests explicitly marked for retirement
test-registry.sh retire

# Show tests that depend on mock API
test-registry.sh retire --filter mockDependent

# Show slow tests (execution time >1s)
test-registry.sh retire --filter slow

# Show contract tests
test-registry.sh retire --filter contractTest
```

---

## Test Detection Patterns

Each language uses specific patterns to identify test functions:

| Language | Test Pattern |
|----------|-------------|
| **Python** | Functions starting with `test_` or classes starting with `Test` |
| **JavaScript/TypeScript** | `describe()`, `it()`, `test()` function calls |
| **Go** | Functions starting with `Test` or `Benchmark` with signature `(t *testing.T)` |
| **Rust** | Functions with `#[test]` or `#[tokio::test]` attribute |

---

## Migration Guide

To add tags to existing tests, use the auto-tagger:

```bash
# Dry run (show what would be changed)
bun .claude/skills/speckit/scripts/add-test-tags-universal.ts --dry-run

# Write tags to files
bun .claude/skills/speckit/scripts/add-test-tags-universal.ts --write
```

The auto-tagger infers metadata from:
- File path → `@spec` (e.g., `specs/001-*/tests/` → `001`)
- File path → `@testType` (e.g., `/integration/` → `integration`)
- Imports → `@mockDependent` (detects mock libraries)
- Existing comments → `@userStory`, `@functionalReq` (extracts US1, FR-031 patterns)
