#!/usr/bin/env bun

/**
 * Universal Auto-Tagging Script for Test Metadata Migration
 *
 * Scans existing test files across multiple languages and adds metadata tags:
 * - @spec from file path (specs/001-name/tests/)
 * - @userStory from existing comments (US1, US2, etc.)
 * - @functionalReq from existing comments (FR-001, FR-031, etc.)
 * - @testType from file path (unit/integration/e2e)
 * - @mockDependent from imports
 *
 * Supported languages: Python, JavaScript, TypeScript, Go, Rust
 *
 * Usage:
 *   bun .claude/skills/speckit/scripts/add-test-tags-universal.ts [--write] [--dry-run] [--lang <language>]
 *
 * Options:
 *   --write       Write changes to files
 *   --dry-run     Show what would be changed without writing (default)
 *   --lang <name> Only process specific language (python, javascript, go, rust)
 *   --help        Show this help message
 */

import { Parser, Language } from 'web-tree-sitter';
import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';
import { PythonAdapter } from './language-adapters/python.js';
import { JavaScriptAdapter } from './language-adapters/javascript.js';
import { GoAdapter } from './language-adapters/go.js';
import { RustAdapter } from './language-adapters/rust.js';
import type { LanguageAdapter, InferredMetadata } from './language-adapters/base.js';

// Parse command line arguments
const args = process.argv.slice(2);
const WRITE_MODE = args.includes('--write');
const DRY_RUN = args.includes('--dry-run') || !WRITE_MODE;
const SHOW_HELP = args.includes('--help') || args.includes('-h');
const langIndex = args.indexOf('--lang');
const SPECIFIC_LANG = langIndex >= 0 ? args[langIndex + 1] : null;

if (SHOW_HELP) {
  console.log(`
Universal Auto-Tagging Script for Test Metadata Migration

Supported Languages: Python, JavaScript, TypeScript, Go, Rust

Usage:
  bun .claude/skills/speckit/scripts/add-test-tags-universal.ts [options]

Options:
  --write        Write changes to files
  --dry-run      Show what would be changed without writing (default)
  --lang <name>  Only process specific language (python, javascript, go, rust)
  --help, -h     Show this help message

Examples:
  # Dry run (show changes for all languages)
  bun .claude/skills/speckit/scripts/add-test-tags-universal.ts

  # Write changes to all Python files
  bun .claude/skills/speckit/scripts/add-test-tags-universal.ts --write --lang python

  # Write changes to all files
  bun .claude/skills/speckit/scripts/add-test-tags-universal.ts --write
`);
  process.exit(0);
}

// Find repo root
function findRepoRoot(): string {
  let dir = process.cwd();
  while (dir !== path.parse(dir).root) {
    if (fs.existsSync(path.join(dir, 'package.json')) ||
        fs.existsSync(path.join(dir, '.git'))) {
      return dir;
    }
    dir = path.dirname(dir);
  }
  return process.cwd();
}

const REPO_ROOT = findRepoRoot();

// Initialize language adapters
const adapters: LanguageAdapter[] = [
  new PythonAdapter(),
  new JavaScriptAdapter(),
  new GoAdapter(),
  new RustAdapter()
];

// Filter by specific language if requested
const activeAdapters = SPECIFIC_LANG
  ? adapters.filter(a => a.getLanguage() === SPECIFIC_LANG)
  : adapters;

if (activeAdapters.length === 0) {
  console.error(`Error: Unknown language "${SPECIFIC_LANG}"`);
  console.error(`Available: ${adapters.map(a => a.getLanguage()).join(', ')}`);
  process.exit(1);
}

/**
 * Process a single test file with the appropriate language adapter
 */
async function processTestFile(
  filePath: string,
  adapter: LanguageAdapter,
  parser: Parser
): Promise<{ modified: boolean; changes: string[] }> {
  const content = fs.readFileSync(filePath, 'utf-8');

  // Parse the file
  const tree = parser.parse(content);

  if (!tree) {
    throw new Error('Failed to parse file');
  }

  // Find all test nodes
  const testLocations = adapter.findTestNodes(tree, content);

  if (testLocations.length === 0) {
    return { modified: false, changes: [] };
  }

  // Infer file-level metadata
  const spec = adapter.inferSpecNumber(filePath);
  const testType = adapter.inferTestType(filePath);
  const userStories = adapter.extractUserStories(content);
  const functionalReqs = adapter.extractFunctionalReqs(content);
  const mockDependent = adapter.isMockDependent(content);

  const fileLevelMetadata: InferredMetadata = {
    spec,
    userStories,
    functionalReqs,
    testType,
    mockDependent
  };

  // Check which tests need tags
  const testsNeedingTags = testLocations.filter(location => {
    const comment = adapter.extractCommentForNode(location.node, content);
    const tags = adapter.extractTags(comment);
    // If no @spec tag, needs tagging
    return !tags.spec;
  });

  if (testsNeedingTags.length === 0) {
    return { modified: false, changes: [] };
  }

  // Sort by line number (descending) so we can insert from bottom to top
  testsNeedingTags.sort((a, b) => b.line - a.line);

  let modifiedContent = content;
  const changes: string[] = [];

  for (const location of testsNeedingTags) {
    const { line, testName, node } = location;
    const lines = modifiedContent.split('\n');

    // Get indentation from the current line
    const currentLine = lines[line - 1];
    const indent = currentLine.match(/^\s*/)?.[0] || '';

    // Generate metadata comment
    const metadataComment = adapter.generateMetadataComment(fileLevelMetadata, indent);

    // Insert comment before the test line
    lines.splice(line - 1, 0, metadataComment);
    modifiedContent = lines.join('\n');

    changes.push(`  Line ${line}: Added metadata to ${testName}`);
  }

  if (WRITE_MODE) {
    fs.writeFileSync(filePath, modifiedContent, 'utf-8');
  }

  return { modified: true, changes };
}

/**
 * Main execution
 */
async function main() {
  console.log(`\nUniversal Auto-Tagging Script`);
  console.log(`============================\n`);
  console.log(`Mode: ${WRITE_MODE ? 'WRITE' : 'DRY RUN'}`);
  console.log(`Languages: ${activeAdapters.map(a => a.getLanguage()).join(', ')}\n`);

  // Initialize tree-sitter WASM
  await Parser.init();

  let totalFiles = 0;
  let modifiedCount = 0;
  let totalChanges = 0;

  // Process each language
  for (const adapter of activeAdapters) {
    console.log(`\nProcessing ${adapter.getLanguage()} files...`);
    console.log(`${'='.repeat(40)}\n`);

    // Create parser for this language
    const parser = new Parser();
    const wasmPath = await adapter.getTreeSitterLanguage();
    const language = await Language.load(wasmPath);
    parser.setLanguage(language);

    // Build glob patterns for this language's extensions
    const patterns = adapter.getExtensions().map(ext => {
      // Handle different test file naming conventions
      if (ext === '.py') {
        return [`**/*test${ext}`, `**/test_*${ext}`];
      } else if (ext === '.go') {
        return [`**/*_test${ext}`];
      } else if (ext === '.rs') {
        return [`**/tests/**/*${ext}`, `**/*_test${ext}`];
      } else {
        return [`**/*.{test,spec}${ext}`];
      }
    }).flat();

    // Find test files
    const testFiles: string[] = [];
    for (const pattern of patterns) {
      const files = await glob(pattern, {
        cwd: REPO_ROOT,
        ignore: ['node_modules/**', 'dist/**', 'build/**', 'target/**', '.venv/**'],
        absolute: true
      });
      testFiles.push(...files);
    }

    // Remove duplicates
    const uniqueFiles = [...new Set(testFiles)];

    console.log(`Found ${uniqueFiles.length} test files\n`);
    totalFiles += uniqueFiles.length;

    // Process each file
    for (const file of uniqueFiles) {
      const relativePath = path.relative(REPO_ROOT, file);

      try {
        const { modified, changes } = await processTestFile(file, adapter, parser);

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
  }

  console.log(`\nSummary`);
  console.log(`=======`);
  console.log(`Files processed: ${totalFiles}`);
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
