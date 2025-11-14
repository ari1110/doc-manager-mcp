#!/usr/bin/env python3
"""
Universal Test Parser using Tree-sitter

Parses test files across multiple languages to extract metadata from comments/docstrings:
- Test structure (classes, functions, methods)
- Annotation tags (@spec, @userStory, @functionalReq, etc.)
- File metadata (path, modification date)
- Mock dependency detection

Outputs JSON array of test metadata objects.

Supported languages: Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, PHP, C, C++

Usage:
    python parse-test-file.py <file-path> [--json]

Output:
    JSON array of TestMetadata objects
"""

import sys
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict

try:
    from tree_sitter_languages import get_parser, get_language
except ImportError:
    print("Error: tree-sitter-languages not installed", file=sys.stderr)
    print("Install with: pip install tree-sitter-languages", file=sys.stderr)
    sys.exit(1)


@dataclass
class TestMetadata:
    """Metadata for a single test."""
    id: str
    file: str
    type: str  # 'unit' | 'integration' | 'e2e'
    describePath: List[str]
    testName: str
    lineNumber: int

    # From annotation tags
    specNumber: Optional[str]
    userStories: List[str]
    functionalReqs: List[str]
    testType: Optional[str]
    mockDependent: bool
    retirementCandidate: bool
    contractTest: bool
    slow: bool

    # File metadata
    createdDate: str
    lastModified: str
    tags: List[str]


class UniversalTestParser:
    """Parse test files across multiple languages using tree-sitter."""

    # Language detection patterns
    LANGUAGE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.go': 'go',
        '.rs': 'rust',
        '.java': 'java',
        '.rb': 'ruby',
        '.php': 'php',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
    }

    # Test function/method name patterns by language
    TEST_PATTERNS = {
        'python': [
            r'^test_',  # pytest/unittest: test_something
            r'^Test',   # pytest classes: TestSomething
        ],
        'javascript': [r'^(test|it|describe)$'],
        'typescript': [r'^(test|it|describe)$'],
        'tsx': [r'^(test|it|describe)$'],
        'go': [r'^Test', r'^Benchmark'],  # Go: TestSomething, BenchmarkSomething
        'rust': [r'^test_', r'#\[test\]'],  # Rust: #[test] or test_ prefix
        'java': [r'^test', r'@Test'],  # JUnit: @Test annotation
        'ruby': [r'^test_', r'^it\s', r'^describe\s'],  # RSpec/minitest
        'php': [r'^test', r'@test'],  # PHPUnit
    }

    # Mock/dependency detection patterns
    MOCK_PATTERNS = [
        'mock', 'Mock', 'MOCK',
        'stub', 'Stub', 'STUB',
        'fake', 'Fake', 'FAKE',
        'spy', 'Spy', 'SPY',
        'double', 'Double', 'DOUBLE',
        '@patch', '@mock',  # Python decorators
        'jest.mock', 'vi.mock',  # JS mocking
    ]

    def __init__(self, file_path: str):
        self.file_path = Path(file_path).resolve()
        self.language = self._detect_language()
        self.parser = get_parser(self.language)
        self.source_code = self.file_path.read_text(encoding='utf-8', errors='ignore')
        self.tree = self.parser.parse(bytes(self.source_code, 'utf8'))
        self.tests: List[TestMetadata] = []
        self.describe_stack: List[str] = []

    def _detect_language(self) -> str:
        """Detect language from file extension."""
        ext = self.file_path.suffix.lower()
        if ext not in self.LANGUAGE_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {ext}")
        return self.LANGUAGE_EXTENSIONS[ext]

    def _generate_test_id(self, describe_path: List[str], test_name: str) -> str:
        """Generate unique test ID from file path, describe path, and test name."""
        content = f"{self.file_path}::{':'.join(describe_path)}::{test_name}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _infer_test_type(self) -> str:
        """Infer test type from file path."""
        path_str = str(self.file_path).lower()
        if '/e2e/' in path_str or '.e2e.' in path_str or 'end-to-end' in path_str:
            return 'e2e'
        if '/integration/' in path_str or '.integration.' in path_str:
            return 'integration'
        return 'unit'

    def _detect_mock_dependency(self) -> bool:
        """Check if file imports or uses mocking libraries."""
        for pattern in self.MOCK_PATTERNS:
            if pattern in self.source_code:
                return True
        return False

    def _extract_tags_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract @tag annotations from comment/docstring text."""
        tags = {}

        # Pattern: @tagName value or @tagName (for flags)
        pattern = r'@(\w+)(?:\s+([^\n@]+))?'
        matches = re.finditer(pattern, text)

        for match in matches:
            tag_name = match.group(1)
            value = match.group(2)

            if tag_name not in tags:
                tags[tag_name] = []

            if value:
                tags[tag_name].append(value.strip())
            else:
                # Flag tag (like @mockDependent)
                tags[tag_name].append('true')

        return tags

    def _get_node_text(self, node) -> str:
        """Get text content of a node."""
        return self.source_code[node.start_byte:node.end_byte]

    def _get_comment_before_node(self, node) -> str:
        """Extract comment/docstring immediately before a node."""
        comments = []

        # Get previous siblings that are comments
        current = node.prev_sibling
        while current and current.type in ['comment', 'block_comment', 'line_comment', 'expression_statement']:
            # For Python, docstrings are expression_statements containing a string
            if current.type == 'expression_statement' and self.language == 'python':
                # Check if it contains a string (docstring)
                string_node = current.child_by_field_name('value') or current.children[0] if current.children else None
                if string_node and string_node.type == 'string':
                    docstring = self._get_node_text(string_node)
                    # Remove quotes
                    docstring = docstring.strip('"""').strip("'''").strip('"').strip("'")
                    comments.insert(0, docstring)
            else:
                comment_text = self._get_node_text(current)
                # Clean up comment syntax
                comment_text = re.sub(r'^(//|#|/\*|\*/)', '', comment_text, flags=re.MULTILINE)
                comments.insert(0, comment_text)

            current = current.prev_sibling

        return '\n'.join(comments)

    def _extract_test_name(self, node) -> Optional[str]:
        """Extract test name from function/method node."""
        name_node = node.child_by_field_name('name')
        if name_node:
            return self._get_node_text(name_node)

        # For JavaScript/TypeScript describe/it calls, get the first string argument
        if self.language in ['javascript', 'typescript', 'tsx']:
            if node.type == 'call_expression':
                args = node.child_by_field_name('arguments')
                if args and args.children:
                    for child in args.children:
                        if child.type in ['string', 'template_string', 'string_fragment']:
                            text = self._get_node_text(child)
                            # Remove quotes
                            return text.strip('"').strip("'").strip('`')

        return None

    def _is_test_node(self, node) -> bool:
        """Check if node represents a test function/method."""
        if not node:
            return False

        node_type = node.type

        # Language-specific test detection
        if self.language == 'python':
            if node_type in ['function_definition', 'class_definition']:
                name = self._extract_test_name(node)
                if name:
                    for pattern in self.TEST_PATTERNS['python']:
                        if re.match(pattern, name):
                            return True

        elif self.language in ['javascript', 'typescript', 'tsx']:
            if node_type == 'call_expression':
                func = node.child_by_field_name('function')
                if func:
                    func_name = self._get_node_text(func)
                    if func_name in ['test', 'it', 'describe']:
                        return True

        elif self.language == 'go':
            if node_type == 'function_declaration':
                name = self._extract_test_name(node)
                if name and (name.startswith('Test') or name.startswith('Benchmark')):
                    return True

        elif self.language == 'rust':
            # Check for #[test] attribute
            if node_type == 'function_item':
                # Look for attribute list
                for child in node.children:
                    if child.type == 'attribute_item':
                        attr_text = self._get_node_text(child)
                        if '#[test]' in attr_text:
                            return True
                # Also check function name
                name = self._extract_test_name(node)
                if name and name.startswith('test_'):
                    return True

        elif self.language == 'java':
            if node_type == 'method_declaration':
                # Check for @Test annotation
                for child in node.children:
                    if child.type == 'modifiers':
                        mods_text = self._get_node_text(child)
                        if '@Test' in mods_text:
                            return True
                # Also check method name
                name = self._extract_test_name(node)
                if name and name.startswith('test'):
                    return True

        return False

    def _process_test_node(self, node, file_tags: Dict[str, List[str]]):
        """Process a test node and extract metadata."""
        test_name = self._extract_test_name(node)
        if not test_name:
            return

        # Get line number
        line_number = node.start_point[0] + 1

        # Extract comments/docstrings
        comment_text = self._get_comment_before_node(node)
        test_tags = self._extract_tags_from_text(comment_text)

        # Merge file-level and test-level tags (test-level takes precedence)
        all_tags = {**file_tags, **test_tags}

        # Parse standard tags
        spec_number = all_tags.get('spec', [None])[0]
        user_stories = all_tags.get('userStory', [])
        functional_reqs = all_tags.get('functionalReq', [])
        explicit_test_type = all_tags.get('testType', [None])[0]
        mock_dependent = 'mockDependent' in all_tags or self._detect_mock_dependency()
        retirement_candidate = 'retirementCandidate' in all_tags
        contract_test = 'contractTest' in all_tags
        slow = 'slow' in all_tags

        # Collect custom tags
        standard_tags = {'spec', 'userStory', 'functionalReq', 'testType', 'mockDependent',
                        'retirementCandidate', 'contractTest', 'slow'}
        custom_tags = [tag for tag in all_tags.keys() if tag not in standard_tags]

        # Get file timestamps
        stat = self.file_path.stat()
        created_date = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified_date = datetime.fromtimestamp(stat.st_mtime).isoformat()

        # Determine test type
        test_type = explicit_test_type or self._infer_test_type()

        # Create metadata
        metadata = TestMetadata(
            id=self._generate_test_id(self.describe_stack.copy(), test_name),
            file=str(self.file_path),
            type=test_type,
            describePath=self.describe_stack.copy(),
            testName=test_name,
            lineNumber=line_number,
            specNumber=spec_number,
            userStories=user_stories,
            functionalReqs=functional_reqs,
            testType=explicit_test_type,
            mockDependent=mock_dependent,
            retirementCandidate=retirement_candidate,
            contractTest=contract_test,
            slow=slow,
            createdDate=created_date,
            lastModified=modified_date,
            tags=custom_tags
        )

        self.tests.append(metadata)

    def _traverse(self, node, file_tags: Dict[str, List[str]]):
        """Recursively traverse the syntax tree and extract tests."""
        if not node:
            return

        # Check if this is a describe block (for JS/TS)
        if self.language in ['javascript', 'typescript', 'tsx']:
            if node.type == 'call_expression':
                func = node.child_by_field_name('function')
                if func and self._get_node_text(func) == 'describe':
                    describe_name = None
                    args = node.child_by_field_name('arguments')
                    if args and args.children:
                        for child in args.children:
                            if child.type in ['string', 'template_string', 'string_fragment']:
                                describe_name = self._get_node_text(child).strip('"').strip("'").strip('`')
                                break

                    if describe_name:
                        self.describe_stack.append(describe_name)
                        # Traverse children
                        for child in node.children:
                            self._traverse(child, file_tags)
                        self.describe_stack.pop()
                        return

        # Check if this is a test class (for Python)
        if self.language == 'python' and node.type == 'class_definition':
            class_name = self._extract_test_name(node)
            if class_name and class_name.startswith('Test'):
                self.describe_stack.append(class_name)
                # Traverse children
                for child in node.children:
                    self._traverse(child, file_tags)
                self.describe_stack.pop()
                return

        # Check if this is a test node
        if self._is_test_node(node):
            self._process_test_node(node, file_tags)

        # Continue traversing
        for child in node.children:
            self._traverse(child, file_tags)

    def parse(self) -> List[Dict[str, Any]]:
        """Parse the test file and return list of test metadata."""
        # Extract file-level tags from the first comment/docstring
        file_tags = {}
        if self.tree.root_node.children:
            first_node = self.tree.root_node.children[0]
            if first_node.type in ['comment', 'expression_statement']:
                comment_text = self._get_comment_before_node(first_node) or self._get_node_text(first_node)
                file_tags = self._extract_tags_from_text(comment_text)

        # Traverse the tree
        self._traverse(self.tree.root_node, file_tags)

        # Convert to dict for JSON serialization
        return [asdict(test) for test in self.tests]


def main():
    """Main entry point."""
    # Parse arguments
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0 if '--help' in sys.argv or '-h' in sys.argv else 1)

    file_path = sys.argv[1]
    json_mode = '--json' in sys.argv or True  # Always output JSON

    # Validate file exists
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Parse the file
        parser = UniversalTestParser(file_path)
        tests = parser.parse()

        # Output results
        if json_mode:
            print(json.dumps(tests, indent=2))
        else:
            print(f"Parsed {len(tests)} tests from {file_path}")
            for test in tests:
                describe_path = ' > '.join(test['describePath']) if test['describePath'] else ''
                print(f"  [{test['type']}] {describe_path} > {test['testName']}")
                print(f"    Spec: {test['specNumber'] or 'none'}")
                print(f"    User Stories: {', '.join(test['userStories']) or 'none'}")
                print(f"    Functional Reqs: {', '.join(test['functionalReqs']) or 'none'}")
                print()

    except Exception as e:
        print(f"Error parsing test file: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
