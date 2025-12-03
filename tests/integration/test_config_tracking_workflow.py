"""Integration tests for config tracking workflow (T020)."""

import json
import pytest
import tempfile
from pathlib import Path

from doc_manager_mcp.indexing.analysis.semantic_diff import (
    compare_config_fields,
    load_symbol_baseline,
    save_symbol_baseline,
)
from doc_manager_mcp.indexing.analysis.tree_sitter import SymbolIndexer


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        # Create .doc-manager directory
        (project_path / ".doc-manager" / "memory").mkdir(parents=True)
        yield project_path


class TestEndToEndConfigTracking:
    """Test end-to-end config field tracking workflow."""

    def test_detect_config_changes_workflow(self, temp_project):
        """Test: code change -> detect -> action items."""
        # Step 1: Create initial config file
        config_v1 = '''
from pydantic import BaseModel

class AppConfig(BaseModel):
    host: str = "localhost"
    port: int = 8080
'''
        (temp_project / "config.py").write_text(config_v1)

        # Step 2: Index and save baseline
        indexer = SymbolIndexer()
        indexer.index_project(temp_project, file_patterns=["config.py"])

        baseline_path = temp_project / ".doc-manager" / "memory" / "symbol-baseline.json"
        save_symbol_baseline(baseline_path, indexer.index)

        # Step 3: Modify config (add field)
        config_v2 = '''
from pydantic import BaseModel

class AppConfig(BaseModel):
    host: str = "localhost"
    port: int = 8080
    debug: bool = False
'''
        (temp_project / "config.py").write_text(config_v2)

        # Step 4: Load old baseline and index new state
        old_symbols = load_symbol_baseline(baseline_path)
        assert old_symbols is not None

        new_indexer = SymbolIndexer()
        new_indexer.index_project(temp_project, file_patterns=["config.py"])

        # Step 5: Compare config fields
        config_changes = compare_config_fields(old_symbols, new_indexer.index)

        # Should detect added 'debug' field
        assert len(config_changes) >= 1
        added_fields = [c for c in config_changes if c.change_type == "added"]
        assert any(c.field_name == "debug" for c in added_fields)


class TestBaselineUpdateWithConfigFields:
    """Test that baselines include config fields."""

    def test_baseline_includes_config_fields(self, temp_project):
        """Test that symbol baseline includes config_fields."""
        # Create a config file
        config_code = '''
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
'''
        (temp_project / "config.py").write_text(config_code)

        # Index project
        indexer = SymbolIndexer()
        indexer.index_project(temp_project, file_patterns=["config.py"])

        # Save baseline
        baseline_path = temp_project / ".doc-manager" / "memory" / "symbol-baseline.json"
        save_symbol_baseline(baseline_path, indexer.index)

        # Verify baseline has config_fields
        with open(baseline_path) as f:
            baseline_data = json.load(f)

        # Check version
        assert baseline_data["version"] == "1.1"

        # Find the symbol with config fields
        found_config_fields = False
        for file_symbols in baseline_data["symbols"].values():
            for sym in file_symbols:
                if sym.get("config_fields"):
                    found_config_fields = True
                    field_names = [f["name"] for f in sym["config_fields"]]
                    assert "host" in field_names
                    assert "port" in field_names

        assert found_config_fields, "No config_fields found in baseline"

    def test_baseline_load_preserves_config_fields(self, temp_project):
        """Test that loading baseline preserves config_fields."""
        # Create and save baseline
        config_code = '''
from pydantic import BaseModel

class Config(BaseModel):
    setting: str = "value"
'''
        (temp_project / "config.py").write_text(config_code)

        indexer = SymbolIndexer()
        indexer.index_project(temp_project, file_patterns=["config.py"])

        baseline_path = temp_project / ".doc-manager" / "memory" / "symbol-baseline.json"
        save_symbol_baseline(baseline_path, indexer.index)

        # Load baseline
        loaded_symbols = load_symbol_baseline(baseline_path)
        assert loaded_symbols is not None

        # Verify config_fields are preserved
        for file_symbols in loaded_symbols.values():
            for sym in file_symbols:
                if sym.name == "Config":
                    assert sym.config_fields is not None
                    field_names = [f.name for f in sym.config_fields]
                    assert "setting" in field_names


class TestMultiLanguageProject:
    """Test config tracking across multiple languages."""

    def test_python_and_typescript_configs(self, temp_project):
        """Test tracking configs in Python and TypeScript."""
        # Create Python config
        py_config = '''
from dataclasses import dataclass

@dataclass
class PyConfig:
    host: str = "localhost"
'''
        (temp_project / "config.py").write_text(py_config)

        # Create TypeScript config
        ts_config = '''
interface TsConfig {
  host: string;
  port?: number;
}
'''
        (temp_project / "config.ts").write_text(ts_config)

        # Index both
        indexer = SymbolIndexer()
        indexer.index_project(temp_project, file_patterns=["config.py", "config.ts"])

        # Both should have config fields
        py_symbols = indexer.lookup("PyConfig")
        ts_symbols = indexer.lookup("TsConfig")

        assert len(py_symbols) >= 1
        assert len(ts_symbols) >= 1

        # Python config should have host field
        if py_symbols[0].config_fields:
            py_fields = {f.name for f in py_symbols[0].config_fields}
            assert "host" in py_fields

        # TypeScript config should have host and port fields
        if ts_symbols[0].config_fields:
            ts_fields = {f.name for f in ts_symbols[0].config_fields}
            assert "host" in ts_fields
