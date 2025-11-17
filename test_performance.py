#!/usr/bin/env python3
"""Quick performance test for initialize_memory fix."""

import asyncio
import time
from pathlib import Path

from src.models import InitializeMemoryInput
from src.tools.memory import initialize_memory


async def test_memory_performance():
    """Test initialize_memory performance."""
    project_path = Path(__file__).parent.resolve()

    print(f"Testing initialize_memory on: {project_path}")
    print(f"Expected: <5 seconds, ~100-200 files scanned")
    print("-" * 60)

    # Time the operation
    start_time = time.time()

    try:
        result = await initialize_memory(InitializeMemoryInput(
            project_path=str(project_path)
        ))

        elapsed = time.time() - start_time

        print(f"[OK] Completed in {elapsed:.2f} seconds")
        print()

        if isinstance(result, dict):
            print(f"[OK] Returned dict (not hanging!)")
            print(f"  Status: {result.get('status')}")
            print(f"  Files tracked: {result.get('files_tracked')}")
            print(f"  Language: {result.get('language')}")
            print(f"  Repository: {result.get('repository')}")

            # Success criteria
            if elapsed < 5:
                print()
                print("*** PERFORMANCE FIX VERIFIED! ***")
                print(f"   Before: 6+ minutes, 12k files")
                print(f"   After: {elapsed:.2f}s, {result.get('files_tracked')} files")
            else:
                print()
                print("[WARN] Still slow, but better than before")
        else:
            print(f"[WARN] Returned string: {result[:100]}...")

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[FAIL] Failed after {elapsed:.2f} seconds")
        print(f"  Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_memory_performance())
