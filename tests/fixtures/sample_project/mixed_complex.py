"""Complex module mixing all scenarios.

Expected symbols:
- 2 FUNCTION symbols (module_function, main)
- 2 CLASS symbols (Service, Service.Config)
- 3 METHOD symbols (Service.process, Service.validate, Service.Config.load)

Total: 7 symbols
"""


def module_function():
    """Module-level function."""
    return "module"


class Service:
    """Service class with methods and nested class."""

    def process(self, data):
        """Process data."""
        return self.validate(data)

    def validate(self, data):
        """Validate data."""
        return bool(data)

    class Config:
        """Nested configuration class."""

        def load(self, path):
            """Load configuration from path."""
            return {}


def main():
    """Main entry point."""
    service = Service()
    config = Service.Config()
    return service.process("test")
