/**
 * JavaScript/TypeScript Language Adapter
 *
 * Handles JS/TS test detection and metadata extraction:
 * - Test blocks: describe(), it(), test()
 * - JSDoc comments
 * - Supports both .js and .ts files
 */

import type { Tree } from 'web-tree-sitter';
import { BaseLanguageAdapter, type InferredMetadata, type TestLocation, type SyntaxNode, filterNullNodes } from './base.js';

export class JavaScriptAdapter extends BaseLanguageAdapter {
  getLanguage(): string {
    return 'javascript';
  }

  getExtensions(): string[] {
    return ['.js', '.jsx', '.ts', '.tsx'];
  }

  async getTreeSitterLanguage(): Promise<string> {
    // Use TypeScript grammar for all JS/TS files (it's a superset)
    return require.resolve('tree-sitter-typescript/tree-sitter-typescript.wasm');
  }

  findTestNodes(tree: Tree, sourceCode: string): TestLocation[] {
    const tests: TestLocation[] = [];
    const describeStack: string[] = [];

    const traverse = (node: SyntaxNode) => {
      if (node.type === 'call_expression') {
        const func = node.childForFieldName('function');
        if (func) {
          const funcName = sourceCode.slice(func.startIndex, func.endIndex);

          // Check for describe/it/test calls
          if (funcName === 'describe' || funcName === 'it' || funcName === 'test') {
            const testName = this.extractTestName(node, sourceCode);

            if (funcName === 'describe') {
              // Push describe block onto stack
              if (testName) {
                describeStack.push(testName);
              }
              // Traverse children
              for (const child of filterNullNodes(node.children)) {
                traverse(child);
              }
              if (testName) {
                describeStack.pop();
              }
              return;
            } else {
              // it() or test() - this is an actual test
              if (testName) {
                tests.push({
                  node,
                  line: node.startPosition.row + 1,
                  testName,
                  describePath: [...describeStack]
                });
              }
            }
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

  /**
   * Extract test name from the first string argument
   */
  private extractTestName(node: SyntaxNode, sourceCode: string): string | null {
    const args = node.childForFieldName('arguments');
    if (!args) return null;

    for (const child of filterNullNodes(args.children)) {
      if (child.type === 'string' || child.type === 'template_string') {
        let text = sourceCode.slice(child.startIndex, child.endIndex);
        // Remove quotes
        text = text.replace(/^['"`]/, '').replace(/['"`]$/, '');
        return text;
      }
    }

    return null;
  }

  extractCommentForNode(node: SyntaxNode, sourceCode: string): string {
    // In tree-sitter, comments are not part of the AST but exist as "trivia"
    // We need to look backwards from the node's start position to find comments

    const comments: string[] = [];
    const startLine = node.startPosition.row;

    // Look backwards through source lines to find JSDoc or line comments
    const lines = sourceCode.split('\n');
    let currentLine = startLine - 1;

    // Collect JSDoc comment block if present
    if (currentLine >= 0 && lines[currentLine].trim() === '') {
      currentLine--; // Skip blank line
    }

    if (currentLine >= 0) {
      const line = lines[currentLine].trim();

      // Check for end of JSDoc block
      if (line === '*/') {
        const jsdocLines: string[] = [];
        jsdocLines.unshift(line);
        currentLine--;

        // Collect JSDoc lines
        while (currentLine >= 0) {
          const jsdocLine = lines[currentLine].trim();
          jsdocLines.unshift(jsdocLine);

          if (jsdocLine.startsWith('/**')) {
            break;
          }
          currentLine--;
        }

        // Clean up JSDoc
        const jsdoc = jsdocLines.join('\n')
          .replace(/^\/\*\*/, '')
          .replace(/\*\/$/, '')
          .replace(/^\s*\*\s?/gm, '')
          .trim();

        comments.push(jsdoc);
      }
      // Check for single-line comments
      else if (line.startsWith('//')) {
        const singleLineComments: string[] = [];

        while (currentLine >= 0 && lines[currentLine].trim().startsWith('//')) {
          const comment = lines[currentLine].trim().replace(/^\/\/\s?/, '');
          singleLineComments.unshift(comment);
          currentLine--;
        }

        comments.push(singleLineComments.join('\n'));
      }
    }

    return comments.join('\n');
  }

  generateMetadataComment(metadata: InferredMetadata, indent: string): string {
    const lines: string[] = ['/**'];

    if (metadata.spec) {
      lines.push(` * @spec ${metadata.spec}`);
    }

    for (const story of metadata.userStories) {
      lines.push(` * @userStory ${story}`);
    }

    for (const req of metadata.functionalReqs) {
      lines.push(` * @functionalReq ${req}`);
    }

    lines.push(` * @testType ${metadata.testType}`);

    if (metadata.mockDependent) {
      lines.push(` * @mockDependent`);
    }

    lines.push(' */');

    return lines.map(line => indent + line).join('\n');
  }

  /**
   * JavaScript/TypeScript-specific mock detection
   */
  isMockDependent(sourceCode: string): boolean {
    const jsMockPatterns = [
      'jest.mock',
      'vi.mock',
      'vitest.mock',
      'sinon',
      'jest.fn(',
      'vi.fn(',
      'createMock',
      'mockImplementation',
      'mockReturnValue'
    ];

    return jsMockPatterns.some(pattern => sourceCode.includes(pattern)) ||
           super.isMockDependent(sourceCode);
  }

  /**
   * Insert metadata into JavaScript/TypeScript source code
   * Handles JSDoc comments for test() and it() calls
   */
  insertMetadataIntoSource(
    sourceCode: string,
    testNode: SyntaxNode,
    metadata: InferredMetadata
  ): string {
    const lines = sourceCode.split('\n');
    const testLine = testNode.startPosition.row;

    // Get indentation from the test line
    const testLineText = lines[testLine];
    const indent = testLineText.match(/^\s*/)?.[0] || '';

    // Check if there's already a JSDoc comment above this test
    let insertLine = testLine;
    let hasExistingJSDoc = false;
    let jsdocStartLine = -1;
    let jsdocEndLine = -1;

    // Look backwards for JSDoc
    let checkLine = testLine - 1;
    while (checkLine >= 0 && lines[checkLine].trim() === '') {
      checkLine--; // Skip blank lines
    }

    if (checkLine >= 0 && lines[checkLine].trim() === '*/') {
      // Found end of JSDoc block
      jsdocEndLine = checkLine;
      checkLine--;

      // Find start of JSDoc block
      while (checkLine >= 0) {
        if (lines[checkLine].trim().startsWith('/**')) {
          jsdocStartLine = checkLine;
          hasExistingJSDoc = true;
          break;
        }
        checkLine--;
      }
    }

    if (hasExistingJSDoc && jsdocStartLine >= 0 && jsdocEndLine >= 0) {
      // Merge metadata into existing JSDoc
      const metadataLines: string[] = [];
      metadataLines.push(' *');
      if (metadata.spec) metadataLines.push(` * @spec ${metadata.spec}`);
      for (const story of metadata.userStories) {
        metadataLines.push(` * @userStory ${story}`);
      }
      for (const req of metadata.functionalReqs) {
        metadataLines.push(` * @functionalReq ${req}`);
      }
      metadataLines.push(` * @testType ${metadata.testType}`);
      if (metadata.mockDependent) {
        metadataLines.push(` * @mockDependent`);
      }

      // Insert before closing */
      const indentedLines = metadataLines.map(line => indent + line);
      lines.splice(jsdocEndLine, 0, ...indentedLines);
    } else {
      // No existing JSDoc - create new one
      const jsdocLines: string[] = [];
      jsdocLines.push('/**');
      if (metadata.spec) jsdocLines.push(` * @spec ${metadata.spec}`);
      for (const story of metadata.userStories) {
        jsdocLines.push(` * @userStory ${story}`);
      }
      for (const req of metadata.functionalReqs) {
        jsdocLines.push(` * @functionalReq ${req}`);
      }
      jsdocLines.push(` * @testType ${metadata.testType}`);
      if (metadata.mockDependent) {
        jsdocLines.push(` * @mockDependent`);
      }
      jsdocLines.push(' */');

      // Insert before test line
      const indentedLines = jsdocLines.map(line => indent + line);
      lines.splice(testLine, 0, ...indentedLines);
    }

    return lines.join('\n');
  }
}
