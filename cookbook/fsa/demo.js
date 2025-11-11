/**
 * FSA-1.2 Code Template Library - Demo Script
 * Demonstrates all features and template usage
 */

const { CodeTemplateLibrary } = require('./fsa_1_2_template_library.js');

console.log('='.repeat(80));
console.log('FSA-1.2 CODE TEMPLATE LIBRARY - DEMONSTRATION');
console.log('='.repeat(80));
console.log();

// Initialize the library
const library = new CodeTemplateLibrary();

// 1. List all available templates
console.log('1. AVAILABLE TEMPLATES');
console.log('-'.repeat(80));
const allTemplates = library.listTemplates();
allTemplates.forEach(t => {
  console.log(`  [${t.category.toUpperCase()}] ${t.name}`);
  console.log(`    Description: ${t.description}`);
  console.log(`    Language: ${t.language} | Framework: ${t.framework}`);
  console.log(`    Variables: ${t.hasVariables ? 'Yes' : 'No'}`);
  console.log();
});

// 2. Get categories
console.log('2. TEMPLATE CATEGORIES');
console.log('-'.repeat(80));
const categories = library.getCategories();
console.log(`  Available categories: ${categories.join(', ')}`);
console.log();

// 3. Demonstrate API Endpoint template with custom variables
console.log('3. API ENDPOINT TEMPLATE (Customized)');
console.log('-'.repeat(80));
const apiTemplate = library.getTemplate('api', 'api-endpoint', {
  METHOD: 'GET',
  METHOD_LOWER: 'get',
  RESOURCE: 'products',
  ACCESS_LEVEL: 'Public',
  PARAMS: 'category, limit',
  PARAM_SOURCE: 'query',
  SERVICE_NAME: 'ProductService',
  ACTION: 'findProducts',
  SUCCESS_CODE: '200'
});

if (apiTemplate) {
  console.log(`  Template: ${apiTemplate.name}`);
  console.log(`  Customized: ${apiTemplate.metadata.customized}`);
  console.log(`  Code preview (first 20 lines):`);
  const lines = apiTemplate.code.split('\n').slice(0, 20);
  lines.forEach(line => console.log(`    ${line}`));
  console.log('    ...');
}
console.log();

// 4. Demonstrate Data Pipeline template
console.log('4. DATA PIPELINE TEMPLATE');
console.log('-'.repeat(80));
const pipelineTemplate = library.getTemplate('data', 'data-pipeline');
if (pipelineTemplate) {
  console.log(`  Template: ${pipelineTemplate.name}`);
  console.log(`  Description: ${pipelineTemplate.description}`);
  console.log(`  Total lines: ${pipelineTemplate.code.split('\n').length}`);
  console.log(`  Features: ETL pattern, batch processing, retry logic, error handling`);
}
console.log();

// 5. Demonstrate Authentication Middleware template
console.log('5. AUTHENTICATION MIDDLEWARE TEMPLATE');
console.log('-'.repeat(80));
const authTemplate = library.getTemplate('security', 'auth-middleware');
if (authTemplate) {
  console.log(`  Template: ${authTemplate.name}`);
  console.log(`  Description: ${authTemplate.description}`);
  console.log(`  Features: JWT verification, role-based access, token generation`);
}
console.log();

// 6. Demonstrate Database Query template
console.log('6. DATABASE QUERY TEMPLATE');
console.log('-'.repeat(80));
const dbTemplate = library.getTemplate('database', 'database-query');
if (dbTemplate) {
  console.log(`  Template: ${dbTemplate.name}`);
  console.log(`  Description: ${dbTemplate.description}`);
  console.log(`  Features: CRUD operations, transactions, connection pooling`);
}
console.log();

// 7. Demonstrate Error Handler template
console.log('7. ERROR HANDLER TEMPLATE');
console.log('-'.repeat(80));
const errorTemplate = library.getTemplate('middleware', 'error-handler');
if (errorTemplate) {
  console.log(`  Template: ${errorTemplate.name}`);
  console.log(`  Description: ${errorTemplate.description}`);
  console.log(`  Features: Custom errors, logging, sanitization, async handling`);
}
console.log();

// 8. Add a custom template
console.log('8. ADD CUSTOM TEMPLATE');
console.log('-'.repeat(80));
const customAdded = library.addTemplate('custom-logger', {
  category: 'utils',
  name: 'custom-logger',
  description: 'Simple logging utility',
  code: `
const logger = {
  info: (msg) => console.log(\`[INFO] \${new Date().toISOString()}: \${msg}\`),
  error: (msg) => console.error(\`[ERROR] \${new Date().toISOString()}: \${msg}\`)
};
module.exports = logger;
  `,
  variables: {}
});
console.log(`  Custom template added: ${customAdded}`);
console.log(`  Total templates now: ${library.listTemplates().length}`);
console.log();

// 9. FSA-1.1 Integration: Optimize a template
console.log('9. FSA-1.1 INTEGRATION: TEMPLATE OPTIMIZATION');
console.log('-'.repeat(80));
const optimization = library.optimizeTemplate('api-endpoint', {
  authentication: 'JWT',
  database: 'PostgreSQL',
  patterns: ['REST', 'MVC']
});

console.log(`  Template: ${optimization.template}`);
console.log(`  Analysis:`);
console.log(`    Complexity Score: ${optimization.analysis.complexity.toFixed(2)}`);
console.log(`    Detected Patterns: ${optimization.analysis.patterns.join(', ')}`);
console.log(`    Metrics:`);
console.log(`      Lines: ${optimization.analysis.metrics.lines}`);
console.log(`      Functions: ${optimization.analysis.metrics.functions}`);
console.log(`      Classes: ${optimization.analysis.metrics.classes}`);
console.log(`  Suggestions:`);
optimization.analysis.suggestions.forEach(s => console.log(`    - ${s}`));
console.log(`  Recommendations:`);
optimization.recommendations.forEach(r => console.log(`    - ${r}`));
console.log();

// 10. Filter templates by category
console.log('10. FILTER BY CATEGORY');
console.log('-'.repeat(80));
categories.forEach(cat => {
  const filtered = library.listTemplates(cat);
  console.log(`  ${cat}: ${filtered.length} template(s)`);
});
console.log();

// Summary
console.log('='.repeat(80));
console.log('SUMMARY');
console.log('='.repeat(80));
console.log(`  Total Templates: ${allTemplates.length}`);
console.log(`  Categories: ${categories.length}`);
console.log(`  Features:`);
console.log(`    - Production-ready code templates`);
console.log(`    - Variable substitution`);
console.log(`    - FSA-1.1 integration (prompt optimization)`);
console.log(`    - Template analysis and recommendations`);
console.log(`    - Custom template support`);
console.log(`    - Category-based organization`);
console.log('='.repeat(80));
console.log('Demo completed successfully!');
console.log('='.repeat(80));
