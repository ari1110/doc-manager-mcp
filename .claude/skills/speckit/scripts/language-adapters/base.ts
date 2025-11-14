/**
 * Base types and interfaces for language adapters
 */

import type { Node, Tree } from 'web-tree-sitter';

export type SyntaxNode = Node;

/**
 * Helper to filter out null nodes from children arrays
 */
export function filterNullNodes(nodes: readonly (Node | null)[]): Node[] {
  return nodes.filter((node): node is Node => node !== null);
}

export interface InferredMetadata {
  spec: string | null;
  userStories: string[];
  functionalReqs: string[];
  testType: 'unit' | 'integration' | 'e2e';
  mockDependent: boolean;
}

export interface TestLocation {
  node: SyntaxNode;
  line: number;
  testName: string;
  describePath: string[];
}

export interface TagExtractionResult {
  spec?: string;
  userStories?: string[];
  functionalReqs?: string[];
  testType?: 'unit' | 'integration' | 'e2e';
  mockDependent?: boolean;
  retirementCandidate?: boolean;
  contractTest?: boolean;
  slow?: boolean;
  [key: string]: any; // Allow custom tags
}

/**
 * Base language adapter interface
 * Each language implements this to provide language-specific parsing logic
 */
export interface LanguageAdapter {
  /**
   * Get the language name (e.g., 'python', 'javascript', 'go', 'rust')
   */
  getLanguage(): string;

  /**
   * Get file extensions supported by this adapter (e.g., ['.py', '.pyi'])
   */
  getExtensions(): string[];

  /**
   * Get the path to the tree-sitter WASM file for this adapter
   */
  getTreeSitterLanguage(): Promise<string>;

  /**
   * Find all test nodes in the syntax tree
   * Returns an array of test locations with metadata
   */
  findTestNodes(tree: Tree, sourceCode: string): TestLocation[];

  /**
   * Extract comment/docstring text associated with a node
   * Different languages have different comment styles
   */
  extractCommentForNode(node: SyntaxNode, sourceCode: string): string;

  /**
   * Check if the file or test is mock-dependent
   * Based on imports or specific patterns
   */
  isMockDependent(sourceCode: string): boolean;

  /**
   * Infer test type from file path
   * Default implementation in base, can be overridden
   */
  inferTestType(filePath: string): 'unit' | 'integration' | 'e2e';

  /**
   * Generate JSDoc/comment block with metadata tags
   * Returns the formatted comment string with proper indentation
   */
  generateMetadataComment(metadata: InferredMetadata, indent: string): string;

  /**
   * Extract @tag annotations from comment text
   */
  extractTags(commentText: string): TagExtractionResult;

  /**
   * Infer spec number from file path
   */
  inferSpecNumber(filePath: string): string | null;

  /**
   * Extract user stories from file content
   */
  extractUserStories(content: string): string[];

  /**
   * Extract functional requirements from file content
   */
  extractFunctionalReqs(content: string): string[];
}

/**
 * Base implementation with common functionality
 */
export abstract class BaseLanguageAdapter implements LanguageAdapter {
  abstract getLanguage(): string;
  abstract getExtensions(): string[];
  abstract getTreeSitterLanguage(): Promise<string>;
  abstract findTestNodes(tree: Tree, sourceCode: string): TestLocation[];
  abstract extractCommentForNode(node: SyntaxNode, sourceCode: string): string;
  abstract generateMetadataComment(metadata: InferredMetadata, indent: string): string;

  /**
   * Default implementation for test type inference from file path
   */
  inferTestType(filePath: string): 'unit' | 'integration' | 'e2e' {
    const pathLower = filePath.toLowerCase();

    if (pathLower.includes('/e2e/') || pathLower.includes('.e2e.') || pathLower.includes('end-to-end')) {
      return 'e2e';
    }

    if (pathLower.includes('/integration/') || pathLower.includes('.integration.')) {
      return 'integration';
    }

    return 'unit';
  }

  /**
   * Default implementation for mock dependency detection
   */
  isMockDependent(sourceCode: string): boolean {
    const mockPatterns = [
      'mock', 'Mock', 'MOCK',
      'stub', 'Stub', 'STUB',
      'fake', 'Fake', 'FAKE',
      'spy', 'Spy', 'SPY',
      'double', 'Double', 'DOUBLE',
      '@patch', '@mock',
      'jest.mock', 'vi.mock', 'vitest.mock',
      'unittest.mock', 'pytest-mock'
    ];

    return mockPatterns.some(pattern => sourceCode.includes(pattern));
  }

  /**
   * Extract @tag annotations from comment text
   * Common across all languages
   */
  extractTags(commentText: string): TagExtractionResult {
    const tags: TagExtractionResult = {};

    // Pattern: @tagName value or @tagName (for flags)
    const pattern = /@(\w+)(?:\s+([^\n@]+))?/g;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(commentText)) !== null) {
      const tagName = match[1];
      const value = match[2]?.trim();

      switch (tagName) {
        case 'spec':
          tags.spec = value;
          break;
        case 'userStory':
          if (!tags.userStories) tags.userStories = [];
          if (value) tags.userStories.push(value);
          break;
        case 'functionalReq':
          if (!tags.functionalReqs) tags.functionalReqs = [];
          if (value) tags.functionalReqs.push(value);
          break;
        case 'testType':
          if (value === 'unit' || value === 'integration' || value === 'e2e') {
            tags.testType = value;
          }
          break;
        case 'mockDependent':
          tags.mockDependent = true;
          break;
        case 'retirementCandidate':
          tags.retirementCandidate = true;
          break;
        case 'contractTest':
          tags.contractTest = true;
          break;
        case 'slow':
          tags.slow = true;
          break;
        default:
          // Custom tag
          tags[tagName] = value || true;
      }
    }

    return tags;
  }

  /**
   * Infer spec number from file path
   * Looks for specs/NNN-name/ pattern
   */
  inferSpecNumber(filePath: string): string | null {
    const match = filePath.match(/specs[/\\](\d{3})-[^/\\]+[/\\]/);
    if (match) {
      return match[1];
    }
    // Default to 001 for tests not in a spec directory
    return '001';
  }

  /**
   * Extract user stories from file content (US1, US2, US10, etc.)
   */
  extractUserStories(content: string): string[] {
    const stories = new Set<string>();
    const matches = content.matchAll(/US\d+/g);
    for (const match of matches) {
      stories.add(match[0]);
    }
    return Array.from(stories);
  }

  /**
   * Extract functional requirements from file content (FR-001, FR-031, etc.)
   */
  extractFunctionalReqs(content: string): string[] {
    const reqs = new Set<string>();
    const matches = content.matchAll(/FR-\d+[a-z]?/g);
    for (const match of matches) {
      reqs.add(match[0]);
    }
    return Array.from(reqs);
  }
}
