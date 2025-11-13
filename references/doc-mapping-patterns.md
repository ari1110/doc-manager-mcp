# Documentation Mapping Patterns

This reference provides common patterns for mapping code changes to documentation updates. Use these patterns in the `docmgr_map_changes` tool to identify which documentation files need updates when code changes.

## Pattern Categories

### 1. CLI Command Changes

**Pattern**: Changes to `cmd/*.go`, `cmd/**/*.go` files

**Affected Documentation**:
- `docs/reference/command-reference.md` - Update command syntax, flags, examples
- `docs/guides/basic-workflows.md` - Update workflow examples using the command
- `README.md` - Update quick start if it's a primary command

**Detection Logic**:
```python
if file_path.startswith("cmd/") and file_path.endswith(".go"):
    affected_docs.append({
        "file": "docs/reference/command-reference.md",
        "reason": f"CLI command implementation changed: {file_path}",
        "priority": "high"
    })
```

**Example Mapping**:
- `cmd/add.go` changed → Update `docs/reference/command-reference.md` (add command section)
- `cmd/tui/model.go` changed → Update `docs/guides/tui-guide.md`

---

### 2. API/Library Changes

**Pattern**: Changes to `internal/**/*.go`, `pkg/**/*.go`, `lib/**/*.py` files

**Affected Documentation**:
- `docs/reference/api.md` - Update API reference
- `docs/development/contributing.md` - Update if internal APIs changed
- `docs/reference/architecture.md` - Update if architecture impacted

**Detection Logic**:
```python
if file_path.startswith("internal/") or file_path.startswith("pkg/"):
    # Check if it's a public API (exported functions/types)
    if is_public_api(file_path):
        affected_docs.append({
            "file": "docs/reference/api.md",
            "reason": f"Public API changed: {file_path}",
            "priority": "high"
        })
```

**Example Mapping**:
- `internal/vault/operations.go` changed → Update `docs/reference/security-architecture.md`
- `pkg/crypto/encrypt.go` changed → Update `docs/reference/api.md` (crypto section)

---

### 3. Configuration Changes

**Pattern**: Changes to config files, schemas, or config-handling code

**Affected Documentation**:
- `docs/reference/configuration.md` - Update config options
- `docs/getting-started/installation.md` - Update if default config changed
- `README.md` - Update if critical config option added

**Detection Logic**:
```python
config_files = ["config.yaml", "config.toml", ".env.example", "viper config", "cobra config"]
if any(pattern in file_path for pattern in config_files):
    affected_docs.append({
        "file": "docs/reference/configuration.md",
        "reason": f"Configuration schema changed: {file_path}",
        "priority": "high"
    })
```

**Example Mapping**:
- `config/defaults.go` changed → Update `docs/reference/configuration.md`
- `.env.example` changed → Update `docs/getting-started/installation.md`

---

### 4. Dependency Changes

**Pattern**: Changes to `go.mod`, `package.json`, `requirements.txt`, etc.

**Affected Documentation**:
- `docs/getting-started/installation.md` - Update dependencies
- `docs/development/contributing.md` - Update dev setup
- `README.md` - Update requirements section

**Detection Logic**:
```python
dependency_files = ["go.mod", "package.json", "requirements.txt", "Cargo.toml", "pom.xml"]
if file_path in dependency_files:
    affected_docs.append({
        "file": "docs/getting-started/installation.md",
        "reason": f"Dependencies changed: {file_path}",
        "priority": "medium"
    })
```

**Example Mapping**:
- `go.mod` changed → Update `docs/getting-started/installation.md` (prerequisites)
- `package.json` changed → Update `README.md` (dependencies section)

---

### 5. Test Changes

**Pattern**: Changes to `*_test.go`, `test/**/*`, `tests/**/*` files

**Affected Documentation**:
- `docs/development/testing.md` - Update test instructions
- `docs/development/contributing.md` - Update if test patterns changed

**Detection Logic**:
```python
if "_test." in file_path or file_path.startswith("test/") or file_path.startswith("tests/"):
    affected_docs.append({
        "file": "docs/development/testing.md",
        "reason": f"Test patterns changed: {file_path}",
        "priority": "low"
    })
```

**Example Mapping**:
- `test/integration_test.go` changed → Update `docs/development/testing.md`

---

### 6. Documentation Platform Changes

**Pattern**: Changes to Hugo config, Docusaurus config, MkDocs config, etc.

**Affected Documentation**:
- `docs/development/documentation-lifecycle.md` - Update doc build process
- `README.md` - Update if doc site URL changed

**Detection Logic**:
```python
doc_platform_files = ["hugo.yaml", "hugo.toml", "docusaurus.config.js", "mkdocs.yml"]
if any(pattern in file_path for pattern in doc_platform_files):
    affected_docs.append({
        "file": "docs/development/documentation-lifecycle.md",
        "reason": f"Documentation platform configuration changed: {file_path}",
        "priority": "medium"
    })
```

**Example Mapping**:
- `docsite/hugo.yaml` changed → Update `docs/development/documentation-lifecycle.md`

---

### 7. Security/Auth Changes

**Pattern**: Changes to auth, security, encryption modules

**Affected Documentation**:
- `docs/reference/security-architecture.md` - Update security details
- `docs/guides/keychain-setup.md` - Update if auth flow changed
- `docs/operations/security-operations.md` - Update security procedures

**Detection Logic**:
```python
security_keywords = ["auth", "security", "crypto", "keychain", "vault", "encrypt"]
if any(keyword in file_path.lower() for keyword in security_keywords):
    affected_docs.append({
        "file": "docs/reference/security-architecture.md",
        "reason": f"Security implementation changed: {file_path}",
        "priority": "critical"
    })
```

**Example Mapping**:
- `internal/security/audit.go` changed → Update `docs/reference/security-architecture.md`
- `internal/keychain/manager.go` changed → Update `docs/guides/keychain-setup.md`

---

### 8. Build/CI Changes

**Pattern**: Changes to Makefiles, GitHub Actions, build scripts

**Affected Documentation**:
- `docs/development/ci-cd.md` - Update CI/CD pipeline docs
- `docs/development/release.md` - Update release process
- `README.md` - Update if build commands changed

**Detection Logic**:
```python
build_files = ["Makefile", ".github/workflows/", "scripts/build", ".gitlab-ci.yml"]
if any(pattern in file_path for pattern in build_files):
    affected_docs.append({
        "file": "docs/development/ci-cd.md",
        "reason": f"Build/CI configuration changed: {file_path}",
        "priority": "medium"
    })
```

**Example Mapping**:
- `.github/workflows/test.yml` changed → Update `docs/development/ci-cd.md`
- `Makefile` changed → Update `README.md` (build instructions)

---

## Priority Levels

**Critical**: Security changes, breaking API changes
- Immediate documentation update required
- Block releases until docs updated

**High**: CLI commands, public APIs, configuration
- Update before next release
- Affects user-facing functionality

**Medium**: Dependencies, build process, documentation platform
- Update in same sprint/iteration
- Affects developers or doc maintenance

**Low**: Tests, internal refactoring, non-public code
- Update when convenient
- Optional documentation updates

---

## Usage in `docmgr_map_changes`

```python
async def map_changes(params: MapChangesInput) -> str:
    changed_files = await _get_changed_files(project_path, since_commit)
    affected_docs = []

    for file_path in changed_files:
        # Apply all patterns
        if file_path.startswith("cmd/"):
            affected_docs.extend(_map_cli_changes(file_path))
        elif file_path.startswith("internal/") or file_path.startswith("pkg/"):
            affected_docs.extend(_map_api_changes(file_path))
        # ... apply other patterns

    # Deduplicate and prioritize
    affected_docs = _deduplicate_and_prioritize(affected_docs)

    return _format_mapping_report(affected_docs, params.response_format)
```

---

## Project-Specific Customization

Each project may have unique mapping patterns. To customize:

1. Edit `.doc-manager.yml` to add custom mappings:
```yaml
custom_mappings:
  - pattern: "cmd/tui/*.go"
    docs: ["docs/guides/tui-guide.md"]
    priority: "high"
  - pattern: "internal/vault/*.go"
    docs: ["docs/reference/security-architecture.md", "docs/guides/backup-restore.md"]
    priority: "high"
```

2. The `docmgr_map_changes` tool will load and apply custom mappings alongside default patterns.

---

## Common Pitfalls

1. **Over-mapping**: Don't map every code change to docs. Internal refactoring rarely needs doc updates.
2. **Under-mapping**: Don't forget edge cases like schema changes in comments/annotations.
3. **Ignoring context**: Same file can map to different docs depending on what changed (e.g., internal vs exported functions).
4. **Missing cross-references**: Update all docs that reference the changed component, not just the primary doc.

---

**Last Updated**: 2025-01-13
