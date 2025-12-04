# Changelog

All notable changes to Documentation Manager are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.1.1]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.1.1
[1.1.0]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.1.0
[1.0.3]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.3
[1.0.2]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.2
[1.0.1]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.1
[1.0.0]: https://github.com/ari1110/doc-manager-mcp/releases/tag/v1.0.0
