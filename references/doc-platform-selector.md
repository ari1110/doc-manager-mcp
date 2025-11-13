# Documentation Platform Selection Guide

This reference provides a decision framework for choosing the best documentation platform for a project. Use this in the `docmgr_detect_platform` and `docmgr_bootstrap` tools.

## Platform Overview

| Platform | Language | Best For | Learning Curve | Build Speed | Ecosystem |
|----------|----------|----------|----------------|-------------|-----------|
| **Hugo** | Go | Speed, simplicity | Low | Very Fast | Large |
| **Docusaurus** | React/JS | Modern features, versioning | Medium | Fast | Growing |
| **MkDocs** | Python | Python projects, simplicity | Low | Fast | Moderate |
| **Sphinx** | Python | API docs, technical writing | High | Moderate | Large |
| **VitePress** | Vue/JS | Vue projects, modern DX | Low | Very Fast | Growing |
| **Jekyll** | Ruby | GitHub Pages, blogs | Low | Slow | Large |
| **GitBook** | N/A (SaaS) | Teams, collaboration | Very Low | N/A | Proprietary |

---

## Decision Tree

### Step 1: Identify Project Constraints

**Question 1: Is this a commercial/team project with budget?**
- **Yes** → Consider GitBook (best collaboration features)
- **No** → Continue to Step 2

**Question 2: What is the primary programming language?**
- **Go** → Hugo (same ecosystem, fast builds)
- **Python** → MkDocs or Sphinx
- **JavaScript/TypeScript** → Docusaurus or VitePress
- **Ruby** → Jekyll
- **Other/Multiple** → Hugo (language-agnostic, widely adopted)

**Question 3: Do you need API documentation generation?**
- **Yes** → Sphinx (best autodoc), or language-specific + platform
- **No** → Continue to Step 3

**Question 4: Do you need versioning for multiple releases?**
- **Yes** → Docusaurus (built-in versioning)
- **No** → Continue to Step 4

**Question 5: What is your team's skill level with web technologies?**
- **Expert** → Any platform
- **Intermediate** → Docusaurus, VitePress, Hugo
- **Beginner** → MkDocs, Hugo (simplest)

---

## Platform Details

### Hugo

**Pros:**
- Fastest build times (< 1 second for most sites)
- Single binary, no dependencies
- Large theme ecosystem
- Excellent for large sites (1000+ pages)
- Language-agnostic

**Cons:**
- Go template syntax can be tricky
- Less JavaScript-heavy features
- Theme customization requires Go template knowledge

**Best For:**
- Large documentation sites
- Go projects
- Teams wanting minimal dependencies
- Speed-critical builds (CI/CD)

**Detection Signals:**
- `hugo.toml`, `hugo.yaml`, `config.toml`
- `themes/` directory
- `content/` directory

**Recommendation Logic:**
```python
if language == "Go" or site_size > 500_pages:
    return "hugo"
```

---

### Docusaurus

**Pros:**
- React-based, modern UI/UX
- Built-in versioning
- Plugin ecosystem
- MDX support (JSX in Markdown)
- Excellent developer experience

**Cons:**
- Heavier build (Node.js required)
- Slower than Hugo for very large sites
- Requires Node/npm knowledge

**Best For:**
- JavaScript/TypeScript projects
- Projects needing versioning
- Modern, interactive docs
- Teams comfortable with React

**Detection Signals:**
- `docusaurus.config.js`, `docusaurus.config.ts`
- `docs/` and `blog/` directories
- `package.json` with `@docusaurus/core`

**Recommendation Logic:**
```python
if language == "JavaScript/TypeScript" or needs_versioning:
    return "docusaurus"
```

---

### MkDocs

**Pros:**
- Simplest configuration (single YAML file)
- Python-based (pip install)
- Material theme is beautiful
- Fast builds
- Easy to learn

**Cons:**
- Less plugin ecosystem than Hugo
- Not ideal for very large sites
- Limited customization without plugins

**Best For:**
- Python projects
- Small to medium sites
- Teams wanting simplicity
- Beautiful default themes

**Detection Signals:**
- `mkdocs.yml`
- `docs/` directory
- `site/` output directory

**Recommendation Logic:**
```python
if language == "Python" and not needs_advanced_features:
    return "mkdocs"
```

---

### Sphinx

**Pros:**
- Best-in-class API documentation
- reStructuredText support
- Extensive Python autodoc
- Used by major Python projects
- Very powerful

**Cons:**
- Steep learning curve
- reStructuredText is less popular than Markdown
- Requires Python knowledge
- Slower builds

**Best For:**
- Python projects with extensive APIs
- Technical documentation requiring precise control
- Projects already using Sphinx

**Detection Signals:**
- `conf.py` in docs directory
- `_build/`, `_static/`, `_templates/` directories
- `.rst` files

**Recommendation Logic:**
```python
if language == "Python" and needs_api_docs:
    return "sphinx"
```

---

### VitePress

**Pros:**
- Vue-based, modern
- Lightning-fast dev server (Vite)
- Simple Markdown-focused
- Great theming
- Low learning curve

**Cons:**
- Smaller ecosystem than Docusaurus
- Vue-specific (less general-purpose)
- Younger project

**Best For:**
- Vue projects
- Modern, fast developer experience
- Markdown-focused documentation

**Detection Signals:**
- `.vitepress/config.js`, `.vitepress/config.ts`
- `docs/` directory
- `package.json` with `vitepress`

**Recommendation Logic:**
```python
if language == "JavaScript/TypeScript" and uses_vue:
    return "vitepress"
```

---

### Jekyll

**Pros:**
- GitHub Pages native support
- Ruby-based
- Large theme ecosystem
- Battle-tested

**Cons:**
- Slow builds (Ruby performance)
- Less modern features
- Declining popularity

**Best For:**
- GitHub Pages hosting
- Ruby projects
- Simple blogs/docs
- Legacy projects

**Detection Signals:**
- `_config.yml`
- `_posts/`, `_layouts/`, `_includes/` directories
- `Gemfile` with `jekyll`

**Recommendation Logic:**
```python
if uses_github_pages or language == "Ruby":
    return "jekyll"
```

---

## Advanced Considerations

### Performance Requirements

**Large sites (1000+ pages):**
1. Hugo (fastest)
2. VitePress (fast dev, good build)
3. Docusaurus (slower but acceptable)
4. MkDocs (not recommended for very large sites)

### Customization Needs

**High customization:**
1. Docusaurus (React components)
2. Hugo (powerful templating)
3. Sphinx (Python extensions)
4. VitePress (Vue components)

**Low customization (use themes as-is):**
1. MkDocs Material (beautiful defaults)
2. Hugo (many ready themes)
3. Jekyll (many themes)

### Team Preferences

**Prefer Markdown:**
- MkDocs, Hugo, Docusaurus, VitePress

**Comfortable with React:**
- Docusaurus

**Comfortable with Vue:**
- VitePress

**Want simplicity:**
- MkDocs (simplest)
- Hugo (simple after setup)

---

## Migration Paths

### From Jekyll → Hugo
- Moderate effort
- Content mostly compatible
- Frontmatter similar

### From MkDocs → Docusaurus
- Moderate effort
- Markdown compatible
- Need to restructure navigation

### From Sphinx → MkDocs
- High effort (reStructuredText → Markdown)
- Consider MyST parser for Sphinx Markdown support

### From GitBook → Any
- Low effort (Markdown-based)
- Export content and import

---

## Implementation in `docmgr_detect_platform`

```python
async def detect_platform(params: DetectPlatformInput) -> str:
    # Step 1: Check for existing platform (high confidence)
    detected = _detect_existing_platform(project_path)
    if detected:
        return _format_recommendation(detected, "existing")

    # Step 2: Analyze project characteristics
    language = _detect_language(project_path)
    size = _estimate_doc_size(project_path)
    needs_versioning = _check_versioning_need(project_path)
    needs_api_docs = _check_api_docs_need(project_path)

    # Step 3: Apply decision logic
    if language == "Python" and needs_api_docs:
        recommendation = "sphinx"
    elif language == "Python":
        recommendation = "mkdocs"
    elif language == "Go" or size > 500:
        recommendation = "hugo"
    elif language == "JavaScript/TypeScript" and needs_versioning:
        recommendation = "docusaurus"
    elif language == "JavaScript/TypeScript":
        recommendation = "vitepress"
    else:
        recommendation = "hugo"  # Default fallback

    return _format_recommendation(recommendation, "recommended")
```

---

## Fallback Strategy

If unable to determine ideal platform:

1. **Default to Hugo** (most versatile, fast, language-agnostic)
2. **Provide rationale**: "Hugo is fast, widely adopted, and works well for most use cases"
3. **Offer alternatives**: List 2-3 alternatives based on language

---

**Last Updated**: 2025-01-13
