"""Module with nested functions (closures).

Expected symbols:
- 2 FUNCTION symbols (outer_function, another_function)
- 2 FUNCTION symbols for closures (inner_function, helper)

Note: Nested functions should be counted as FUNCTION, not METHOD.
"""


def outer_function(x: int):
    """Function with nested closure."""

    def inner_function(y: int):
        """Nested closure function."""
        return x + y

    return inner_function(10)


def another_function():
    """Another function with nested helper."""

    def helper():
        """Nested helper function."""
        return "help"

    return helper()
