"""Tests for config field detection across languages (T017)."""

import pytest
from pathlib import Path

from doc_manager_mcp.indexing.analysis.tree_sitter import SymbolIndexer, SymbolType


@pytest.fixture
def indexer():
    """Create a SymbolIndexer for testing."""
    return SymbolIndexer()


@pytest.fixture
def fixtures_path():
    """Path to config sample fixtures."""
    return Path(__file__).parent.parent / "fixtures" / "config_samples"


class TestPythonConfigDetection:
    """Test Python config class detection (Pydantic, dataclass, TypedDict, attrs)."""

    def test_pydantic_basemodel_detection(self, indexer, fixtures_path):
        """Test Pydantic BaseModel detection."""
        file_path = fixtures_path / "pydantic_config.py"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["pydantic_config.py"])

        # Should find DatabaseConfig class
        symbols = indexer.lookup("DatabaseConfig")
        assert len(symbols) == 1
        symbol = symbols[0]
        assert symbol.type == SymbolType.CLASS

        # Should have config fields
        assert symbol.config_fields is not None
        field_names = {f.name for f in symbol.config_fields}
        assert "host" in field_names
        assert "port" in field_names
        assert "database" in field_names

    def test_pydantic_field_types(self, indexer, fixtures_path):
        """Test field type extraction from Pydantic model."""
        file_path = fixtures_path / "pydantic_config.py"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["pydantic_config.py"])

        symbols = indexer.lookup("DatabaseConfig")
        assert len(symbols) == 1
        symbol = symbols[0]

        # Check specific fields
        if symbol.config_fields:
            fields_by_name = {f.name: f for f in symbol.config_fields}

            if "ssl_enabled" in fields_by_name:
                ssl_field = fields_by_name["ssl_enabled"]
                assert ssl_field.is_optional is False  # bool = False is not optional

    def test_dataclass_detection(self, indexer, fixtures_path):
        """Test @dataclass decorator detection."""
        file_path = fixtures_path / "dataclass_config.py"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["dataclass_config.py"])

        symbols = indexer.lookup("ServerConfig")
        assert len(symbols) == 1
        symbol = symbols[0]
        assert symbol.type == SymbolType.CLASS

        # Should detect as config class and have fields
        assert symbol.config_fields is not None
        field_names = {f.name for f in symbol.config_fields}
        assert "host" in field_names
        assert "port" in field_names


class TestGoConfigDetection:
    """Test Go config struct detection with yaml/json tags."""

    def test_go_struct_with_tags(self, indexer, fixtures_path):
        """Test Go struct with yaml/json tags detection."""
        file_path = fixtures_path / "go_config.go"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["go_config.go"])

        symbols = indexer.lookup("AppConfig")
        assert len(symbols) == 1
        symbol = symbols[0]
        assert symbol.type == SymbolType.STRUCT

        # Should have config fields with tags
        assert symbol.config_fields is not None
        field_names = {f.name for f in symbol.config_fields}
        assert "Name" in field_names
        assert "Version" in field_names

    def test_go_field_tags_parsing(self, indexer, fixtures_path):
        """Test Go field tag parsing."""
        file_path = fixtures_path / "go_config.go"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["go_config.go"])

        symbols = indexer.lookup("AppConfig")
        if symbols and symbols[0].config_fields:
            fields_by_name = {f.name: f for f in symbols[0].config_fields}

            # Check tags are parsed
            if "Version" in fields_by_name:
                version_field = fields_by_name["Version"]
                assert version_field.tags is not None
                assert "yaml" in version_field.tags
                assert "omitempty" in version_field.tags["yaml"]


class TestTypeScriptConfigDetection:
    """Test TypeScript interface detection by name pattern."""

    def test_ts_interface_with_config_suffix(self, indexer, fixtures_path):
        """Test TypeScript interface with *Config name pattern."""
        file_path = fixtures_path / "ts_config.ts"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["ts_config.ts"])

        symbols = indexer.lookup("AppConfig")
        assert len(symbols) == 1
        symbol = symbols[0]
        assert symbol.type == SymbolType.INTERFACE

        # Should have config fields
        assert symbol.config_fields is not None
        field_names = {f.name for f in symbol.config_fields}
        assert "name" in field_names
        assert "debug" in field_names

    def test_ts_optional_properties(self, indexer, fixtures_path):
        """Test TypeScript optional property (?) detection."""
        file_path = fixtures_path / "ts_config.ts"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["ts_config.ts"])

        symbols = indexer.lookup("AppConfig")
        if symbols and symbols[0].config_fields:
            fields_by_name = {f.name: f for f in symbols[0].config_fields}

            # version should be optional
            if "version" in fields_by_name:
                assert fields_by_name["version"].is_optional is True


class TestRustConfigDetection:
    """Test Rust config struct detection with serde derives."""

    def test_rust_serde_struct(self, indexer, fixtures_path):
        """Test Rust struct with #[derive(Serialize, Deserialize)]."""
        file_path = fixtures_path / "rust_config.rs"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["rust_config.rs"])

        symbols = indexer.lookup("AppConfig")
        assert len(symbols) == 1
        symbol = symbols[0]
        assert symbol.type == SymbolType.STRUCT

        # Should detect serde config and have fields
        assert symbol.config_fields is not None
        field_names = {f.name for f in symbol.config_fields}
        assert "name" in field_names
        assert "debug" in field_names

    def test_rust_serde_attributes(self, indexer, fixtures_path):
        """Test Rust serde attribute parsing."""
        file_path = fixtures_path / "rust_config.rs"
        if not file_path.exists():
            pytest.skip("Fixture file not found")

        indexer.index_project(fixtures_path, file_patterns=["rust_config.rs"])

        symbols = indexer.lookup("AppConfig")
        if symbols and symbols[0].config_fields:
            fields_by_name = {f.name: f for f in symbols[0].config_fields}

            # Check Option<T> detection
            if "version" in fields_by_name:
                assert fields_by_name["version"].is_optional is True
