# Platform support

Doc-manager supports multiple documentation platforms with platform-specific features and conventions.

## Supported platforms

### MkDocs

**Best for**: Python projects, simple documentation needs, Material theme users

**Detection**: Looks for `mkdocs.yml` or `mkdocs.yaml` in project root

**Configuration files**:
- `mkdocs.yml` - Main configuration
- `docs/` - Default documentation directory

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: mkdocs
docs_path: docs
```

**Conventions**:
- Uses `index.md` as landing page
- Supports nested directory structure
- Markdown-based with CommonMark + extensions

**Resources**:
- [MkDocs documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)

### Sphinx

**Best for**: Python projects with extensive API documentation, ReadTheDocs users

**Detection**: Looks for `conf.py` in `docs/` directory or project root

**Configuration files**:
- `docs/conf.py` - Sphinx configuration
- `docs/index.rst` - Landing page (reStructuredText)

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: sphinx
docs_path: docs
```

**Conventions**:
- Supports both `.rst` and `.md` (with MyST parser)
- Directive-based (e.g., `.. toctree::`)
- Strong autodoc capabilities

**Resources**:
- [Sphinx documentation](https://www.sphinx-doc.org/)
- [ReadTheDocs](https://readthedocs.org/)

### Hugo

**Best for**: Go projects, fast static sites, multi-language documentation

**Detection**: Looks for `config.toml`, `hugo.toml`, `config.yaml`, or `config.json`

**Configuration files**:
- `config.toml` (or `.yaml`, `.json`) - Hugo configuration
- `content/` - Default content directory

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: hugo
docs_path: content
```

**Conventions**:
- Frontmatter-driven (YAML, TOML, JSON)
- Section-based organization
- Fast builds for large sites

**Resources**:
- [Hugo documentation](https://gohugo.io/documentation/)
- [Hugo themes](https://themes.gohugo.io/)

### Docusaurus

**Best for**: JavaScript/React projects, versioned documentation, internationalization

**Detection**: Looks for `docusaurus.config.js` or `docusaurus.config.ts`

**Configuration files**:
- `docusaurus.config.js` - Main configuration
- `docs/` - Documentation directory
- `blog/` - Blog directory (optional)

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: docusaurus
docs_path: docs
```

**Conventions**:
- MDX support (Markdown + JSX)
- Built-in versioning and i18n
- React component integration

**Resources**:
- [Docusaurus documentation](https://docusaurus.io/)
- [Docusaurus showcase](https://docusaurus.io/showcase)

### VitePress

**Best for**: Vue projects, modern documentation sites, Vite users

**Detection**: Looks for `.vitepress/config.js` or `.vitepress/config.ts`

**Configuration files**:
- `.vitepress/config.js` - VitePress configuration
- `docs/` or root - Documentation files

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: vitepress
docs_path: docs
```

**Conventions**:
- Markdown with Vue components
- Fast hot module replacement
- Vite-powered builds

**Resources**:
- [VitePress documentation](https://vitepress.dev/)
- [VitePress guide](https://vitepress.dev/guide/)

### Jekyll

**Best for**: Ruby projects, GitHub Pages, simple blogs

**Detection**: Looks for `_config.yml` in project root

**Configuration files**:
- `_config.yml` - Jekyll configuration
- `_posts/` - Blog posts
- `docs/` or root - Documentation

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: jekyll
docs_path: docs
```

**Conventions**:
- Liquid templating
- Frontmatter-based metadata
- GitHub Pages integration

**Resources**:
- [Jekyll documentation](https://jekyllrb.com/docs/)
- [GitHub Pages](https://pages.github.com/)

### GitBook

**Best for**: Product documentation, team wikis, hosted documentation

**Detection**: Looks for `.gitbook.yaml` or `book.json`

**Configuration files**:
- `.gitbook.yaml` - GitBook configuration
- `SUMMARY.md` - Table of contents

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: gitbook
docs_path: docs
```

**Conventions**:
- `SUMMARY.md` defines structure
- Simple Markdown-based
- Can be hosted or self-hosted

**Resources**:
- [GitBook documentation](https://docs.gitbook.com/)

### Unknown / Custom

**When to use**: No specific platform, custom static site generator, plain Markdown

**Doc-manager integration**:
```yaml
# .doc-manager.yml
platform: unknown
docs_path: docs
```

**Notes**:
- Generic Markdown conventions applied
- No platform-specific features
- Validation and quality assessment still work

---

## Platform detection

Use `docmgr_detect_platform` to automatically identify your platform:

```json
{
  "tool": "docmgr_detect_platform",
  "arguments": {
    "project_path": "/path/to/project"
  }
}
```

### Detection logic

1. **Check for config files** in project root and docs directory:
   - MkDocs: `mkdocs.yml`, `mkdocs.yaml`
   - Sphinx: `conf.py`
   - Hugo: `config.toml`, `hugo.toml`, etc.
   - Docusaurus: `docusaurus.config.js`
   - VitePress: `.vitepress/config.js`
   - Jekyll: `_config.yml`
   - GitBook: `.gitbook.yaml`, `book.json`

2. **Return confidence level**:
   - `high`: Config file found with matching directory structure
   - `medium`: Config file found but unclear structure
   - `low`: No config file, recommending based on project language

3. **Provide recommendations** if platform not detected:
   - Analyzes project language (Python → Sphinx/MkDocs, JavaScript → Docusaurus, Go → Hugo)
   - Considers project complexity and needs

### Manual specification

If auto-detection fails or you want to override:

```json
{
  "tool": "docmgr_init",
  "arguments": {
    "platform": "mkdocs"  // Manually specify
  }
}
```

---

## Platform-specific configuration

### MkDocs

**Common patterns**:
```yaml
# .doc-manager.yml
platform: mkdocs
docs_path: docs
sources:
  - "src/**/*.py"
  - "lib/**/*.py"
```

**Material theme integration**:
- Doc-manager respects Material's directory structure
- Validation checks work with custom Material components
- Quality assessment considers Material-specific features

### Sphinx

**Common patterns**:
```yaml
# .doc-manager.yml
platform: sphinx
docs_path: docs
sources:
  - "src/**/*.py"
  - "lib/**/*.py"
```

**reStructuredText vs Markdown**:
- Doc-manager primarily validates `.md` files
- For `.rst` files, use Sphinx's built-in validation
- MyST parser allows Markdown in Sphinx projects

### Hugo

**Common patterns**:
```yaml
# .doc-manager.yml
platform: hugo
docs_path: content
sources:
  - "cmd/**/*.go"
  - "pkg/**/*.go"
exclude:
  - "content/*/index.md"  # Exclude auto-generated indexes
```

**Content organization**:
- Sections as directories
- `_index.md` for section landing pages
- Frontmatter validation included

### Docusaurus

**Common patterns**:
```yaml
# .doc-manager.yml
platform: docusaurus
docs_path: docs
sources:
  - "src/**/*.{js,ts,jsx,tsx}"
  - "packages/**/*.{js,ts}"
```

**Versioning considerations**:
- Use `docs/` for current version
- Exclude `versioned_docs/` from source tracking (add to `exclude`)
- Validate each version separately if needed

---

## Migrating between platforms

### MkDocs to Sphinx

1. **Run migration with platform change**:

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "source_path": "docs",
    "target_path": "sphinx-docs",
    "target_platform": "sphinx",
    "preserve_history": true,
    "rewrite_links": true
  }
}
```

2. **Convert Markdown to reStructuredText** (optional):
   - Use `pandoc` or `m2r2` for conversion
   - Or use MyST parser to keep Markdown

3. **Create `conf.py`**:

```python
# docs/conf.py
project = 'My Project'
extensions = ['myst_parser']  # For Markdown support
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
```

4. **Update doc-manager config**:

```yaml
platform: sphinx
docs_path: sphinx-docs
```

### Hugo to Docusaurus

1. **Migrate content**:

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "source_path": "content",
    "target_path": "docs",
    "target_platform": "docusaurus",
    "rewrite_links": true
  }
}
```

2. **Convert frontmatter** (Hugo TOML → Docusaurus YAML):

```bash
# Manually or with script
for file in docs/**/*.md; do
  # Convert TOML frontmatter to YAML
done
```

3. **Initialize Docusaurus**:

```bash
npx create-docusaurus@latest
```

4. **Update doc-manager config**:

```yaml
platform: docusaurus
docs_path: docs
```

### Any platform to custom

If migrating to custom/unknown platform:

```json
{
  "tool": "docmgr_migrate",
  "arguments": {
    "source_path": "old-docs",
    "target_path": "docs",
    "target_platform": "unknown",
    "preserve_history": true
  }
}
```

---

## Platform-specific best practices

### MkDocs

- **Use Material theme** for better UI and search
- **Enable extensions** in `mkdocs.yml` (tables, code highlighting)
- **Structure**: Keep flat for small projects, nested for large ones
- **Navigation**: Use `nav` in `mkdocs.yml` for explicit ordering

### Sphinx

- **Use autodoc** for API documentation from docstrings
- **Enable MyST** for Markdown support
- **Intersphinx**: Link to other Sphinx documentation
- **Custom roles**: Define project-specific roles for consistency

### Hugo

- **Use archetypes** for consistent frontmatter
- **Page bundles**: Group related content and assets
- **Taxonomies**: Use tags and categories for organization
- **Shortcodes**: Create reusable content snippets

### Docusaurus

- **Use sidebars.js** for navigation structure
- **Version docs** early if planning multiple versions
- **MDX components**: Create reusable React components
- **i18n**: Plan internationalization from the start

---

## Platform feature comparison

| Feature | MkDocs | Sphinx | Hugo | Docusaurus | VitePress |
|---------|--------|--------|------|------------|-----------|
| **Primary language** | Python | Python | Go | JavaScript | JavaScript |
| **Markup** | Markdown | RST/MD | Markdown | Markdown/MDX | Markdown |
| **API autodoc** | Limited | Excellent | No | Limited | No |
| **Build speed** | Medium | Slow | Fast | Medium | Fast |
| **Versioning** | Plugin | Yes | Manual | Built-in | Manual |
| **i18n** | Plugin | Yes | Yes | Built-in | Yes |
| **Search** | Plugin | Yes | Limited | Yes | Yes |
| **Themes** | Good | Excellent | Excellent | Limited | Limited |

---

## Choosing a platform

### For Python projects

- **Sphinx**: If you need extensive API documentation from docstrings
- **MkDocs**: If you want simple setup and Markdown-first approach

### For JavaScript/TypeScript projects

- **Docusaurus**: If you need versioning and i18n
- **VitePress**: If you use Vue and want modern tooling

### For Go projects

- **Hugo**: Fast builds, native Go integration

### For multi-language projects

- **Docusaurus** or **Hugo**: Strong i18n support

### For simple projects

- **MkDocs** or **Jekyll**: Minimal configuration needed

---

## See also

- [docmgr_detect_platform reference](../reference/tools/docmgr_detect_platform.md)
- [docmgr_migrate reference](../reference/tools/docmgr_migrate.md)
- [Workflows guide](workflows.md)
- [Configuration reference](../reference/file-formats.md)
