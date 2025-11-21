# docmgr_assess_quality

Assess documentation quality against 7 criteria with scores and actionable findings.

## Purpose

Evaluates documentation quality using a structured framework of 7 criteria. Provides scores, specific findings, issues, and metrics to track and improve documentation health over time.

## When to use

- Auditing documentation health before releases
- Tracking quality improvements over time
- Identifying high-priority documentation issues
- Establishing documentation quality baselines
- After major content additions or refactoring

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_path` | string | Yes | - | Absolute path to project root |
| `docs_path` | string | No | `null` | Override docs path from config |
| `criteria` | list[string] | No | `null` | Specific criteria to assess (default: all 7) |

## Output

```json
{
  "overall_score": "fair",
  "assessed_at": "2025-11-20T22:15:30.123456",
  "criteria_scores": {
    "relevance": "good",
    "accuracy": "fair",
    "purposefulness": "good",
    "uniqueness": "poor",
    "consistency": "fair",
    "clarity": "good",
    "structure": "good"
  },
  "findings": {
    "relevance": {
      "score": "good",
      "issues": [],
      "positives": ["Documentation addresses current features"],
      "metrics": {
        "outdated_references": 2,
        "total_pages": 12
      }
    },
    "accuracy": {
      "score": "fair",
      "issues": [
        "13 documented symbols not found in codebase",
        "API coverage at 6.7% (13/195 symbols)"
      ],
      "positives": ["Code examples are syntactically valid"],
      "metrics": {
        "api_coverage": 6.7,
        "documented_symbols": 13,
        "total_symbols": 195
      }
    }
  },
  "summary": {
    "strengths": ["Clear structure", "Good purposefulness"],
    "weaknesses": ["Low API coverage", "Duplicate topics", "Missing language tags"],
    "recommendations": [
      "Document more public APIs",
      "Consolidate duplicate content",
      "Add language tags to code blocks"
    ]
  }
}
```

## Examples

### Full quality assessment

```python
await mcp.call_tool("docmgr_assess_quality", {
  "project_path": "/path/to/project"
})
```

### Assess specific criteria

```python
await mcp.call_tool("docmgr_assess_quality", {
  "project_path": "/path/to/project",
  "criteria": ["accuracy", "consistency", "clarity"]
})
```

### Custom docs path

```python
await mcp.call_tool("docmgr_assess_quality", {
  "project_path": "/path/to/project",
  "docs_path": "documentation"
})
```

## Quality criteria

### 1. Relevance
**What it measures**: Documentation addresses current user needs and isn't outdated

**Good indicators**:
- Up-to-date feature coverage
- No references to deprecated features
- Addresses common user questions

**Poor indicators**:
- Outdated screenshots or examples
- References to removed features
- Missing coverage of new features

### 2. Accuracy
**What it measures**: Documentation reflects actual codebase state

**Good indicators**:
- High API coverage (documented vs total symbols)
- Documented symbols exist in codebase
- Code examples are valid and tested

**Poor indicators**:
- Low API coverage (<20%)
- Documented symbols don't exist
- Broken code examples

### 3. Purposefulness
**What it measures**: Clear goals and target audience for each document

**Good indicators**:
- Clear introduction stating purpose
- Defined target audience
- Focused content without drift

**Poor indicators**:
- Unclear document purpose
- Mixed audiences in same doc
- Meandering content

### 4. Uniqueness
**What it measures**: No redundant or conflicting information

**Good indicators**:
- Each topic covered once
- No contradictory information
- Clear information hierarchy

**Poor indicators**:
- Duplicate content across files
- Conflicting instructions
- Redundant examples

### 5. Consistency
**What it measures**: Aligned terminology, formatting, and style

**Good indicators**:
- Consistent heading styles
- Uniform code formatting
- Standardized terminology

**Poor indicators**:
- Mixed heading case
- Inconsistent code block formatting
- Same concept with different names

### 6. Clarity
**What it measures**: Precise language and easy navigation

**Good indicators**:
- Concise sentences (<25 words)
- Active voice
- Clear navigation structure
- Minimal vague language

**Poor indicators**:
- Long, complex sentences
- Passive voice overuse
- Vague terms ("just", "simply", "easy")
- Poor navigation

### 7. Structure
**What it measures**: Logical organization and hierarchy

**Good indicators**:
- Logical heading hierarchy (no skipped levels)
- Table of contents for long documents
- Clear section organization

**Poor indicators**:
- Skipped heading levels (H1 → H3)
- Missing TOC on long documents
- Disorganized sections

## Score meanings

- **good**: Meets or exceeds quality standards
- **fair**: Acceptable but has room for improvement
- **poor**: Needs significant improvement

## Notes

- **Read-only**: Only analyzes documentation, makes no changes
- **Comprehensive**: Assesses content, structure, and technical accuracy
- **Actionable**: Provides specific issues and recommendations
- **Metrics-driven**: Includes quantifiable measurements
- **Root README**: Includes root README.md if `include_root_readme: true` in config
- **Prerequisites**: Requires baselines for accuracy assessment

## Typical workflow

```
1. Run docmgr_assess_quality to get baseline scores
2. Review findings and recommendations
3. Make improvements based on issues identified
4. Re-run assessment to track progress
5. Monitor quality trends over time
```

## See also

- [docmgr_validate_docs](docmgr_validate_docs.md) - Technical validation checks
- [Documentation conventions](../file-formats.md#doc-managermemorydoc-conventionsyml)
- [Quality improvement guide](../../guides/workflows.md)
