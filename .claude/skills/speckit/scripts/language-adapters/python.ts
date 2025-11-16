/**
 * Python Language Adapter
 *
 * Handles Python test detection and metadata extraction:
 * - Test functions: test_*
 * - Test classes: Test*
 * - Docstrings
 * - Hash comments
 */

import type { Tree } from 'web-tree-sitter';
import { BaseLanguageAdapter, type InferredMetadata, type TestLocation, type SyntaxNode, filterNullNodes } from './base.js';

export class PythonAdapter extends BaseLanguageAdapter {
  getLanguage(): string {
    return 'python';
  }

  getExtensions(): string[] {
    return ['.py', '.pyi'];
  }

  async getTreeSitterLanguage(): Promise<string> {
    // Return path to WASM file
    return require.resolve('tree-sitter-python/tree-sitter-python.wasm');
  }

  findTestNodes(tree: Tree, sourceCode: string): TestLocation[] {
    const tests: TestLocation[] = [];
    const describeStack: string[] = [];

    const traverse = (node: SyntaxNode) => {
      // Check for test classes (TestSomething)
      if (node.type === 'class_definition') {
        const nameNode = node.childForFieldName('name');
        if (nameNode) {
          const className = sourceCode.slice(nameNode.startIndex, nameNode.endIndex);
          if (className.startsWith('Test')) {
            describeStack.push(className);
            // Traverse children
            for (const child of filterNullNodes(node.children)) {
              traverse(child);
            }
            describeStack.pop();
            return;
          }
        }
      }

      // Check for test functions (test_something)
      if (node.type === 'function_definition') {
        const nameNode = node.childForFieldName('name');
        if (nameNode) {
          const funcName = sourceCode.slice(nameNode.startIndex, nameNode.endIndex);
          if (funcName.startsWith('test_')) {
            tests.push({
              node,
              line: node.startPosition.row + 1,
              testName: funcName,
              describePath: [...describeStack]
            });
          }
        }
      }

      // Continue traversing
      for (const child of filterNullNodes(node.children)) {
        traverse(child);
      }
    };

    traverse(tree.rootNode);
    return tests;
  }

  extractCommentForNode(node: SyntaxNode, sourceCode: string): string {
    const comments: string[] = [];

    // Strategy 1: Check for docstring as first statement in function body
    if (node.type === 'function_definition' || node.type === 'class_definition') {
      const body = node.childForFieldName('body');
      if (body && body.children.length > 0) {
        const firstStatement = filterNullNodes(body.children).find((child) =>
          child.type === 'expression_statement'
        );

        if (firstStatement) {
          const stringNode = filterNullNodes(firstStatement.children).find((child) =>
            child.type === 'string'
          );

          if (stringNode) {
            let docstring = sourceCode.slice(stringNode.startIndex, stringNode.endIndex);
            // Remove quotes (""", ''', ", ')
            docstring = docstring.replace(/^("""|'''|"|')/, '').replace(/("""|'''|"|')$/, '');
            comments.push(docstring.trim());
          }
        }
      }
    }

    // Strategy 2: Check for preceding docstring (expression_statement with string)
    let current = node.previousSibling;

    // Skip whitespace/newline nodes
    while (current && (current.type === 'newline' || current.type === 'indent')) {
      current = current.previousSibling;
    }

    // Check if previous sibling is an expression_statement containing a string (docstring)
    if (current && current.type === 'expression_statement') {
      const stringNode = filterNullNodes(current.children).find((child) =>
        child.type === 'string'
      );

      if (stringNode) {
        let docstring = sourceCode.slice(stringNode.startIndex, stringNode.endIndex);
        // Remove quotes (""", ''', ", ')
        docstring = docstring.replace(/^("""|'''|"|')/, '').replace(/("""|'''|"|')$/, '');
        comments.push(docstring.trim());
      }
    }

    // Strategy 3: Check for comment nodes immediately before the function/class
    current = node.previousSibling;
    const precedingComments: string[] = [];

    while (current && current.type === 'comment') {
      const commentText = sourceCode.slice(current.startIndex, current.endIndex);
      // Remove # prefix
      const cleaned = commentText.replace(/^#\s?/, '').trim();
      precedingComments.unshift(cleaned);
      current = current.previousSibling;
    }

    if (precedingComments.length > 0) {
      comments.push(precedingComments.join('\n'));
    }

    return comments.join('\n');
  }

  generateMetadataComment(metadata: InferredMetadata, indent: string): string {
    const lines: string[] = ['"""'];

    if (metadata.spec) {
      lines.push(`@spec ${metadata.spec}`);
    }

    for (const story of metadata.userStories) {
      lines.push(`@userStory ${story}`);
    }

    for (const req of metadata.functionalReqs) {
      lines.push(`@functionalReq ${req}`);
    }

    lines.push(`@testType ${metadata.testType}`);

    if (metadata.mockDependent) {
      lines.push(`@mockDependent`);
    }

    lines.push('"""');

    return lines.map(line => indent + line).join('\n');
  }

  /**
   * Python-specific mock detection
   */
  isMockDependent(sourceCode: string): boolean {
    const pythonMockPatterns = [
      'unittest.mock',
      'pytest-mock',
      'from unittest.mock import',
      'from unittest import mock',
      '@patch',
      '@mock',
      'Mock(',
      'MagicMock(',
      'mocker.patch'
    ];

    return pythonMockPatterns.some(pattern => sourceCode.includes(pattern)) ||
           super.isMockDependent(sourceCode);
  }

  /**
   * Insert metadata into Python source code
   * Creates standalone docstring ABOVE function definition, AFTER decorators
   * Matches canonical pattern from metadata-schema.md
   */
  insertMetadataIntoSource(
    sourceCode: string,
    testNode: SyntaxNode,
    metadata: InferredMetadata
  ): string {
    const lines = sourceCode.split('\n');

    // Get function name node (on same line as 'def' keyword)
    const nameNode = testNode.childForFieldName('name');
    if (!nameNode) {
      throw new Error('Function has no name node');
    }

    // Extract indentation from 'def' line (after any decorators)
    const defLine = lines[nameNode.startPosition.row];
    const baseIndent = defLine.match(/^\s*/)?.[0] || '';

    // Check for existing metadata docstring before function
    // Skip newlines, indents, AND comments (Gemini recommendation)
    let prevSibling = testNode.previousSibling;
    while (prevSibling && ['newline', 'indent', 'comment'].includes(prevSibling.type)) {
      prevSibling = prevSibling.previousSibling;
    }

    // Check if previous sibling is a metadata docstring
    if (prevSibling && prevSibling.type === 'expression_statement') {
      const stringNode = filterNullNodes(prevSibling.children).find(
        (child) => child.type === 'string'
      );
      if (stringNode) {
        const docstringText = sourceCode.slice(stringNode.startIndex, stringNode.endIndex);
        // Skip if metadata tags already exist (holistic remediation - idempotency)
        if (docstringText.includes('@spec') || docstringText.includes('@testType')) {
          return sourceCode;
        }
      }
    }

    // Build metadata lines with base indentation
    const metadataLines: string[] = [];
    metadataLines.push(`${baseIndent}"""`);
    if (metadata.spec) {
      metadataLines.push(`${baseIndent}@spec ${metadata.spec}`);
    }
    for (const story of metadata.userStories) {
      metadataLines.push(`${baseIndent}@userStory ${story}`);
    }
    for (const req of metadata.functionalReqs) {
      metadataLines.push(`${baseIndent}@functionalReq ${req}`);
    }
    metadataLines.push(`${baseIndent}@testType ${metadata.testType}`);
    if (metadata.mockDependent) {
      metadataLines.push(`${baseIndent}@mockDependent`);
    }
    metadataLines.push(`${baseIndent}"""`);

    // Insert metadata docstring BEFORE the 'def' line (after decorators)
    const insertLine = nameNode.startPosition.row;
    lines.splice(insertLine, 0, ...metadataLines);

    return lines.join('\n');
  }
}
