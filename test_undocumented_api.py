#!/usr/bin/env python3
"""Test undocumented API detection functionality."""

from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from doc_manager_mcp.tools.quality_helpers import detect_undocumented_apis

def test_detect_undocumented_apis():
    """Test undocumented API detection on pass-cli project."""

    # Use pass-cli as test project
    project_path = Path(r"R:\Test-Projects\pass-cli")
    docs_path = project_path / "docs"

    if not project_path.exists():
        print(f"Project path does not exist: {project_path}")
        return

    if not docs_path.exists():
        print(f"Docs path does not exist: {docs_path}")
        return

    print(f"Testing undocumented API detection...")
    print(f"Project: {project_path}")
    print(f"Docs: {docs_path}")
    print("-" * 60)

    # Detect undocumented APIs
    undocumented = detect_undocumented_apis(project_path, docs_path)

    print(f"\nTotal undocumented APIs: {len(undocumented)}")
    print("-" * 60)

    if undocumented:
        # Group by type
        by_type = {}
        for symbol in undocumented:
            symbol_type = symbol['type']
            if symbol_type not in by_type:
                by_type[symbol_type] = []
            by_type[symbol_type].append(symbol)

        # Show breakdown by type
        print("\nBreakdown by type:")
        for symbol_type, symbols in sorted(by_type.items()):
            print(f"  {symbol_type}: {len(symbols)}")

        # Show first 10 undocumented symbols
        print(f"\nFirst 10 undocumented symbols:")
        for i, symbol in enumerate(undocumented[:10], 1):
            print(f"  {i}. {symbol['name']} ({symbol['type']}) - {symbol['file']}:{symbol['line']}")
    else:
        print("\nAll public APIs are documented!")

if __name__ == "__main__":
    test_detect_undocumented_apis()
