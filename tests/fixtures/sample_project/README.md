# Test Fixtures for Symbol Extraction

This directory contains Python files for testing symbol extraction accuracy.

## Expected Symbol Counts

### simple_module.py
- **3 FUNCTION** symbols: greet, calculate, main
- **Total**: 3 symbols

### simple_class.py
- **1 CLASS** symbol: Calculator
- **3 METHOD** symbols: add, subtract, multiply
- **Total**: 4 symbols

### nested_classes.py
- **2 CLASS** symbols: Outer, Outer.Inner
- **2 METHOD** symbols: Outer.outer_method, Outer.Inner.inner_method
- **Total**: 4 symbols

### nested_functions.py
- **4 FUNCTION** symbols: outer_function, inner_function, another_function, helper
- **Total**: 4 symbols
- **Note**: Nested functions should be FUNCTION type, not METHOD

### mixed_complex.py
- **2 FUNCTION** symbols: module_function, main
- **2 CLASS** symbols: Service, Service.Config
- **3 METHOD** symbols: Service.process, Service.validate, Service.Config.load
- **Total**: 7 symbols

## Overall Expected Total

**22 symbols** across all files:
- 9 FUNCTION symbols
- 5 CLASS symbols
- 8 METHOD symbols

## Usage

These fixtures are used for:
1. A/B testing symbol extraction changes
2. Verifying no false negatives after deduplication fix
3. Testing nested class method attribution
4. Ensuring closures/nested functions are handled correctly
