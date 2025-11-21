"""Module with nested classes.

Expected symbols:
- 2 CLASS symbols (Outer, Outer.Inner)
- 2 METHOD symbols (Outer.outer_method, Outer.Inner.inner_method)
"""


class Outer:
    """Outer class."""

    def outer_method(self):
        """Method in outer class."""
        return "outer"

    class Inner:
        """Nested inner class."""

        def inner_method(self):
            """Method in inner class."""
            return "inner"
