"""Quick test script for TreeSitter symbol indexer.

Install dependencies first:
    pip install tree-sitter tree-sitter-language-pack
"""

from pathlib import Path
from src.indexing import SymbolIndexer

# Test on pass-cli project
project_path = Path("R:/Test-Projects/pass-cli")

print("Indexing pass-cli project...")
print()

indexer = SymbolIndexer()
index = indexer.index_project(project_path, file_patterns=["cmd/**/*.go", "internal/**/*.go"])

# Show statistics
stats = indexer.get_index_stats()
print("Index Statistics:")
print(f"  Total symbols: {stats['total_symbols']}")
print(f"  Unique names: {stats['unique_names']}")
print(f"  Files indexed: {stats['files_indexed']}")
print()
print("  By type:")
for symbol_type, count in sorted(stats['by_type'].items()):
    print(f"    {symbol_type}: {count}")
print()

# Test lookups for some known symbols
test_symbols = ["SaveVault", "LoadVault", "Config", "add", "get", "init"]

print("Symbol Lookups:")
for name in test_symbols:
    symbols = indexer.lookup(name)
    if symbols:
        print(f"  {name}:")
        for sym in symbols:
            print(f"    - {sym.type} in {sym.file}:{sym.line}")
    else:
        print(f"  {name}: NOT FOUND")
print()

# Show cmd/ files
cmd_symbols = [s for s in indexer.get_all_symbols() if s.file.startswith("cmd/") and s.file.endswith(".go")]
print(f"CMD Commands ({len(set(s.file for s in cmd_symbols))} files):")
cmd_files = sorted(set(s.file for s in cmd_symbols))
for f in cmd_files[:15]:  # Show first 15
    count = len([s for s in cmd_symbols if s.file == f])
    print(f"  {f} ({count} symbols)")

print()
print("TreeSitter indexer test complete!")
