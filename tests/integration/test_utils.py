
import pytest
from pathlib import Path
import time
from threading import Thread

from src.utils import file_lock


class TestFileLocking:
    """Integration tests for file locking behavior (T070 - US6)."""

    def test_file_lock_prevents_concurrent_writes(self, tmp_path):
        """Test that file locking prevents concurrent writes."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        write_order = []

        def write_with_lock(content, id):
            with file_lock(test_file):
                write_order.append(f"start-{id}")
                time.sleep(0.1)  # Simulate write operation
                test_file.write_text(content)
                write_order.append(f"end-{id}")

        # Start two threads trying to write simultaneously
        thread1 = Thread(target=write_with_lock, args=('{"thread": 1}', 1))
        thread2 = Thread(target=write_with_lock, args=('{"thread": 2}', 2))

        thread1.start()
        time.sleep(0.01)  # Small delay to ensure thread1 gets lock first
        thread2.start()

        thread1.join()
        thread2.join()

        # Verify operations were serialized (one completed before other started)
        assert write_order == ["start-1", "end-1", "start-2", "end-2"] or \
               write_order == ["start-2", "end-2", "start-1", "end-1"]

    def test_file_lock_releases_on_exception(self, tmp_path):
        """Test that file lock is released even if exception occurs."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        # First operation that fails
        try:
            with file_lock(test_file):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Second operation should succeed (lock was released)
        with file_lock(test_file):
            test_file.write_text('{"success": true}')

        assert test_file.read_text() == '{"success": true}'
