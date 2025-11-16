#!/usr/bin/env tsx
/**
 * Strip Test Metadata Tags
 *
 * Removes all metadata docstrings (@spec, @testType, etc.) from test files.
 * Used for clean slate re-tagging during holistic remediation.
 *
 * Usage:
 *   tsx strip-test-tags.ts <file-path>
 *   tsx strip-test-tags.ts --all  # Strip all tests in registry
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * Check if a docstring contains metadata tags
 */
function isMetadataDocstring(docstring: string): boolean {
  const metadataTags = [
    '@spec',
    '@testType',
    '@userStory',
    '@functionalReq',
    '@mockDependent'
  ];

  return metadataTags.some(tag => docstring.includes(tag));
}

/**
 * Strip metadata docstrings from Python source code
 * AGGRESSIVE MODE: Removes ALL docstrings containing metadata tags,
 * regardless of position (handles buggy old tagger output)
 */
function stripPythonMetadata(sourceCode: string): string {
  // Normalize line endings (handle mixed CRLF/LF)
  const normalized = sourceCode.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = normalized.split('\n');
  const result: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Debug specific line
    if (process.env.DEBUG === '1' && i >= 97 && i <= 102) {
      console.log(`Line ${i + 1}: "${line}" | trimmed: "${trimmed}"`);
    }

    // Check if this line starts a docstring (opening """)
    if (trimmed === '"""' || trimmed.startsWith('"""')) {
      // Collect the full docstring
      const startLine = i;
      const indent = line.match(/^\s*/)?.[0] || '';
      const docstringLines: string[] = [line];

      // If it's a one-liner docstring (e.g., """text""")
      if (trimmed.length > 6 && trimmed.endsWith('"""')) {
        const hasMetadata = isMetadataDocstring(trimmed);
        if (process.env.DEBUG === '1' && hasMetadata) {
          console.log(`FOUND METADATA (one-liner) at line ${i + 1}: ${trimmed}`);
        }
        // Check if it contains metadata
        if (!hasMetadata) {
          result.push(line);
        }
        i++;
        continue;
      }

      // Multi-line docstring - collect until closing """
      i++;
      let foundClosing = false;
      while (i < lines.length) {
        docstringLines.push(lines[i]);
        const currentTrimmed = lines[i].trim();

        if (currentTrimmed === '"""' || currentTrimmed.endsWith('"""')) {
          foundClosing = true;
          i++;
          break;
        }
        i++;
      }

      // Check if this docstring contains metadata
      const fullDocstring = docstringLines.join('\n');
      const hasMetadata = isMetadataDocstring(fullDocstring);

      // Debug logging
      if (process.env.DEBUG === '1' && startLine >= 97 && startLine <= 102) {
        console.log(`\n=== DOCSTRING at lines ${startLine + 1}-${i} ===`);
        console.log(`Full docstring (${fullDocstring.length} chars):`);
        console.log(JSON.stringify(fullDocstring));
        console.log(`Has metadata: ${hasMetadata}`);
        console.log(`Contains @spec: ${fullDocstring.includes('@spec')}`);
        console.log(`================================\n`);
      }

      if (hasMetadata) {
        // Metadata docstring - skip it entirely (don't add to result)
        // Also check if there's a blank line after it that should be removed
        if (i < lines.length && lines[i].trim() === '') {
          i++; // Skip trailing blank line
        }
      } else {
        // Not a metadata docstring - keep it
        result.push(...docstringLines);
      }

      continue;
    }

    result.push(line);
    i++;
  }

  return result.join('\n');
}

/**
 * Process a single test file
 */
function processFile(filePath: string): { stripped: boolean; error?: string } {
  try {
    // Only process Python files
    if (!filePath.endsWith('.py')) {
      return { stripped: false, error: 'Not a Python file' };
    }

    const originalContent = fs.readFileSync(filePath, 'utf-8');
    const strippedContent = stripPythonMetadata(originalContent);

    // Check if anything changed
    if (originalContent === strippedContent) {
      return { stripped: false };
    }

    // Write back
    fs.writeFileSync(filePath, strippedContent, 'utf-8');
    return { stripped: true };
  } catch (error) {
    return { stripped: false, error: String(error) };
  }
}

/**
 * Process all tests in registry
 */
function processAllTests(registryPath: string): void {
  const registry = JSON.parse(fs.readFileSync(registryPath, 'utf-8'));

  let totalFiles = 0;
  let strippedFiles = 0;
  let errorFiles = 0;

  console.log('Stripping metadata from all tests in registry...\n');

  // Get unique file paths
  const uniqueFiles = new Set<string>();
  for (const test of registry.tests) {
    uniqueFiles.add(test.file);
  }

  for (const filePath of uniqueFiles) {
    totalFiles++;
    const result = processFile(filePath);

    if (result.error) {
      console.error(`❌ Error processing ${filePath}: ${result.error}`);
      errorFiles++;
    } else if (result.stripped) {
      console.log(`✓ Stripped: ${filePath}`);
      strippedFiles++;
    } else {
      console.log(`  Skipped: ${filePath} (no metadata found)`);
    }
  }

  console.log(`\n${'='.repeat(60)}`);
  console.log(`Total files: ${totalFiles}`);
  console.log(`Stripped: ${strippedFiles}`);
  console.log(`Skipped: ${totalFiles - strippedFiles - errorFiles}`);
  console.log(`Errors: ${errorFiles}`);
}

/**
 * Main entry point
 */
function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.error('Usage:');
    console.error('  tsx strip-test-tags.ts <file-path>');
    console.error('  tsx strip-test-tags.ts --all');
    process.exit(1);
  }

  if (args[0] === '--all') {
    // Find test-registry.json
    const registryPath = path.join(process.cwd(), 'test-registry.json');

    if (!fs.existsSync(registryPath)) {
      console.error(`Error: test-registry.json not found at ${registryPath}`);
      process.exit(1);
    }

    processAllTests(registryPath);
  } else {
    // Process single file
    const filePath = args[0];

    if (!fs.existsSync(filePath)) {
      console.error(`Error: File not found: ${filePath}`);
      process.exit(1);
    }

    const result = processFile(filePath);

    if (result.error) {
      console.error(`Error: ${result.error}`);
      process.exit(1);
    }

    if (result.stripped) {
      console.log(`✓ Stripped metadata from: ${filePath}`);
    } else {
      console.log(`  No metadata found in: ${filePath}`);
    }
  }
}

main();
