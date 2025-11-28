---
description: Assess documentation quality
---

# Documentation Quality Assessment

Run comprehensive quality assessment against 7 criteria.

@doc-expert Please run a documentation quality assessment.

Execute the quality assessment workflow:

1. **Run Assessment**: Execute `docmgr_assess_quality` to evaluate documentation against 7 criteria:
   - Relevance
   - Accuracy
   - Purposefulness
   - Uniqueness
   - Consistency
   - Clarity
   - Structure

2. **Also Run Validation**: Execute `docmgr_validate_docs` to check:
   - Broken links
   - Missing assets
   - Code snippet syntax
   - Convention compliance

3. **Present Findings**: Provide a comprehensive report with:
   - Overall quality score
   - Per-criterion scores
   - Specific issues with file paths and line numbers
   - Validation results
   - Actionable recommendations

Format the output:

```
## Documentation Quality Report

### Overall Assessment: {excellent | good | fair | poor}

### Quality Scores

| Criterion | Score | Issues |
|-----------|-------|--------|
| Relevance | {score} | {count} |
| Accuracy | {score} | {count} |
| Purposefulness | {score} | {count} |
| Uniqueness | {score} | {count} |
| Consistency | {score} | {count} |
| Clarity | {score} | {count} |
| Structure | {score} | {count} |

### Validation Results
- **Links**: {count} checked, {count} issues
- **Assets**: {count} checked, {count} issues
- **Code Snippets**: {count} checked, {count} issues

### Specific Issues

**High Priority** (poor scores):
- {file}:{line} - {issue description}

**Medium Priority** (fair scores):
- {file}:{line} - {issue description}

### Recommendations
1. {actionable recommendation}
2. {actionable recommendation}

### Next Steps
- Fix high-priority issues first
- Run /doc-sync after fixes to update baseline
```

If user wants to fix issues:
```
Would you like me to help fix these issues? I can delegate the revisions to @doc-writer.
```
