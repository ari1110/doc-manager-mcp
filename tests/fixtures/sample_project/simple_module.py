"""Simple module with module-level functions only.

Expected symbols:
- 3 FUNCTION symbols (greet, calculate, main)
"""


def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


def calculate(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def main():
    """Main entry point."""
    print(greet("World"))
    print(calculate(2, 3))
