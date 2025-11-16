
import pytest


class TestReadOnlyHintAccuracy:
    """Test that readOnlyHint annotations match actual tool behavior (T053 - US4)."""

    def test_readonly_hints_match_behavior(self):
        """Test that all 10 tools have correct readOnlyHint values (FR-009).

        readOnlyHint should be:
        - False: If tool writes files, modifies state, or creates resources
        - True: If tool only reads and analyzes without modification
        """
        import server

        # Expected readOnlyHint values based on tool behavior
        expected_hints = {
            # Write operations - should be False
            "docmgr_initialize_config": False,  # Creates .doc-manager.yml
            "docmgr_initialize_memory": False,  # Creates .doc-manager/memory/
            "docmgr_map_changes": False,  # T047: Writes to memory baseline
            "docmgr_track_dependencies": False,  # T048: Writes dependencies.json
            "docmgr_bootstrap": False,  # Creates docs structure
            "docmgr_migrate": False,  # Moves/creates files

            # Read-only operations - should be True
            "docmgr_detect_platform": True,  # Only reads project files
            "docmgr_validate_docs": True,  # Only reads and validates
            "docmgr_assess_quality": True,  # Only reads and analyzes
            "docmgr_sync": True,  # Only reads and recommends (doesn't write)
        }

        # Verify we have all 10 tools
        assert len(expected_hints) == 10, "Should have exactly 10 tools"

        # Get all registered tools from server
        mcp_server = server.mcp
        tools = mcp_server.list_tools()

        # Verify all expected tools exist
        tool_names = {tool.name for tool in tools}
        for expected_tool in expected_hints.keys():
            assert expected_tool in tool_names, f"Tool {expected_tool} not found in server"

        # Verify readOnlyHint for each tool
        for tool in tools:
            if tool.name in expected_hints:
                expected_hint = expected_hints[tool.name]
                actual_hint = tool.annotations.get("readOnlyHint")

                assert actual_hint == expected_hint, (
                    f"Tool '{tool.name}' has incorrect readOnlyHint: "
                    f"expected {expected_hint}, got {actual_hint}"
                )

    def test_destructive_hints_all_false(self):
        """Test that all tools have destructiveHint=False (none are destructive)."""
        import server

        mcp_server = server.mcp
        tools = mcp_server.list_tools()

        for tool in tools:
            if tool.name.startswith("docmgr_"):
                destructive_hint = tool.annotations.get("destructiveHint")
                assert destructive_hint is False, (
                    f"Tool '{tool.name}' should have destructiveHint=False, "
                    f"got {destructive_hint}"
                )

    def test_idempotent_hints_accuracy(self):
        """Test that idempotentHint values are correct."""
        import server

        # Tools that should be idempotent (same input = same output)
        should_be_idempotent = {
            "docmgr_detect_platform",  # Always returns same platform for same project
            "docmgr_validate_docs",  # Always returns same validation results
            "docmgr_assess_quality",  # Always returns same quality score
            "docmgr_map_changes",  # Consistent results for same commit
            "docmgr_track_dependencies",  # Consistent dependency graph
            "docmgr_sync",  # Consistent recommendations
        }

        # Tools that might NOT be idempotent
        might_not_be_idempotent = {
            "docmgr_initialize_config",  # Includes timestamp
            "docmgr_initialize_memory",  # Includes timestamp
            "docmgr_bootstrap",  # Creates new files each time
            "docmgr_migrate",  # File operations
        }

        mcp_server = server.mcp
        tools = mcp_server.list_tools()

        for tool in tools:
            if tool.name in should_be_idempotent:
                idempotent_hint = tool.annotations.get("idempotentHint")
                assert idempotent_hint is True, (
                    f"Tool '{tool.name}' should be idempotent"
                )
            elif tool.name in might_not_be_idempotent:
                idempotent_hint = tool.annotations.get("idempotentHint")
                assert idempotent_hint is False, (
                    f"Tool '{tool.name}' should not be marked as idempotent"
                )
