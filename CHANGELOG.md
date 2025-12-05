# Changelog

All notable changes to Documentation Manager are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.3] - 2025-12-04

### Fixed

- `dependencies_tracked` count in `docmgr_update_baseline` output now correctly reports `total_references` instead of always showing 0

## [1.2.2] - 2025-12-04

### Added

- **Active schema validation** - Baseline files are now validated against Pydantic schemas on load
- **Graceful validation errors** - Invalid baselines return `None` with warning instead of crashing
- **Version compatibility checking** - Warns when baseline version is older than required

### Changed

- `load_repo_baseline()` now validates by default (`validate=True`, `check_version=True`)
- `load_dependencies()` now validates by default (`validate=True`)
- All 11 baseline load sites now use schema validation
- Invalid JSON or schema failures log warnings to stderr and return `None`

### Fixed

- Schema validation was defined but never activated (all callers passed `validate=False`)

## [1.2.1] - 2025-12-04

### Added

- **Complete data utilization** - All stored fields in baseline files now have concrete consumers
- **`load_repo_baseline()` function** - Load repo-baseline.json with typed access and version validation
- **Change percentage reporting** - `docmgr_detect_changes` shows "X of Y files changed (Z%)"
- **Project context in reports** - Quality and sync reports include repo_name and description
- **Language-aware validation** - Primary language syntax errors elevated to error severity
- **Early exit for missing docs** - Tools return early with clear message when `docs_exist=false`
- **Stale reference validation** - `docmgr_validate_docs` warns about unmatched code references
- **External asset validation** - Opt-in `check_external_assets` flag to verify HTTP URLs
- **Docstring coverage metric** - Quality assessment reports "X% of public symbols have docstrings"
- **Parent change detection** - `compare_symbols` detects when symbols move between classes
- **Doc change detection** - Detect and track docstring modifications as semantic changes
- **Precise column locations** - Action items include column number for precise source locations

### Changed

- `SemanticChange` now includes `column`, `old_parent`, `new_parent`, `old_doc`, `new_doc` fields
- Action generator includes parent and doc change info in source_change references
- `ValidateDocsInput` adds `check_stale_references` (default: true) and `check_external_assets` (default: false)

## [1.2.0] - 2025-12-04

### Added

- **Staleness detection** - Warn when baseline files are outdated (7/30/90 day thresholds)
- **Branch mismatch warnings** - Detect when current git branch differs from baseline
- **`load_dependencies()` function** - Load dependencies.json with optional schema validation
- **`get_reference_to_doc()` helper** - Derive reference→doc mappings on-demand from `all_references`
- **Schema validation** - Pydantic schemas for all baseline files with validation helpers
- **Config schema alignment** - Added `project_name` and `ConfigMetadata` to match actual config files

### Changed

- **Precise affected doc detection** - Uses `code_to_doc` from dependencies.json instead of hardcoded fallbacks
- **Action generation** - ActionGenerator now accepts `code_to_doc` and `doc_mappings` for precise inference
- **CLI tools detection** - Dynamically detects project name instead of hardcoded list
- **Baseline staleness** - `docmgr_detect_changes` now includes staleness warnings in output

### Deprecated

- `docs_path` in repo-baseline.json - Use `config.docs_path` as authoritative source
- `reference_to_doc` in dependencies.json - Use `get_reference_to_doc()` helper instead

### Removed

- Hardcoded category→doc fallback mappings - Explicit configuration or dependencies.json required
- `reference_to_doc` from dependencies.json output - Reduces file size ~40%

## [1.1.1] - 2025-12-03

### Fixed

- Symbol baseline now created during `docmgr_init` (was only created by `docmgr_update_baseline`)
- Extracted `create_symbol_baseline()` as shared function for consistency

## [1.1.0] - 2025-12-03

### Added

- **Config field tracking** - Detect changes to configuration fields in Pydantic models, dataclasses, attrs classes, Go structs, TypeScript interfaces, and Rust structs with serde
- **Actionable outputs** - Get prioritized action items when config fields change, with clear descriptions and severity levels
- **Rust symbol extraction** - Full support for Rust codebases including functions, structs, enums, traits, and impl blocks
- **Context-aware skill** - New doc-management skill with improved knowledge source hierarchy

### Changed

- Semantic analysis now includes config field changes in output
- Baseline files track config field signatures for change detection

## [1.0.3] - 2025-11-28

### Added

- **Configurable API coverage** - Control which symbols appear in documentation metrics
- **Multi-language presets** - Built-in presets for Python (pydantic), Go, TypeScript, Rust
- **Symbol filtering strategies** - Choose `all_only`, `all_then_underscore`, or `underscore_only`
- **Claude Code plugin** - Interactive documentation workflow with specialized agents

### Changed

- Improved public symbol detection using industry-standard conventions
- Standardized heading case to sentence_case across documentation
- Plugin renamed from `doc-manager-mcp` to `doc-manager` for consistency

### Fixed

- Session start hook now uses Python for cross-platform compatibility
- Corrected MCP tool naming in plugin configuration

## [1.0.2] - 2025-11-22

### Added

- PyPI badges and MIT license display
- Python version classifiers in package metadata

### Changed

- Documentation reframed to focus on MCP server usage
- README.md now symlinks to docs/index.md for consistency

### Fixed

- Corrected PyPI badge URLs
- Resolved documentation validation errors
- Updated installation instructions with correct repository and CLI names

## [1.0.1] - 2025-11-21

### Changed

- Version bump for initial PyPI release

## [1.0.0] - 2025-11-21

### Added

- Initial release of Documentation Manager MCP server
- 8 documentation lifecycle management tools
- TreeSitter-based symbol extraction for Python, Go, TypeScript, Rust
- Quality assessment against 7 criteria
- Link and asset validation
- Platform detection (MkDocs, Sphinx, Hugo, Docusaurus)
- Checksum and semantic change detection
- Baseline management for tracking documentation state

[1.2.3]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.2.3
[1.2.2]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.2.2
[1.2.1]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.2.1
[1.2.0]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.2.0
[1.1.1]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.1.1
[1.1.0]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.1.0
[1.0.3]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.3
[1.0.2]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.2
[1.0.1]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.1
[1.0.0]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.0
