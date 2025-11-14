#!/usr/bin/env bun

/**
 * Auto-Tagging Script for Test Metadata Migration
 *
 * Scans existing test files and adds JSDoc tags with inferred metadata:
 * - @spec from file path (specs/001-name/tests/)
 * - @userStory from existing comments (Part of US1)
 * - @functionalReq from existing comments (Validates FR-031)
 * - @testType from file path
 * - @mockDependent from imports
 *
 * Usage:
 *   bun .claude/skills/speckit/scripts/add-test-tags.ts [--write] [--dry-run]
 *
 * Options:
 *   --write     Write changes to files
 *   --dry-run   Show what would be changed without writing
 *   --help      Show this help message
 */

import * as ts from 'typescript';
import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';

interface InferredMetadata {
  spec: string | null;
  userStories: string[];
  functionalReqs: string[];
  testType: 'unit' | 'integration' | 'e2e';
  mockDependent: boolean;
}

interface TestLocation {
  node: ts.Node;
  line: number;
  needsTag: boolean;
  inferredMetadata: InferredMetadata;
}

// Parse command line arguments
const args = process.argv.slice(2);
const WRITE_MODE = args.includes('--write');
const DRY_RUN = args.includes('--dry-run') || !WRITE_MODE;
const SHOW_HELP = args.includes('--help') || args.includes('-h');

if (SHOW_HELP) {
  console.log(`
Auto-Tagging Script for Test Metadata Migration

Usage:
  bun .claude/skills/speckit/scripts/add-test-tags.ts [options]

Options:
  --write      Write changes to files
  --dry-run    Show what would be changed without writing (default)
  --help, -h   Show this help message

Examples:
  # Dry run (show changes)
  bun .claude/skills/speckit/scripts/add-test-tags.ts

  # Write changes to files
  bun .claude/skills/speckit/scripts/add-test-tags.ts --write
`);
  process.exit(0);
}

// Find repo root
function findRepoRoot(): string {
  let dir = process.cwd();
  while (dir !== path.parse(dir).root) {
    if (fs.existsSync(path.join(dir, 'package.json'))) {
      return dir;
    }
    dir = path.dirname(dir);
  }
  return process.cwd();
}

const REPO_ROOT = findRepoRoot();

// Infer spec number from file path
function inferSpecNumber(filePath: string): string | null {
  // Check if file is in specs/NNN-* directory
  const match = filePath.match(/specs[/\\](\d{3})-[^/\\]+[/\\]/);
  if (match) {
    return match[1];
  }

  // Default to 001 for tests not in a spec directory
  return '001';
}

// Infer test type from file path
function inferTestType(filePath: string): 'unit' | 'integration' | 'e2e' {
  if (filePath.includes('/e2e/') || filePath.includes('.e2e.')) {
    return 'e2e';
  }
  if (filePath.includes('/integration/')) {
    return 'integration';
  }
  return 'unit';
}

// Extract user stories from file content
function extractUserStories(content: string): string[] {
  const stories = new Set<string>();

  // Match: US1, US2, US10, etc.
  const matches = content.matchAll(/US\d+/g);
  for (const match of matches) {
    stories.add(match[0]);
  }

  return Array.from(stories);
}

// Extract functional requirements from file content
function extractFunctionalReqs(content: string): string[] {
  const reqs = new Set<string>();

  // Match: FR-001, FR-031, etc.
  const matches = content.matchAll(/FR-\d+[a-z]?/g);
  for (const match of matches) {
    reqs.add(match[0]);
  }

  return Array.from(reqs);
}

// Check if file imports mockAPI
function checkMockDependent(content: string): boolean {
  return content.includes('mockAPI') ||
         content.includes("from '@/api/mock'") ||
         content.includes('from "../api/mock"');
}

// Check if node already has JSDoc with @spec tag
function hasSpecTag(node: ts.Node, sourceFile: ts.SourceFile): boolean {
  const jsDocTags = ts.getJSDocTags(node);
  return jsDocTags.some(tag => tag.tagName.text === 'spec');
}

// Generate JSDoc comment with inferred metadata
function generateJSDoc(metadata: InferredMetadata, indent: string): string {
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

// Process a single test file
function processTestFile(filePath: string): { modified: boolean; changes: string[] } {
  const content = fs.readFileSync(filePath, 'utf-8');
  const sourceFile = ts.createSourceFile(
    filePath,
    content,
    ts.ScriptTarget.Latest,
    true
  );

  // Infer file-level metadata
  const spec = inferSpecNumber(filePath);
  const testType = inferTestType(filePath);
  const userStories = extractUserStories(content);
  const functionalReqs = extractFunctionalReqs(content);
  const mockDependent = checkMockDependent(content);

  const metadata: InferredMetadata = {
    spec,
    userStories,
    functionalReqs,
    testType,
    mockDependent
  };

  // Find all describe/it/test blocks that need tags
  const locationsToTag: TestLocation[] = [];

  function visit(node: ts.Node) {
    if (ts.isCallExpression(node) &&
        ts.isIdentifier(node.expression)) {
      const funcName = node.expression.text;

      if (funcName === 'describe' || funcName === 'it' || funcName === 'test') {
        if (!hasSpecTag(node, sourceFile)) {
          const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
          locationsToTag.push({
            node,
            line: line + 1,
            needsTag: true,
            inferredMetadata: metadata
          });
        }
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);

  if (locationsToTag.length === 0) {
    return { modified: false, changes: [] };
  }

  // Sort by line number (descending) so we can insert from bottom to top
  locationsToTag.sort((a, b) => b.line - a.line);

  let modifiedContent = content;
  const changes: string[] = [];

  for (const location of locationsToTag) {
    const { line, node, inferredMetadata } = location;
    const lines = modifiedContent.split('\n');

    // Get indentation from the current line
    const currentLine = lines[line - 1];
    const indent = currentLine.match(/^\s*/)?.[0] || '';

    // Generate JSDoc
    const jsdoc = generateJSDoc(inferredMetadata, indent);

    // Insert JSDoc before the describe/it/test line
    lines.splice(line - 1, 0, jsdoc);
    modifiedContent = lines.join('\n');

    const funcName = ts.isCallExpression(node) && ts.isIdentifier(node.expression)
      ? node.expression.text
      : 'test';
    changes.push(`  Line ${line}: Added JSDoc to ${funcName}()`);
  }

  if (WRITE_MODE) {
    fs.writeFileSync(filePath, modifiedContent, 'utf-8');
  }

  return { modified: true, changes };
}

// Main execution
async function main() {
  console.log(`\nAuto-Tagging Script`);
  console.log(`==================\n`);
  console.log(`Mode: ${WRITE_MODE ? 'WRITE' : 'DRY RUN'}\n`);

  // Find all test files
  const testFiles = await glob('**/*.{test,spec}.{ts,tsx}', {
    cwd: REPO_ROOT,
    ignore: ['node_modules/**', 'dist/**', 'build/**'],
    absolute: true
  });

  console.log(`Found ${testFiles.length} test files\n`);

  let modifiedCount = 0;
  let totalChanges = 0;

  for (const file of testFiles) {
    const relativePath = path.relative(REPO_ROOT, file);

    try {
      const { modified, changes } = processTestFile(file);

      if (modified) {
        modifiedCount++;
        totalChanges += changes.length;

        console.log(`✓ ${relativePath}`);
        for (const change of changes) {
          console.log(change);
        }
        console.log('');
      }
    } catch (error) {
      console.error(`✗ ${relativePath}`);
      console.error(`  Error: ${error instanceof Error ? error.message : String(error)}`);
      console.log('');
    }
  }

  console.log(`\nSummary`);
  console.log(`=======`);
  console.log(`Files processed: ${testFiles.length}`);
  console.log(`Files modified: ${modifiedCount}`);
  console.log(`Total changes: ${totalChanges}`);

  if (DRY_RUN) {
    console.log(`\nℹ This was a dry run. Use --write to apply changes.\n`);
  } else {
    console.log(`\n✓ Changes written to files.\n`);
  }
}

main().catch(error => {
  console.error('Error:', error);
  process.exit(1);
});
