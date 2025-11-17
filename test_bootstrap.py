#!/usr/bin/env python3
"""Test bootstrap workflow with timing."""

import asyncio
import shutil
import time
from pathlib import Path

from src.models import BootstrapInput
from src.tools.workflows import bootstrap

async def test_bootstrap():
    """Test full bootstrap workflow."""
    project_path = Path(__file__).parent.resolve()

    # Temporarily move existing docs
    docs_path = project_path / "docs"
    docs_backup = project_path / "docs.backup"
    moved_docs = False

    if docs_path.exists():
        print(f"Temporarily moving {docs_path} to {docs_backup}")
        if docs_backup.exists():
            shutil.rmtree(docs_backup)
        shutil.move(str(docs_path), str(docs_backup))
        moved_docs = True

    # Clean up existing .doc-manager
    doc_manager_path = project_path / ".doc-manager"
    if doc_manager_path.exists():
        print(f"Cleaning up existing {doc_manager_path}")
        shutil.rmtree(doc_manager_path)

    print(f"Testing bootstrap on: {project_path}")
    print(f"Expected: <10 seconds for full workflow")
    print("-" * 60)

    # Time the operation
    start_time = time.time()

    try:
        result = await bootstrap(BootstrapInput(
            project_path=str(project_path),
            platform="mkdocs",
            docs_path="docs"
        ))

        elapsed = time.time() - start_time

        print(f"\n[OK] Completed in {elapsed:.2f} seconds")
        print()

        if isinstance(result, dict):
            print(f"[OK] Returned dict structure")
            print(f"  Status: {result.get('status')}")
            print(f"  Platform: {result.get('platform')}")
            print(f"  Docs path: {result.get('docs_path')}")
            print(f"  Files created: {result.get('files_created')}")
            print(f"  Quality score: {result.get('quality_score')}")

            # Show the report
            if 'report' in result:
                print()
                print("=" * 60)
                print("BOOTSTRAP REPORT")
                print("=" * 60)
                print(result['report'])
                print("=" * 60)

            # Verify files exist
            print()
            print("Verifying files...")
            config_file = project_path / ".doc-manager.yml"
            memory_dir = project_path / ".doc-manager" / "memory"

            if config_file.exists():
                print(f"  [OK] {config_file.name}")
                # Read and show config
                import yaml
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                    print(f"       Platform: {config.get('platform')}")
                    print(f"       Exclude patterns: {len(config.get('exclude', []))}")
            else:
                print(f"  [FAIL] {config_file.name} not found!")

            if memory_dir.exists():
                print(f"  [OK] {memory_dir.relative_to(project_path)}/")
                for file in memory_dir.iterdir():
                    print(f"       - {file.name} ({file.stat().st_size} bytes)")
            else:
                print(f"  [FAIL] {memory_dir} not found!")

            # Success criteria
            if elapsed < 10:
                print()
                print("*** BOOTSTRAP WORKFLOW VERIFIED! ***")
                print(f"   Time: {elapsed:.2f}s (target: <10s)")
                print(f"   Files: {result.get('files_created')} created")
                print(f"   Quality: {result.get('quality_score')}")
                return True
        else:
            print(f"[FAIL] Expected dict, got: {type(result)}")
            print(f"Result: {result}")
            return False

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[FAIL] Exception after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore docs directory
        if moved_docs and docs_backup.exists():
            print()
            print(f"Restoring {docs_backup} to {docs_path}")
            if docs_path.exists():
                shutil.rmtree(docs_path)
            shutil.move(str(docs_backup), str(docs_path))

if __name__ == "__main__":
    success = asyncio.run(test_bootstrap())
    exit(0 if success else 1)
