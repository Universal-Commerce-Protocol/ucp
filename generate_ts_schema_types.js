/**
 * @fileoverview Generates TypeScript type definitions from JSON Schema files.
 *
 * This script dynamically discovers all JSON schemas in the spec directory
 * and compiles them into TypeScript interfaces using json-schema-to-typescript.
 *
 * @license Apache-2.0
 * @copyright 2026 UCP Authors
 *
 * Usage: node generate_ts_schema_types.js
 *
 * The generated types are written to ./generated/schema-types.ts and should
 * not be modified manually. Instead, modify the source JSON Schema files
 * and regenerate this file.
 */

const fs = require('node:fs');
const path = require('node:path');
const { compile } = require('json-schema-to-typescript');

/** @const {string} Root directory containing source JSON schemas */
const SOURCE_ROOT = path.resolve(__dirname, 'spec');

/** @const {string} Output file path for generated TypeScript definitions */
const OUTPUT_FILE = path.resolve(__dirname, './generated/schema-types.ts');

/** @const {string} Wrapper schema name used during compilation */
const WRAPPER_NAME = 'SCHEMA_WRAPPER';

/**
 * Recursively cleans a JSON object by removing properties that interfere
 * with json-schema-to-typescript compilation.
 *
 * When $ref is present, other properties like title and description are
 * technically ignored in older JSON Schema drafts. We remove them here to
 * prevent json-schema-to-typescript from generating duplicate interface
 * definitions or conflicting JSDoc comments.
 *
 * @param {*} obj - The object to clean (mutates in place)
 * @returns {void}
 */
function cleanSchemaObject(obj) {
  if (typeof obj !== 'object' || obj === null) return;

  // When $ref is present, remove conflicting metadata
  if (obj.$ref) {
    delete obj.description;
    delete obj.title;
  }

  for (const key in obj) {
    cleanSchemaObject(obj[key]);
  }
}

/**
 * Discovers and collects all JSON schema files from the spec directory.
 *
 * @returns {{[key: string]: {$ref: string}}} Object mapping schema names to $ref objects
 */
function discoverSchemas() {
  const properties = {};

  // Add shopping schemas
  const shoppingDir = path.join(SOURCE_ROOT, 'schemas/shopping');
  if (fs.existsSync(shoppingDir)) {
    for (const file of fs.readdirSync(shoppingDir)) {
      if (file.endsWith('.json')) {
        properties[path.basename(file, '.json')] = {
          $ref: path.join(shoppingDir, file)
        };
      }
    }
  }

  // Add handler schemas
  const handlersDir = path.join(SOURCE_ROOT, 'handlers');
  if (fs.existsSync(handlersDir)) {
    for (const handler of fs.readdirSync(handlersDir)) {
      const handlerPath = path.join(handlersDir, handler);
      if (fs.statSync(handlerPath).isDirectory()) {
        for (const file of fs.readdirSync(handlerPath)) {
          if (file.endsWith('.json')) {
            const name = `${handler}_${path.basename(file, '.json')}`.replace(/-/g, '_');
            properties[name] = { $ref: path.join(handlerPath, file) };
          }
        }
      }
    }
  }

  return properties;
}

/**
 * Creates a custom file resolver for json-schema-to-typescript.
 *
 * The resolver handles file:// URLs and performs schema cleaning
 * to remove properties that conflict with TypeScript generation.
 *
 * @returns {{order: number, canRead: boolean, read: function}} Resolver configuration
 */
function createFileResolver() {
  return {
    order: 1,
    canRead: true,
    /**
     * Reads and parses a JSON schema file.
     * @param {{url: string}} file - File reference object
     * @returns {object} Parsed and cleaned JSON schema
     */
    read: (file) => {
      let filePath = file.url;
      if (filePath.startsWith('file://')) {
        try {
          filePath = require('node:url').fileURLToPath(filePath);
        } catch {
          filePath = filePath.replace('file://', '');
        }
      }

      const content = fs.readFileSync(filePath, 'utf8');
      const json = JSON.parse(content);
      cleanSchemaObject(json);
      return json;
    }
  };
}

/**
 * Post-processes generated TypeScript to clean up and standardize output.
 *
 * @param {string} ts - Raw TypeScript output from json-schema-to-typescript
 * @returns {string} Cleaned TypeScript with standardized formatting
 */
function postProcessTypeScript(ts) {
  // Remove the wrapper interface (matches closing brace at start of line)
  const wrapperRegex = new RegExp(
    `export interface ${WRAPPER_NAME}\\s*\\{[\\s\\S]*?\\n\\}\\s*`,
    'g'
  );
  ts = ts.replace(wrapperRegex, '');

  // Convert to declare interface for ambient declarations
  ts = ts.replace(/export interface/g, 'export declare interface');

  // Fix array type formatting for better readability
  // Replace (A | B)[] with Array<A | B>
  ts = ts.replace(/:\s*\(([^)]+)\)\[\]/g, ': Array<$1>');
  // Replace { ... }[] with Array<{ ... }>
  ts = ts.replace(/:\s*(\{[^}]+\})\[\]/g, ': Array<$1>');

  return ts.trim();
}

/**
 * Main entry point - generates TypeScript types from JSON schemas.
 *
 * @async
 * @returns {Promise<void>}
 */
async function generate() {
  // Ensure output directory exists
  if (!fs.existsSync(path.dirname(OUTPUT_FILE))) {
    fs.mkdirSync(path.dirname(OUTPUT_FILE), { recursive: true });
  }

  const properties = discoverSchemas();
  console.log(`Found ${Object.keys(properties).length} schemas. Compiling...`);

  // Create a wrapper schema that references all discovered schemas
  const wrappedSchema = {
    title: WRAPPER_NAME,
    type: 'object',
    properties,
    additionalProperties: false
  };

  try {
    let ts = await compile(wrappedSchema, WRAPPER_NAME, {
      cwd: SOURCE_ROOT,
      $refOptions: {
        resolve: {
          file: createFileResolver()
        }
      },
      bannerComment: `
/* tslint:disable:enforce-comments-on-exported-symbols */
/* eslint-disable */
/* tslint:disable:enforce-name-casing */
/**
 * This file was automatically generated by json-schema-to-typescript.
 * DO NOT MODIFY IT BY HAND. Instead, modify the source JSONSchema file,
 * and run json-schema-to-typescript to regenerate this file.
 *
 * @fileoverview TypeScript type definitions for UCP JSON Schemas.
 * @license Apache-2.0
 * @copyright 2026 UCP Authors
 */
`,
      style: { singleQuote: true, bracketSpacing: true },
      declareExternallyReferenced: true,
      enableConstEnums: false,
      unreachableDefinitions: true,
      strictIndexSignatures: false
    });

    ts = postProcessTypeScript(ts);
    fs.writeFileSync(OUTPUT_FILE, ts);
    console.log(`Success! Types written to ${OUTPUT_FILE}`);
  } catch (err) {
    console.error('Error generating types:', err);
    process.exit(1);
  }
}

generate();
