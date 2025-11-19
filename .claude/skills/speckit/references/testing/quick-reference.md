# Testing Quick Reference

Quick reference for test registry commands and metadata tags. For comprehensive guide, see `references/speckit.testing.md`.

## Test Pyramid Targets

- **70% Unit Tests**: Fast, isolated
- **20% Integration Tests**: Component interactions
- **10% E2E Tests**: Full system flows

## Common Commands

### Setup (First Time)

```bash
# Auto-initializes during first plan, or manually:
.claude/skills/speckit/scripts/test-registry.sh init
```

### Brownfield Projects (Existing Tests)

```bash
# Auto-tag existing untagged tests
.claude/skills/speckit/scripts/test-registry.sh bootstrap --spec 001
```

### Daily Workflow

```bash
# Scan and update registry
.claude/skills/speckit/scripts/test-registry.sh scan

# Show health report
.claude/skills/speckit/scripts/test-registry.sh report

# Query tests for spec
.claude/skills/speckit/scripts/test-registry.sh spec 001

# Validate all tests have @spec tags
.claude/skills/speckit/scripts/test-registry.sh validate
```

### Test Retirement

```bash
# Find retirement candidates
.claude/skills/speckit/scripts/test-registry.sh retire
.claude/skills/speckit/scripts/test-registry.sh retire --filter mockDependent
.claude/skills/speckit/scripts/test-registry.sh retire --filter slow
.claude/skills/speckit/scripts/test-registry.sh retire --filter contractTest
```

## Metadata Tag Cheat Sheet

### Required

```python
# Python (zero-padded 001-999)
"""
@spec 001
"""
def test_feature():
    pass
```

```javascript
// JavaScript/TypeScript
/**
 * @spec 001
 */
it('tests feature', () => {});
```

```go
// Go
// @spec 001
func TestFeature(t *testing.T) {}
```

```rust
// Rust
/// @spec 001
#[test]
fn test_feature() {}
```

### Optional Tags

```python
"""
@spec 001
@testType integration          # Override path-based inference
@userStory US1                 # Link to user story
@functionalReq FR-031          # Link to functional requirement
@mockDependent                 # Uses mocks (retirement candidate)
@slow                          # Takes >1s (optimization candidate)
@retirementCandidate           # Marked for removal
@contractTest                  # API contract test
"""
```

## Test Type Inference

Tests are auto-classified by path if no `@testType` tag:

- `tests/unit/` or `test_*.py` → **unit**
- `tests/integration/` or `*_integration.py` → **integration**
- `tests/e2e/` or `*_e2e.py` or `test_e2e.py` → **e2e**

## Pyramid Health Status

- **HEALTHY**: Ratios within ±10% of targets (70/20/10)
- **WARN**: Inverted pyramid (more integration than unit)
- **CRITICAL**: E2E tests >20% of suite

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "Found N untagged tests" | Run `test-registry.sh bootstrap --spec 001` |
| "Pyramid Status: WARN" | Add unit tests OR retire excessive integration/e2e |
| "OrphanedTests: N" | Run `test-registry.sh bootstrap` or add @spec tags manually |
| "Validate failed" | Add @spec tags to failing tests, then `scan` |

## File Paths

- **Schema**: `.claude/skills/speckit/references/testing/metadata-schema.md`
- **Comprehensive Guide**: `.claude/skills/speckit/references/speckit.testing.md`
- **Test Registry**: `test-registry.json` (auto-generated, repo root)
- **Scripts**: `.claude/skills/speckit/scripts/test-registry.sh`

## Workflow Integration

1. **Specify**: Add test coverage success criteria
2. **Plan**: Bootstrap (if brownfield), load baseline, identify retirements
3. **Tasks**: Generate test tasks with 70/20/10 distribution
4. **Implement**: Tag tests, scan, validate, check pyramid health
5. **Maintain**: Retire obsolete tests, keep pyramid healthy

---

**See also**:
- Full guide: `../speckit.testing.md`
- Tag schema: `metadata-schema.md`
- Skill overview: `../../SKILL.md`
