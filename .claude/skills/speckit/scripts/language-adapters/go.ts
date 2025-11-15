/**
 * Go Language Adapter
 *
 * Handles Go test detection and metadata extraction:
 * - Test functions: TestSomething(t *testing.T)
 * - Benchmark functions: BenchmarkSomething(b *testing.B)
 * - Line comments
 */

import type { Tree } from 'web-tree-sitter';
import { BaseLanguageAdapter, type InferredMetadata, type TestLocation, type SyntaxNode, filterNullNodes } from './base.js';

export class GoAdapter extends BaseLanguageAdapter {
  getLanguage(): string {
    return 'go';
  }

  getExtensions(): string[] {
    return ['.go'];
  }

  async getTreeSitterLanguage(): Promise<string> {
    return require.resolve('tree-sitter-go/tree-sitter-go.wasm');
  }

  findTestNodes(tree: Tree, sourceCode: string): TestLocation[] {
    const tests: TestLocation[] = [];

    const traverse = (node: SyntaxNode) => {
      // Check for function declarations
      if (node.type === 'function_declaration') {
        const nameNode = node.childForFieldName('name');
        if (nameNode) {
          const funcName = sourceCode.slice(nameNode.startIndex, nameNode.endIndex);

          // Check if it's a test function (starts with Test or Benchmark)
          if (funcName.startsWith('Test') || funcName.startsWith('Benchmark')) {
            // Verify it has the correct signature
            const params = node.childForFieldName('parameters');
            if (params) {
              const paramText = sourceCode.slice(params.startIndex, params.endIndex);
              // Check for (t *testing.T) or (b *testing.B)
              if (paramText.includes('*testing.T') || paramText.includes('*testing.B')) {
                tests.push({
                  node,
                  line: node.startPosition.row + 1,
                  testName: funcName,
                  describePath: []
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

  extractCommentForNode(node: SyntaxNode, sourceCode: string): string {
    const comments: string[] = [];
    const lines = sourceCode.split('\n');
    const startLine = node.startPosition.row;

    // Look backwards to collect line comments
    let currentLine = startLine - 1;

    // Skip blank lines
    while (currentLine >= 0 && lines[currentLine].trim() === '') {
      currentLine--;
    }

    // Collect consecutive line comments
    const commentLines: string[] = [];
    while (currentLine >= 0) {
      const line = lines[currentLine].trim();

      if (line.startsWith('//')) {
        const comment = line.replace(/^\/\/\s?/, '');
        commentLines.unshift(comment);
        currentLine--;
      } else {
        break;
      }
    }

    if (commentLines.length > 0) {
      comments.push(commentLines.join('\n'));
    }

    return comments.join('\n');
  }

  generateMetadataComment(metadata: InferredMetadata, indent: string): string {
    const lines: string[] = [];

    if (metadata.spec) {
      lines.push(`// @spec ${metadata.spec}`);
    }

    for (const story of metadata.userStories) {
      lines.push(`// @userStory ${story}`);
    }

    for (const req of metadata.functionalReqs) {
      lines.push(`// @functionalReq ${req}`);
    }

    lines.push(`// @testType ${metadata.testType}`);

    if (metadata.mockDependent) {
      lines.push(`// @mockDependent`);
    }

    return lines.map(line => indent + line).join('\n');
  }

  /**
   * Go-specific mock detection
   */
  isMockDependent(sourceCode: string): boolean {
    const goMockPatterns = [
      'gomock',
      'testify/mock',
      'mockgen',
      'NewMock',
      'mock.Mock',
      'httpmock',
      'httptest.NewServer'
    ];

    return goMockPatterns.some(pattern => sourceCode.includes(pattern)) ||
           super.isMockDependent(sourceCode);
  }

  /**
   * Insert metadata into Go source code
   * Handles Go doc comments (// style)
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

    // Check if there are already comments above this test
    let insertLine = testLine;
    let hasExistingComments = false;
    let commentStartLine = testLine;

    // Look backwards for comments
    let checkLine = testLine - 1;
    while (checkLine >= 0 && lines[checkLine].trim() === '') {
      checkLine--; // Skip blank lines
    }

    // Collect existing comment lines
    const existingCommentLines: number[] = [];
    while (checkLine >= 0 && lines[checkLine].trim().startsWith('//')) {
      existingCommentLines.unshift(checkLine);
      checkLine--;
    }

    if (existingCommentLines.length > 0) {
      hasExistingComments = true;
      commentStartLine = existingCommentLines[0];
      insertLine = commentStartLine;
    }

    // Generate metadata comment lines
    const metadataLines: string[] = [];
    if (metadata.spec) metadataLines.push(`// @spec ${metadata.spec}`);
    for (const story of metadata.userStories) {
      metadataLines.push(`// @userStory ${story}`);
    }
    for (const req of metadata.functionalReqs) {
      metadataLines.push(`// @functionalReq ${req}`);
    }
    metadataLines.push(`// @testType ${metadata.testType}`);
    if (metadata.mockDependent) {
      metadataLines.push(`// @mockDependent`);
    }

    if (hasExistingComments) {
      // Add blank comment line separator if merging
      metadataLines.push('//');
    }

    // Insert metadata comments
    const indentedLines = metadataLines.map(line => indent + line);
    lines.splice(insertLine, 0, ...indentedLines);

    return lines.join('\n');
  }
}
