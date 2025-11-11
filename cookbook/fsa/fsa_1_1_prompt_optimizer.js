/**
 * FSA-1.1: Prompt Optimization Module
 *
 * This module provides intelligent prompt optimization capabilities for code generation
 * and template customization. It analyzes context, optimizes prompts, and enhances
 * code template generation quality.
 *
 * @module FSA-1.1
 * @version 1.0.0
 */

class PromptOptimizer {
  /**
   * Creates a new PromptOptimizer instance
   * @constructor
   */
  constructor() {
    this.optimizationStrategies = {
      clarity: this._enhanceClarity.bind(this),
      specificity: this._enhanceSpecificity.bind(this),
      context: this._addContext.bind(this),
      constraints: this._addConstraints.bind(this)
    };

    this.optimizationHistory = [];
  }

  /**
   * Optimizes a prompt for better code generation results
   *
   * @param {string} originalPrompt - The original prompt to optimize
   * @param {Object} options - Optimization options
   * @param {string[]} options.strategies - Which optimization strategies to apply
   * @param {Object} options.context - Additional context for optimization
   * @returns {Object} Optimized prompt with metadata
   *
   * @example
   * const optimizer = new PromptOptimizer();
   * const result = optimizer.optimizePrompt("create API endpoint", {
   *   strategies: ['clarity', 'specificity'],
   *   context: { framework: 'express', language: 'javascript' }
   * });
   */
  optimizePrompt(originalPrompt, options = {}) {
    const {
      strategies = ['clarity', 'specificity', 'context'],
      context = {}
    } = options;

    let optimizedPrompt = originalPrompt;
    const appliedStrategies = [];

    // Apply each optimization strategy
    for (const strategy of strategies) {
      if (this.optimizationStrategies[strategy]) {
        optimizedPrompt = this.optimizationStrategies[strategy](
          optimizedPrompt,
          context
        );
        appliedStrategies.push(strategy);
      }
    }

    const result = {
      original: originalPrompt,
      optimized: optimizedPrompt,
      appliedStrategies,
      context,
      timestamp: new Date().toISOString()
    };

    this.optimizationHistory.push(result);
    return result;
  }

  /**
   * Enhances prompt clarity by adding structure and explicit requirements
   * @private
   */
  _enhanceClarity(prompt, context) {
    const clarifiers = [
      'Generate production-ready code that',
      'with proper error handling and',
      'following best practices for'
    ];

    return `${clarifiers[0]} ${prompt} ${clarifiers[1]} ${clarifiers[2]} ${context.language || 'the target language'}.`;
  }

  /**
   * Adds specificity to the prompt based on context
   * @private
   */
  _enhanceSpecificity(prompt, context) {
    const specifics = [];

    if (context.framework) {
      specifics.push(`using ${context.framework} framework`);
    }
    if (context.language) {
      specifics.push(`in ${context.language}`);
    }
    if (context.version) {
      specifics.push(`compatible with version ${context.version}`);
    }

    return specifics.length > 0
      ? `${prompt} (${specifics.join(', ')})`
      : prompt;
  }

  /**
   * Adds relevant context to the prompt
   * @private
   */
  _addContext(prompt, context) {
    const contextParts = [];

    if (context.authentication) {
      contextParts.push(`with ${context.authentication} authentication`);
    }
    if (context.database) {
      contextParts.push(`using ${context.database} database`);
    }
    if (context.patterns) {
      contextParts.push(`following ${context.patterns.join(', ')} patterns`);
    }

    return contextParts.length > 0
      ? `${prompt}. ${contextParts.join(', ')}.`
      : prompt;
  }

  /**
   * Adds constraints and requirements to the prompt
   * @private
   */
  _addConstraints(prompt, context) {
    const constraints = [];

    if (context.maxLines) {
      constraints.push(`Keep implementation under ${context.maxLines} lines`);
    }
    if (context.dependencies) {
      constraints.push(`Use only: ${context.dependencies.join(', ')}`);
    }
    if (context.performance) {
      constraints.push(`Optimize for ${context.performance}`);
    }

    return constraints.length > 0
      ? `${prompt}\n\nConstraints: ${constraints.join('. ')}.`
      : prompt;
  }

  /**
   * Analyzes a template and suggests optimizations
   *
   * @param {string} templateCode - The template code to analyze
   * @returns {Object} Analysis results with suggestions
   */
  analyzeTemplate(templateCode) {
    const analysis = {
      complexity: this._calculateComplexity(templateCode),
      patterns: this._detectPatterns(templateCode),
      suggestions: [],
      metrics: {
        lines: templateCode.split('\n').length,
        functions: (templateCode.match(/function\s+\w+/g) || []).length,
        classes: (templateCode.match(/class\s+\w+/g) || []).length
      }
    };

    // Generate suggestions based on analysis
    if (analysis.complexity > 0.7) {
      analysis.suggestions.push('Consider breaking down into smaller functions');
    }
    if (analysis.metrics.lines > 200) {
      analysis.suggestions.push('Template is lengthy, consider modularization');
    }
    if (!templateCode.includes('/**')) {
      analysis.suggestions.push('Add JSDoc documentation');
    }

    return analysis;
  }

  /**
   * Calculates code complexity score (0-1)
   * @private
   */
  _calculateComplexity(code) {
    const indicators = {
      nested: (code.match(/\{[^}]*\{/g) || []).length,
      conditionals: (code.match(/if\s*\(/g) || []).length,
      loops: (code.match(/(for|while)\s*\(/g) || []).length
    };

    const totalComplexity =
      (indicators.nested * 2) +
      (indicators.conditionals * 1.5) +
      (indicators.loops * 1);

    // Normalize to 0-1 scale
    return Math.min(totalComplexity / 50, 1);
  }

  /**
   * Detects common patterns in code
   * @private
   */
  _detectPatterns(code) {
    const patterns = [];

    if (code.includes('async') && code.includes('await')) {
      patterns.push('async-await');
    }
    if (code.includes('Promise')) {
      patterns.push('promises');
    }
    if (code.includes('class') && code.includes('constructor')) {
      patterns.push('oop');
    }
    if (code.includes('try') && code.includes('catch')) {
      patterns.push('error-handling');
    }
    if (code.includes('module.exports') || code.includes('export')) {
      patterns.push('modular');
    }

    return patterns;
  }

  /**
   * Gets optimization history
   *
   * @param {number} limit - Maximum number of records to return
   * @returns {Array} Array of optimization records
   */
  getHistory(limit = 10) {
    return this.optimizationHistory.slice(-limit);
  }

  /**
   * Clears optimization history
   */
  clearHistory() {
    this.optimizationHistory = [];
  }
}

// Export the module
module.exports = { PromptOptimizer };
