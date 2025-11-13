# Documentation Quality Assessment Criteria

This reference provides detailed rubrics for evaluating documentation against seven essential quality dimensions. Use these criteria consistently across all workflow modes to ensure comprehensive quality assessment.

## 1. Relevance

**Definition**: Documentation addresses current user needs, use cases, and pain points.

**Assessment Questions**:
- Does the documentation cover features and workflows users actually need?
- Are examples drawn from realistic use cases?
- Does it address common user questions and pain points?
- Is outdated content (deprecated features, obsolete workflows) removed or clearly marked?

**Quality Levels**:
- **Excellent**: All content directly supports user goals; examples match real-world usage; deprecated content clearly marked with migration paths
- **Good**: Most content relevant; some outdated sections remain but don't mislead
- **Fair**: Mix of relevant and outdated content; unclear what's current
- **Poor**: Significant outdated content; examples don't match actual usage; user needs not addressed

**Common Issues**:
- Documentation for removed features still present
- Examples using deprecated APIs without migration guidance
- Focus on developer implementation details instead of user tasks
- Missing documentation for frequently-used features

## 2. Accuracy

**Definition**: Information correctly reflects the actual codebase, APIs, and system behavior.

**Assessment Questions**:
- Do code examples execute successfully with current codebase?
- Do CLI command examples produce the documented output?
- Do configuration schemas match actual implementation?
- Are API signatures (parameters, return types) correct?
- Do troubleshooting steps actually resolve the described issues?

**Quality Levels**:
- **Excellent**: All examples tested and work; command outputs match; schemas verified against code
- **Good**: Minor discrepancies in non-critical areas (formatting, optional parameters)
- **Fair**: Some examples fail or produce different output; schemas partially outdated
- **Poor**: Significant inaccuracies; examples don't work; misleading information

**Common Issues**:
- Code examples with syntax errors or missing imports
- Command examples showing outdated flag names or output formats
- Configuration schemas missing required fields or showing wrong types
- Screenshots from older versions showing different UI
- Incorrect troubleshooting advice

**Validation Methods**:
- Execute all code examples (copy-paste test)
- Run all CLI commands in documented scenarios
- Parse configuration examples with actual parsers
- Compare API signatures with source code
- Test troubleshooting steps on actual issues

## 3. Purposefulness

**Definition**: Each document has clear goals, target audience, and success criteria.

**Assessment Questions**:
- Is it clear who this document is for (end users, developers, operators)?
- What should the reader be able to do after reading this?
- Does the document have a single, focused purpose?
- Is the scope appropriate for the stated purpose?

**Quality Levels**:
- **Excellent**: Clear audience stated; measurable learning objectives; focused scope; appropriate depth
- **Good**: Audience and purpose inferable; mostly focused with minor tangents
- **Fair**: Multiple purposes mixed; unclear target audience; scope creep
- **Poor**: No clear purpose; tries to serve everyone; unfocused content

**Common Issues**:
- Mixing beginner tutorials with advanced reference material
- Combining user guides with implementation details
- No clear indication of prerequisites or target skill level
- Document scope too broad or too narrow for stated purpose

**Document Purpose Archetypes**:
- **Tutorial**: Enable complete beginner to accomplish specific task (step-by-step, narrow scope)
- **How-To Guide**: Help user solve specific problem (goal-oriented, assumes basic knowledge)
- **Reference**: Provide comprehensive technical details (exhaustive, lookup-focused)
- **Explanation**: Build understanding of concepts (theory-focused, educational)

## 4. Uniqueness

**Definition**: No redundant, conflicting, or duplicate information across documentation.

**Assessment Questions**:
- Is information about a topic found in only one canonical location?
- Do different documents provide conflicting instructions or explanations?
- Are cross-references used instead of duplicating content?
- Is there a clear information architecture preventing duplication?

**Quality Levels**:
- **Excellent**: Single source of truth for each topic; cross-references used; no conflicts
- **Good**: Minimal duplication; any repeated content identical; no conflicts
- **Fair**: Some duplication; minor conflicts between documents
- **Poor**: Widespread duplication; conflicting information; unclear which source is authoritative

**Common Issues**:
- Installation instructions duplicated in README, Getting Started, and Contributing guides
- Configuration documented in multiple places with different examples
- API reference information scattered across multiple documents
- Conflicting version requirements between different guides
- Same examples repeated across multiple tutorials

**Resolution Strategies**:
- Establish canonical location for each topic
- Use includes/partials for repeated content
- Replace duplicates with links to canonical source
- Create single source of truth documents (e.g., single configuration reference)

## 5. Consistency

**Definition**: Terminology, formatting, structure, and style align throughout documentation.

**Assessment Questions**:
- Are technical terms used consistently (not alternating between synonyms)?
- Do similar document types follow the same structure?
- Is formatting consistent (headings, code blocks, lists, emphasis)?
- Is voice and tone consistent (formal/informal, active/passive)?
- Are examples formatted consistently?

**Quality Levels**:
- **Excellent**: Glossary defines terms; style guide followed; structural templates used; formatting uniform
- **Good**: Generally consistent with occasional deviations; terminology mostly uniform
- **Fair**: Noticeable inconsistencies; multiple terms for same concept; varying structure
- **Poor**: Highly inconsistent; confusing terminology; no apparent standards

**Consistency Dimensions**:

### Terminology
- Feature names (always use canonical name)
- Technical terms (e.g., "credential" vs "password entry" vs "secret")
- Product names (correct capitalization and branding)
- UI elements (button names, menu paths)

### Structure
- Heading hierarchy (consistent H1/H2/H3 usage)
- Section ordering (prerequisites before procedure)
- Document templates for similar doc types

### Formatting
- Code block language tags (always specify language)
- Command syntax (consistent prompt style: `$`, `>`, none)
- File path notation (absolute vs relative)
- Inline code vs code blocks (when to use each)
- Admonitions/callouts (consistent usage of NOTE, WARNING, TIP)

### Style
- Voice (second person "you" vs third person vs imperative)
- Tense (present vs future for instructions)
- Active vs passive voice
- Contractions (don't vs do not)

## 6. Clarity

**Definition**: Language is precise, examples are concrete, and navigation is intuitive.

**Assessment Questions**:
- Can users quickly find what they need?
- Are instructions unambiguous and actionable?
- Are abstractions illustrated with concrete examples?
- Is navigation clear (table of contents, breadcrumbs, cross-links)?
- Is technical jargon explained or avoided when possible?

**Quality Levels**:
- **Excellent**: No ambiguity; step-by-step procedures; concrete examples; excellent navigation; glossary for jargon
- **Good**: Generally clear; minor ambiguities; most terms explained; decent navigation
- **Fair**: Some vague instructions; abstract explanations; weak navigation
- **Poor**: Confusing instructions; heavy unexplained jargon; difficult to navigate; abstract without examples

**Clarity Components**:

### Precision
- Specific rather than vague language ("Run `npm install`" not "Install dependencies")
- Exact names and paths ("`config/app.yaml`" not "the config file")
- Quantified rather than subjective ("< 100ms" not "fast")

### Concreteness
- Every concept illustrated with example
- Abstract patterns shown in real code
- Commands shown with actual output
- Screenshots for complex UI interactions

### Actionability
- Instructions in imperative form ("Click Submit" not "Submit button should be clicked")
- Numbered steps for procedures
- Expected outcomes stated ("You should see: ...")
- Clear entry and exit criteria

### Navigation
- Table of contents for long documents
- Breadcrumbs showing location in hierarchy
- Cross-links to related topics
- Search-friendly headings (descriptive, keyword-rich)
- Next steps / related resources sections

## 7. Structure

**Definition**: Logical organization with appropriate depth, hierarchy, and progressive disclosure.

**Assessment Questions**:
- Is information organized logically (by user task, by feature, by difficulty)?
- Does heading hierarchy reflect content relationships?
- Is content depth appropriate (not too shallow, not overwhelming)?
- Does structure support progressive disclosure (simple to complex)?
- Can users scan and skip to relevant sections?

**Quality Levels**:
- **Excellent**: Logical organization; clear hierarchy; scannable; appropriate depth; progressive disclosure
- **Good**: Generally well-organized; some sections could be restructured; mostly scannable
- **Fair**: Inconsistent organization; heading hierarchy issues; difficult to scan
- **Poor**: No clear organization; flat structure; information buried; hard to navigate

**Structural Patterns**:

### Organization Schemes
- **Task-based**: Organized by what user wants to accomplish (most user-friendly)
- **Feature-based**: Organized by system capabilities (good for reference)
- **Role-based**: Organized by user type (developer, operator, end-user)
- **Sequential**: Ordered by workflow or difficulty (good for learning paths)

### Heading Hierarchy
- One H1 per document (document title)
- H2 for major sections
- H3 for subsections
- H4 rarely needed (consider restructuring if deeper)
- Headings describe content (not just "Overview", "Details")

### Depth Management
- Summaries for long sections
- Expandable details (collapsible sections, separate pages)
- "See also" links for deep-dives
- Separation of reference (exhaustive) from guides (focused)

### Progressive Disclosure
- Start with most common use case
- Simple examples before complex
- Core concepts before advanced topics
- Gradual introduction of parameters/options

## Assessment Workflow

When evaluating documentation against these criteria:

1. **Inventory**: List all documentation files and their stated purposes
2. **Sample**: For large doc sets, sample representative documents (README, 2-3 guides, reference doc)
3. **Evaluate**: Score each document on each criterion (Excellent/Good/Fair/Poor)
4. **Document findings**: Note specific examples of issues with file:line references
5. **Prioritize**: Focus on critical issues (accuracy, relevance) before polish issues (consistency)
6. **Report**: Summarize by criterion with concrete examples and severity

## Integration with Workflow Modes

- **Bootstrap Mode**: Use criteria to design initial documentation structure
- **Sync Mode**: Validate accuracy and relevance after code changes
- **Validation Mode**: Quick checks focus on accuracy and consistency
- **Audit Mode**: Comprehensive evaluation across all seven criteria
