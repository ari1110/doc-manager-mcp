/**
 * Rust Language Adapter
 *
 * Handles Rust test detection and metadata extraction:
 * - Test functions: #[test] or #[tokio::test]
 * - Doc comments
 * - Block comments
 */

import type { Tree } from 'web-tree-sitter';
import { BaseLanguageAdapter, type InferredMetadata, type TestLocation, type SyntaxNode, filterNullNodes } from './base.js';

export class RustAdapter extends BaseLanguageAdapter {
  getLanguage(): string {
    return 'rust';
  }

  getExtensions(): string[] {
    return ['.rs'];
  }

  async getTreeSitterLanguage(): Promise<string> {
    return require.resolve('tree-sitter-rust/tree-sitter-rust.wasm');
  }

  findTestNodes(tree: Tree, sourceCode: string): TestLocation[] {
    const tests: TestLocation[] = [];

    const traverse = (node: SyntaxNode) => {
      // Check for function items with #[test] attribute
      if (node.type === 'function_item') {
        let hasTestAttribute = false;

        // Look for attribute nodes
        for (const child of filterNullNodes(node.children)) {
          if (child.type === 'attribute_item') {
            const attrText = sourceCode.slice(child.startIndex, child.endIndex);
            // Check for #[test], #[tokio::test], #[async_std::test], etc.
            if (attrText.includes('#[test]') || attrText.includes('::test]')) {
              hasTestAttribute = true;
              break;
            }
          }
        }

        if (hasTestAttribute) {
          const nameNode = node.childForFieldName('name');
          if (nameNode) {
            const funcName = sourceCode.slice(nameNode.startIndex, nameNode.endIndex);
            tests.push({
              node,
              line: node.startPosition.row + 1,
              testName: funcName,
              describePath: []
            });
          }
        } else {
          // Also check for test_ prefix (common convention)
          const nameNode = node.childForFieldName('name');
          if (nameNode) {
            const funcName = sourceCode.slice(nameNode.startIndex, nameNode.endIndex);
            if (funcName.startsWith('test_')) {
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

    let currentLine = startLine - 1;

    // Skip blank lines
    while (currentLine >= 0 && lines[currentLine].trim() === '') {
      currentLine--;
    }

    // Skip attribute lines (#[test], #[tokio::test], etc.)
    while (currentLine >= 0 && lines[currentLine].trim().startsWith('#[')) {
      currentLine--;
    }

    // Skip more blank lines after attributes
    while (currentLine >= 0 && lines[currentLine].trim() === '') {
      currentLine--;
    }

    // Collect doc comments (///) or block doc comments (/** ... */)
    const commentLines: string[] = [];

    // Check for block comment
    if (currentLine >= 0 && lines[currentLine].trim().endsWith('*/')) {
      const blockLines: string[] = [];
      blockLines.unshift(lines[currentLine].trim());
      currentLine--;

      while (currentLine >= 0) {
        const line = lines[currentLine].trim();
        blockLines.unshift(line);

        if (line.startsWith('/**') || line.startsWith('/*')) {
          break;
        }
        currentLine--;
      }

      // Clean up block comment
      const blockComment = blockLines.join('\n')
        .replace(/^\/\*\*?/, '')
        .replace(/\*\/$/, '')
        .replace(/^\s*\*\s?/gm, '')
        .trim();

      comments.push(blockComment);
    }
    // Check for doc comment lines (///)
    else {
      while (currentLine >= 0) {
        const line = lines[currentLine].trim();

        if (line.startsWith('///')) {
          const comment = line.replace(/^\/\/\/\s?/, '');
          commentLines.unshift(comment);
          currentLine--;
        } else {
          break;
        }
      }

      if (commentLines.length > 0) {
        comments.push(commentLines.join('\n'));
      }
    }

    return comments.join('\n');
  }

  generateMetadataComment(metadata: InferredMetadata, indent: string): string {
    const lines: string[] = [];

    if (metadata.spec) {
      lines.push(`/// @spec ${metadata.spec}`);
    }

    for (const story of metadata.userStories) {
      lines.push(`/// @userStory ${story}`);
    }

    for (const req of metadata.functionalReqs) {
      lines.push(`/// @functionalReq ${req}`);
    }

    lines.push(`/// @testType ${metadata.testType}`);

    if (metadata.mockDependent) {
      lines.push(`/// @mockDependent`);
    }

    return lines.map(line => indent + line).join('\n');
  }

  /**
   * Rust-specific mock detection
   */
  isMockDependent(sourceCode: string): boolean {
    const rustMockPatterns = [
      'mockall',
      'mockito',
      '#[automock]',
      'mock!',
      'MockServer',
      'fake::'
    ];

    return rustMockPatterns.some(pattern => sourceCode.includes(pattern)) ||
           super.isMockDependent(sourceCode);
  }
}
