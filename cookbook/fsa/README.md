# FSA Template Library

Production-ready code template system with intelligent prompt optimization.

## Modules

### FSA-1.1: Prompt Optimizer
Intelligent prompt optimization for code generation and template customization.

**Features:**
- Multi-strategy optimization (clarity, specificity, context, constraints)
- Template analysis and complexity scoring
- Pattern detection (async/await, promises, OOP, error handling)
- Optimization history tracking

### FSA-1.2: Code Template Library
Comprehensive library of production-ready code templates with FSA-1.1 integration.

**Features:**
- 5 core production templates
- Variable substitution system
- Template optimization and analysis
- Category-based organization
- Custom template support

## Templates

### 1. API Endpoint
**Category:** api
**Framework:** Express.js
**Features:** Request validation, error handling, RESTful patterns

### 2. Data Pipeline
**Category:** data
**Framework:** Node.js
**Features:** ETL pattern, batch processing, retry logic, error recovery

### 3. Authentication Middleware
**Category:** security
**Framework:** Express.js
**Features:** JWT verification, role-based access control, token generation

### 4. Database Query
**Category:** database
**Framework:** Node.js
**Features:** CRUD operations, transactions, connection pooling, parameterized queries

### 5. Error Handler
**Category:** middleware
**Framework:** Express.js
**Features:** Centralized error handling, custom error types, logging, sanitization

## Installation

```bash
cd cookbook/fsa
npm init -y
npm install express jsonwebtoken
```

## Usage

### Basic Template Retrieval

```javascript
const { CodeTemplateLibrary } = require('./fsa_1_2_template_library.js');

const library = new CodeTemplateLibrary();

// Get template with default variables
const template = library.getTemplate('api', 'api-endpoint');

// Get template with custom variables
const customTemplate = library.getTemplate('api', 'api-endpoint', {
  METHOD: 'GET',
  RESOURCE: 'products',
  SERVICE_NAME: 'ProductService'
});

console.log(customTemplate.code);
```

### List Available Templates

```javascript
// List all templates
const allTemplates = library.listTemplates();
allTemplates.forEach(t => {
  console.log(`${t.name}: ${t.description}`);
});

// Filter by category
const apiTemplates = library.listTemplates('api');
```

### Add Custom Template

```javascript
library.addTemplate('my-custom-template', {
  category: 'custom',
  name: 'my-custom-template',
  description: 'Custom utility function',
  language: 'javascript',
  code: `
function myUtility() {
  // Your code here
}
module.exports = myUtility;
  `
});
```

### Template Optimization (FSA-1.1 Integration)

```javascript
const optimization = library.optimizeTemplate('api-endpoint', {
  authentication: 'JWT',
  database: 'PostgreSQL',
  patterns: ['REST', 'MVC']
});

console.log(optimization.analysis);
console.log(optimization.recommendations);
```

### Standalone Prompt Optimization

```javascript
const { PromptOptimizer } = require('./fsa_1_1_prompt_optimizer.js');

const optimizer = new PromptOptimizer();

const result = optimizer.optimizePrompt('create API endpoint', {
  strategies: ['clarity', 'specificity', 'context'],
  context: {
    framework: 'express',
    language: 'javascript',
    authentication: 'JWT'
  }
});

console.log(result.optimized);
```

## Demo

Run the demo to see all features in action:

```bash
node demo.js
```

## API Reference

### CodeTemplateLibrary

#### Methods

**getTemplate(category, name, customVars)**
- Retrieves a template with optional variable customization
- Returns: Template object with populated code

**addTemplate(key, template)**
- Adds a custom template to the library
- Returns: Success boolean

**listTemplates(filterCategory)**
- Lists all templates, optionally filtered by category
- Returns: Array of template metadata

**getCategories()**
- Gets all available template categories
- Returns: Array of category names

**optimizeTemplate(templateKey, context)**
- Analyzes and optimizes a template using FSA-1.1
- Returns: Optimization results with analysis and recommendations

### PromptOptimizer

#### Methods

**optimizePrompt(originalPrompt, options)**
- Optimizes a prompt using specified strategies
- Returns: Optimization result with original and optimized prompts

**analyzeTemplate(templateCode)**
- Analyzes template code for complexity and patterns
- Returns: Analysis results with metrics and suggestions

**getHistory(limit)**
- Retrieves optimization history
- Returns: Array of optimization records

## Template Variables

Templates support variable substitution using `{{VARIABLE_NAME}}` syntax.

Example variables for API endpoint template:
- `{{METHOD}}` - HTTP method (GET, POST, etc.)
- `{{RESOURCE}}` - Resource name (users, products, etc.)
- `{{SERVICE_NAME}}` - Service class name
- `{{ACCESS_LEVEL}}` - Access level (Public, Private, etc.)

## License

MIT
