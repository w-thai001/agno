/**
 * FSA-1.2: Code Template Library
 *
 * Production-ready JavaScript code templates for common development patterns.
 * Integrates with FSA-1.1 for intelligent template customization.
 *
 * @module FSA-1.2
 * @version 1.0.0
 */

const { PromptOptimizer } = require('./fsa_1_1_prompt_optimizer.js');

/**
 * Core code template library with production-ready templates
 */
class CodeTemplateLibrary {
  /**
   * Initialize the template library with built-in templates
   * @constructor
   */
  constructor() {
    this.templates = new Map();
    this.promptOptimizer = new PromptOptimizer();
    this._initializeTemplates();
  }

  /**
   * Initialize built-in production templates
   * @private
   */
  _initializeTemplates() {
    // 1. API Endpoint Template
    this.templates.set('api-endpoint', {
      category: 'api',
      name: 'api-endpoint',
      description: 'RESTful API endpoint with validation and error handling',
      language: 'javascript',
      framework: 'express',
      code: `/**
 * RESTful API Endpoint Template
 * Handles HTTP requests with validation and error handling
 */

const express = require('express');
const router = express.Router();

/**
 * {{METHOD}} {{RESOURCE}}
 * @route {{METHOD}} /api/{{RESOURCE}}
 * @access {{ACCESS_LEVEL}}
 */
router.{{METHOD_LOWER}}('/{{RESOURCE}}', async (req, res) => {
  try {
    // Input validation
    const { {{PARAMS}} } = req.{{PARAM_SOURCE}};

    if (!{{PARAMS}}) {
      return res.status(400).json({
        success: false,
        error: 'Missing required parameters'
      });
    }

    // Business logic
    const result = await {{SERVICE_NAME}}.{{ACTION}}({{PARAMS}});

    // Success response
    res.status({{SUCCESS_CODE}}).json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('API Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

module.exports = router;`,
      variables: {
        METHOD: 'POST',
        METHOD_LOWER: 'post',
        RESOURCE: 'users',
        ACCESS_LEVEL: 'Public',
        PARAMS: 'username, email',
        PARAM_SOURCE: 'body',
        SERVICE_NAME: 'UserService',
        ACTION: 'createUser',
        SUCCESS_CODE: '201'
      }
    });

    // 2. Data Pipeline Template
    this.templates.set('data-pipeline', {
      category: 'data',
      name: 'data-pipeline',
      description: 'ETL data pipeline with transformation and error handling',
      language: 'javascript',
      framework: 'node',
      code: `/**
 * Data Pipeline Template
 * Extract, Transform, Load pattern with error handling
 */

class DataPipeline {
  constructor(config = {}) {
    this.config = {
      batchSize: config.batchSize || 100,
      retryAttempts: config.retryAttempts || 3,
      ...config
    };
    this.stats = {
      processed: 0,
      failed: 0,
      startTime: null
    };
  }

  /**
   * Execute the full pipeline
   * @param {Array} data - Input data to process
   * @returns {Promise<Object>} Pipeline results
   */
  async execute(data) {
    this.stats.startTime = Date.now();
    console.log(\`Starting pipeline with \${data.length} records\`);

    try {
      // Extract
      const extracted = await this.extract(data);
      console.log(\`Extracted: \${extracted.length} records\`);

      // Transform
      const transformed = await this.transform(extracted);
      console.log(\`Transformed: \${transformed.length} records\`);

      // Load
      const loaded = await this.load(transformed);
      console.log(\`Loaded: \${loaded} records\`);

      return this._generateReport(true);

    } catch (error) {
      console.error('Pipeline error:', error);
      return this._generateReport(false, error);
    }
  }

  /**
   * Extract data from source
   * @param {Array} data - Raw input data
   * @returns {Promise<Array>} Extracted data
   */
  async extract(data) {
    return data.filter(item => item !== null && item !== undefined);
  }

  /**
   * Transform data according to business rules
   * @param {Array} data - Extracted data
   * @returns {Promise<Array>} Transformed data
   */
  async transform(data) {
    return data.map(item => {
      // Apply transformations
      return {
        ...item,
        processed: true,
        timestamp: new Date().toISOString()
      };
    });
  }

  /**
   * Load data to destination
   * @param {Array} data - Transformed data
   * @returns {Promise<number>} Number of records loaded
   */
  async load(data) {
    const batches = this._createBatches(data, this.config.batchSize);

    for (const batch of batches) {
      await this._loadBatch(batch);
      this.stats.processed += batch.length;
    }

    return this.stats.processed;
  }

  /**
   * Load a single batch with retry logic
   * @private
   */
  async _loadBatch(batch) {
    let attempts = 0;

    while (attempts < this.config.retryAttempts) {
      try {
        // Simulate data loading
        await new Promise(resolve => setTimeout(resolve, 10));
        return;
      } catch (error) {
        attempts++;
        if (attempts >= this.config.retryAttempts) {
          this.stats.failed += batch.length;
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, 1000 * attempts));
      }
    }
  }

  /**
   * Create batches from data array
   * @private
   */
  _createBatches(data, size) {
    const batches = [];
    for (let i = 0; i < data.length; i += size) {
      batches.push(data.slice(i, i + size));
    }
    return batches;
  }

  /**
   * Generate pipeline execution report
   * @private
   */
  _generateReport(success, error = null) {
    return {
      success,
      stats: {
        ...this.stats,
        duration: Date.now() - this.stats.startTime,
        successRate: this.stats.processed / (this.stats.processed + this.stats.failed)
      },
      error: error ? error.message : null
    };
  }
}

module.exports = { DataPipeline };`,
      variables: {}
    });

    // 3. Authentication Middleware Template
    this.templates.set('auth-middleware', {
      category: 'security',
      name: 'auth-middleware',
      description: 'JWT authentication middleware with role-based access',
      language: 'javascript',
      framework: 'express',
      code: `/**
 * Authentication Middleware Template
 * JWT-based authentication with role validation
 */

const jwt = require('jsonwebtoken');

/**
 * Authentication middleware factory
 * @param {Object} options - Configuration options
 * @returns {Function} Express middleware function
 */
function createAuthMiddleware(options = {}) {
  const {
    secret = process.env.JWT_SECRET,
    tokenHeader = 'authorization',
    tokenPrefix = 'Bearer',
    allowedRoles = []
  } = options;

  return async function authMiddleware(req, res, next) {
    try {
      // Extract token from header
      const authHeader = req.headers[tokenHeader.toLowerCase()];

      if (!authHeader) {
        return res.status(401).json({
          success: false,
          error: 'No authentication token provided'
        });
      }

      // Parse token
      const token = authHeader.startsWith(tokenPrefix)
        ? authHeader.slice(tokenPrefix.length + 1)
        : authHeader;

      // Verify token
      const decoded = jwt.verify(token, secret);

      // Check token expiration
      if (decoded.exp && Date.now() >= decoded.exp * 1000) {
        return res.status(401).json({
          success: false,
          error: 'Token has expired'
        });
      }

      // Role-based access control
      if (allowedRoles.length > 0 && !allowedRoles.includes(decoded.role)) {
        return res.status(403).json({
          success: false,
          error: 'Insufficient permissions'
        });
      }

      // Attach user to request
      req.user = {
        id: decoded.userId,
        email: decoded.email,
        role: decoded.role
      };

      next();

    } catch (error) {
      if (error.name === 'JsonWebTokenError') {
        return res.status(401).json({
          success: false,
          error: 'Invalid token'
        });
      }

      console.error('Auth middleware error:', error);
      return res.status(500).json({
        success: false,
        error: 'Authentication failed'
      });
    }
  };
}

/**
 * Generate JWT token
 * @param {Object} payload - Token payload
 * @param {string} secret - JWT secret
 * @param {string} expiresIn - Token expiration
 * @returns {string} JWT token
 */
function generateToken(payload, secret, expiresIn = '24h') {
  return jwt.sign(payload, secret, { expiresIn });
}

module.exports = { createAuthMiddleware, generateToken };`,
      variables: {}
    });

    // 4. Database Query Template
    this.templates.set('database-query', {
      category: 'database',
      name: 'database-query',
      description: 'Database query handler with connection pooling and transactions',
      language: 'javascript',
      framework: 'node',
      code: `/**
 * Database Query Template
 * Handles database operations with connection pooling and transactions
 */

class DatabaseQuery {
  constructor(pool) {
    this.pool = pool;
  }

  /**
   * Execute a SELECT query
   * @param {string} table - Table name
   * @param {Object} conditions - Where conditions
   * @param {Object} options - Query options
   * @returns {Promise<Array>} Query results
   */
  async select(table, conditions = {}, options = {}) {
    const {
      columns = ['*'],
      orderBy = null,
      limit = null,
      offset = null
    } = options;

    try {
      let query = \`SELECT \${columns.join(', ')} FROM \${table}\`;
      const params = [];
      let paramIndex = 1;

      // WHERE clause
      if (Object.keys(conditions).length > 0) {
        const whereClauses = Object.keys(conditions).map(key => {
          params.push(conditions[key]);
          return \`\${key} = $\${paramIndex++}\`;
        });
        query += \` WHERE \${whereClauses.join(' AND ')}\`;
      }

      // ORDER BY
      if (orderBy) {
        query += \` ORDER BY \${orderBy}\`;
      }

      // LIMIT and OFFSET
      if (limit) {
        query += \` LIMIT $\${paramIndex++}\`;
        params.push(limit);
      }
      if (offset) {
        query += \` OFFSET $\${paramIndex++}\`;
        params.push(offset);
      }

      const result = await this.pool.query(query, params);
      return result.rows;

    } catch (error) {
      console.error('SELECT query error:', error);
      throw new Error(\`Failed to select from \${table}: \${error.message}\`);
    }
  }

  /**
   * Execute an INSERT query
   * @param {string} table - Table name
   * @param {Object} data - Data to insert
   * @returns {Promise<Object>} Inserted record
   */
  async insert(table, data) {
    try {
      const columns = Object.keys(data);
      const values = Object.values(data);
      const placeholders = values.map((_, i) => \`$\${i + 1}\`).join(', ');

      const query = \`
        INSERT INTO \${table} (\${columns.join(', ')})
        VALUES (\${placeholders})
        RETURNING *
      \`;

      const result = await this.pool.query(query, values);
      return result.rows[0];

    } catch (error) {
      console.error('INSERT query error:', error);
      throw new Error(\`Failed to insert into \${table}: \${error.message}\`);
    }
  }

  /**
   * Execute an UPDATE query
   * @param {string} table - Table name
   * @param {Object} data - Data to update
   * @param {Object} conditions - Where conditions
   * @returns {Promise<number>} Number of affected rows
   */
  async update(table, data, conditions) {
    try {
      const setColumns = Object.keys(data);
      const setValues = Object.values(data);
      let paramIndex = 1;

      const setClauses = setColumns.map(col =>
        \`\${col} = $\${paramIndex++}\`
      ).join(', ');

      const whereColumns = Object.keys(conditions);
      const whereValues = Object.values(conditions);
      const whereClauses = whereColumns.map(col =>
        \`\${col} = $\${paramIndex++}\`
      ).join(' AND ');

      const query = \`
        UPDATE \${table}
        SET \${setClauses}
        WHERE \${whereClauses}
      \`;

      const result = await this.pool.query(query, [...setValues, ...whereValues]);
      return result.rowCount;

    } catch (error) {
      console.error('UPDATE query error:', error);
      throw new Error(\`Failed to update \${table}: \${error.message}\`);
    }
  }

  /**
   * Execute a DELETE query
   * @param {string} table - Table name
   * @param {Object} conditions - Where conditions
   * @returns {Promise<number>} Number of deleted rows
   */
  async delete(table, conditions) {
    try {
      const columns = Object.keys(conditions);
      const values = Object.values(conditions);
      const whereClauses = columns.map((col, i) =>
        \`\${col} = $\${i + 1}\`
      ).join(' AND ');

      const query = \`DELETE FROM \${table} WHERE \${whereClauses}\`;
      const result = await this.pool.query(query, values);
      return result.rowCount;

    } catch (error) {
      console.error('DELETE query error:', error);
      throw new Error(\`Failed to delete from \${table}: \${error.message}\`);
    }
  }

  /**
   * Execute a transaction
   * @param {Function} callback - Transaction callback
   * @returns {Promise<any>} Transaction result
   */
  async transaction(callback) {
    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;

    } catch (error) {
      await client.query('ROLLBACK');
      console.error('Transaction error:', error);
      throw error;

    } finally {
      client.release();
    }
  }
}

module.exports = { DatabaseQuery };`,
      variables: {}
    });

    // 5. Error Handler Template
    this.templates.set('error-handler', {
      category: 'middleware',
      name: 'error-handler',
      description: 'Centralized error handling middleware with logging',
      language: 'javascript',
      framework: 'express',
      code: `/**
 * Error Handler Template
 * Centralized error handling with logging and response formatting
 */

/**
 * Custom error class for application errors
 */
class AppError extends Error {
  constructor(message, statusCode = 500, code = 'INTERNAL_ERROR') {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Error types for common scenarios
 */
const ErrorTypes = {
  ValidationError: (message) => new AppError(message, 400, 'VALIDATION_ERROR'),
  NotFoundError: (resource) => new AppError(\`\${resource} not found\`, 404, 'NOT_FOUND'),
  UnauthorizedError: (message) => new AppError(message || 'Unauthorized', 401, 'UNAUTHORIZED'),
  ForbiddenError: (message) => new AppError(message || 'Forbidden', 403, 'FORBIDDEN'),
  ConflictError: (message) => new AppError(message, 409, 'CONFLICT'),
  RateLimitError: () => new AppError('Too many requests', 429, 'RATE_LIMIT_EXCEEDED')
};

/**
 * Global error handler middleware
 * @param {Error} err - Error object
 * @param {Object} req - Express request
 * @param {Object} res - Express response
 * @param {Function} next - Next middleware
 */
function errorHandler(err, req, res, next) {
  // Log error
  logError(err, req);

  // Handle operational errors
  if (err.isOperational) {
    return res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.code,
        message: err.message
      }
    });
  }

  // Handle programming or unknown errors
  console.error('CRITICAL ERROR:', err);

  // Don't leak error details in production
  const message = process.env.NODE_ENV === 'production'
    ? 'An unexpected error occurred'
    : err.message;

  res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_ERROR',
      message
    }
  });
}

/**
 * Log error with context
 * @param {Error} err - Error object
 * @param {Object} req - Express request
 */
function logError(err, req) {
  const errorLog = {
    timestamp: new Date().toISOString(),
    error: {
      name: err.name,
      message: err.message,
      code: err.code,
      stack: err.stack
    },
    request: {
      method: req.method,
      url: req.url,
      params: req.params,
      query: req.query,
      body: sanitizeBody(req.body),
      ip: req.ip,
      userAgent: req.get('user-agent')
    }
  };

  console.error('Error Log:', JSON.stringify(errorLog, null, 2));
}

/**
 * Sanitize request body for logging (remove sensitive data)
 * @param {Object} body - Request body
 * @returns {Object} Sanitized body
 */
function sanitizeBody(body) {
  if (!body || typeof body !== 'object') return body;

  const sanitized = { ...body };
  const sensitiveFields = ['password', 'token', 'secret', 'apiKey', 'creditCard'];

  for (const field of sensitiveFields) {
    if (sanitized[field]) {
      sanitized[field] = '***REDACTED***';
    }
  }

  return sanitized;
}

/**
 * 404 handler for undefined routes
 */
function notFoundHandler(req, res, next) {
  const error = ErrorTypes.NotFoundError(\`Route \${req.originalUrl}\`);
  next(error);
}

/**
 * Async handler wrapper to catch promise rejections
 * @param {Function} fn - Async route handler
 * @returns {Function} Wrapped handler
 */
function asyncHandler(fn) {
  return (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

module.exports = {
  AppError,
  ErrorTypes,
  errorHandler,
  notFoundHandler,
  asyncHandler
};`,
      variables: {}
    });
  }

  /**
   * Get a template by category and name
   *
   * @param {string} category - Template category
   * @param {string} name - Template name
   * @param {Object} customVars - Custom variables to override defaults
   * @returns {Object|null} Template object with populated variables
   *
   * @example
   * const lib = new CodeTemplateLibrary();
   * const template = lib.getTemplate('api', 'api-endpoint', {
   *   METHOD: 'GET',
   *   RESOURCE: 'products'
   * });
   */
  getTemplate(category, name, customVars = {}) {
    const templateKey = name || `${category}`;
    const template = this.templates.get(templateKey);

    if (!template) {
      console.warn(`Template not found: ${templateKey}`);
      return null;
    }

    // Merge custom variables with defaults
    const variables = { ...template.variables, ...customVars };

    // Replace variables in template code
    let code = template.code;
    for (const [key, value] of Object.entries(variables)) {
      const regex = new RegExp(`{{${key}}}`, 'g');
      code = code.replace(regex, value);
    }

    return {
      ...template,
      code,
      variables,
      metadata: {
        retrieved: new Date().toISOString(),
        customized: Object.keys(customVars).length > 0
      }
    };
  }

  /**
   * Add a custom template to the library
   *
   * @param {string} key - Unique template key
   * @param {Object} template - Template object
   * @returns {boolean} Success status
   *
   * @example
   * lib.addTemplate('my-template', {
   *   category: 'custom',
   *   name: 'my-template',
   *   description: 'My custom template',
   *   code: 'console.log("Hello");',
   *   variables: {}
   * });
   */
  addTemplate(key, template) {
    if (!key || !template) {
      console.error('Invalid template: key and template object required');
      return false;
    }

    if (!template.code) {
      console.error('Invalid template: code property required');
      return false;
    }

    const fullTemplate = {
      category: template.category || 'custom',
      name: template.name || key,
      description: template.description || '',
      language: template.language || 'javascript',
      framework: template.framework || 'node',
      code: template.code,
      variables: template.variables || {},
      created: new Date().toISOString()
    };

    this.templates.set(key, fullTemplate);
    console.log(`Template added: ${key}`);
    return true;
  }

  /**
   * List all available templates
   *
   * @param {string} filterCategory - Optional category filter
   * @returns {Array} Array of template metadata
   *
   * @example
   * const lib = new CodeTemplateLibrary();
   * const allTemplates = lib.listTemplates();
   * const apiTemplates = lib.listTemplates('api');
   */
  listTemplates(filterCategory = null) {
    const templates = [];

    for (const [key, template] of this.templates.entries()) {
      if (!filterCategory || template.category === filterCategory) {
        templates.push({
          key,
          category: template.category,
          name: template.name,
          description: template.description,
          language: template.language,
          framework: template.framework,
          hasVariables: Object.keys(template.variables).length > 0
        });
      }
    }

    return templates;
  }

  /**
   * Get all available categories
   *
   * @returns {Array} Array of unique categories
   */
  getCategories() {
    const categories = new Set();
    for (const template of this.templates.values()) {
      categories.add(template.category);
    }
    return Array.from(categories).sort();
  }

  /**
   * Optimize template with FSA-1.1 integration
   *
   * @param {string} templateKey - Template key
   * @param {Object} context - Optimization context
   * @returns {Object} Optimized template analysis
   */
  optimizeTemplate(templateKey, context = {}) {
    const template = this.templates.get(templateKey);

    if (!template) {
      return { error: 'Template not found' };
    }

    // Use FSA-1.1 to analyze template
    const analysis = this.promptOptimizer.analyzeTemplate(template.code);

    // Generate optimization suggestions
    const optimizationResult = this.promptOptimizer.optimizePrompt(
      template.description,
      {
        strategies: ['clarity', 'specificity', 'context'],
        context: {
          language: template.language,
          framework: template.framework,
          ...context
        }
      }
    );

    return {
      template: template.name,
      analysis,
      optimization: optimizationResult,
      recommendations: this._generateRecommendations(template, analysis)
    };
  }

  /**
   * Generate recommendations based on template analysis
   * @private
   */
  _generateRecommendations(template, analysis) {
    const recommendations = [];

    if (analysis.patterns.includes('async-await')) {
      recommendations.push('Template uses modern async/await patterns');
    }

    if (analysis.patterns.includes('error-handling')) {
      recommendations.push('Good error handling detected');
    }

    if (analysis.metrics.lines > 100) {
      recommendations.push('Consider breaking into smaller modules');
    }

    if (!analysis.patterns.includes('error-handling')) {
      recommendations.push('Add comprehensive error handling');
    }

    return recommendations;
  }
}

module.exports = { CodeTemplateLibrary };
