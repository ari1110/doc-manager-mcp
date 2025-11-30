# Documentation Conventions Reference

Complete reference for `doc-conventions.yml` configuration options.

## File Location

Conventions file: `<project_root>/.doc-manager/doc-conventions.yml`

## Overview

Documentation conventions define style, structure, quality, and terminology rules that are enforced during validation and quality assessment.

---

## style Section

Controls heading, code, and voice conventions.

### style.headings

```yaml
style:
  headings:
    case: sentence_case  # or title_case, lower, upper
    consistency_required: true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `case` | `string` | `null` | Required heading case style |
| `consistency_required` | `boolean` | `true` | Enforce consistent case throughout |

**Case options**:
- `sentence_case`: Only first word capitalized (e.g., "Getting started with the API")
- `title_case`: Major words capitalized (e.g., "Getting Started with the API")
- `lower`: All lowercase
- `upper`: All uppercase

### style.code

```yaml
style:
  code:
    inline_format: backticks  # or html
    block_language_required: true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `inline_format` | `string` | `backticks` | Format for inline code |
| `block_language_required` | `boolean` | `true` | Require language in code blocks |

### style.voice

```yaml
style:
  voice:
    person: second  # first, second, or third
    active_voice_preferred: true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `person` | `string` | `second` | Grammatical person (first/second/third) |
| `active_voice_preferred` | `boolean` | `true` | Prefer active voice |

---

## structure Section

Controls document organization rules.

### structure.require_intro

```yaml
structure:
  require_intro: true
```

Require introductory paragraph before first heading.

**Type**: `boolean`
**Default**: `true`

### structure.require_toc

```yaml
structure:
  require_toc:
    enabled: true
    min_length: 500  # words
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `boolean` | `true` | Whether to require TOC |
| `min_length` | `integer` | `500` | Minimum document length (words) to require TOC |

### structure.max_heading_depth

```yaml
structure:
  max_heading_depth: 3
```

Maximum heading depth allowed (1-6).

**Type**: `integer`
**Default**: `3`

### structure.heading_hierarchy

```yaml
structure:
  heading_hierarchy: strict  # or relaxed
```

| Value | Description |
|-------|-------------|
| `strict` | No level skipping (H1 → H2 → H3, not H1 → H3) |
| `relaxed` | Allow level skipping |

**Default**: `strict`

---

## quality Section

Controls validation rules for content quality.

### quality.sentences

```yaml
quality:
  sentences:
    max_length: 25  # words
    min_length: 3
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_length` | `integer` | `25` | Maximum sentence length in words |
| `min_length` | `integer` | `3` | Minimum sentence length in words |

### quality.paragraphs

```yaml
quality:
  paragraphs:
    max_length: 150  # words
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_length` | `integer` | `150` | Maximum paragraph length in words |

### quality.links

```yaml
quality:
  links:
    validate_links: true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `validate_links` | `boolean` | `true` | Validate all links are reachable |

### quality.images

```yaml
quality:
  images:
    require_alt_text: true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `require_alt_text` | `boolean` | `true` | All images must have descriptive alt text |

### quality.code

```yaml
quality:
  code:
    validate_syntax: false
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `validate_syntax` | `boolean` | `false` | Validate code syntax (requires TreeSitter, expensive) |

---

## terminology Section

Controls terminology consistency and avoidance rules.

### terminology.preferred

Define preferred terminology for consistency checking.

```yaml
terminology:
  preferred:
    mcp:
      full_form: "Model Context Protocol"
      abbreviation: "MCP"
      guidance: "Spell out on first use, abbreviate after"
    api:
      full_form: "Application Programming Interface"
      abbreviation: "API"
```

Each entry has:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `full_form` | `string` | Yes | Full form of the term |
| `abbreviation` | `string` | No | Abbreviated form |
| `guidance` | `string` | No | Usage guidance |

### terminology.avoid

Define words or phrases to avoid with optional exceptions.

```yaml
terminology:
  avoid:
    - word: "simply"
      reason: "Implies task is easy, can be condescending"
    - word: "just"
      reason: "Minimizes complexity"
      exceptions:
        - "just-in-time"
    - word: "easy"
      reason: "Subjective, may frustrate users"
    - word: "obvious"
      reason: "What's obvious varies by experience level"
```

Each entry has:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `word` | `string` | Yes | Word or phrase to avoid |
| `reason` | `string` | No | Explanation why to avoid |
| `exceptions` | `list[string]` | No | Phrases that should not be flagged |

---

## Complete Example

```yaml
# .doc-manager/doc-conventions.yml

style:
  headings:
    case: sentence_case
    consistency_required: true
  code:
    inline_format: backticks
    block_language_required: true
  voice:
    person: second
    active_voice_preferred: true

structure:
  require_intro: true
  require_toc:
    enabled: true
    min_length: 500
  max_heading_depth: 4
  heading_hierarchy: strict

quality:
  sentences:
    max_length: 30
    min_length: 3
  paragraphs:
    max_length: 200
  links:
    validate_links: true
  images:
    require_alt_text: true
  code:
    validate_syntax: false

terminology:
  preferred:
    mcp:
      full_form: "Model Context Protocol"
      abbreviation: "MCP"
      guidance: "Spell out on first use"
    api:
      full_form: "Application Programming Interface"
      abbreviation: "API"
  avoid:
    - word: "simply"
      reason: "Implies task is easy"
    - word: "just"
      reason: "Minimizes complexity"
      exceptions:
        - "just-in-time"
    - word: "easy"
      reason: "Subjective"
    - word: "obvious"
      reason: "Experience-dependent"
```

---

## Minimal Example

For projects wanting basic consistency without strict rules:

```yaml
# Minimal conventions - just the essentials

style:
  headings:
    case: sentence_case
  code:
    block_language_required: true

structure:
  heading_hierarchy: strict

quality:
  images:
    require_alt_text: true

terminology:
  avoid:
    - word: "simply"
    - word: "obviously"
```

---

## When to Use Conventions

**Recommended for**:
- Teams with multiple documentation contributors
- Projects with consistency issues detected by quality assessment
- Maintaining brand/style consistency across docs
- Enforcing accessibility requirements (alt text)

**Optional for**:
- Solo projects
- Projects with established conventions
- Documentation that rarely changes

---

## Integration with Quality Assessment

When conventions are defined, `docmgr_assess_quality` will:

1. **Check heading case** against `style.headings.case`
2. **Check heading hierarchy** against `structure.heading_hierarchy`
3. **Flag code blocks** missing language per `style.code.block_language_required`
4. **Flag avoided terms** per `terminology.avoid`
5. **Report preferred term usage** per `terminology.preferred`

Issues appear in the quality assessment report under relevant criteria (Consistency, Clarity, etc.).
