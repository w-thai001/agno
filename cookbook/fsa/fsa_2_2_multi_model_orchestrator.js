/**
 * FSA-2.2: Multi-Model Orchestrator
 *
 * Intelligent routing system for Claude models with budget optimization,
 * task classification, and performance tracking.
 *
 * @module FSA-2.2
 * @version 1.0.0
 */

/**
 * Multi-Model Orchestrator for optimal Claude model selection
 * Routes tasks to Opus (complex), Sonnet (balanced), or Haiku (fast/cheap)
 */
class MultiModelOrchestrator {
  /**
   * Initialize the orchestrator with model configurations
   * @constructor
   * @param {Object} config - Configuration options
   * @param {number} config.budget - Total budget in dollars
   * @param {string} config.defaultModel - Default model to use
   * @param {Object} config.constraints - Default constraints
   */
  constructor(config = {}) {
    this.config = {
      budget: config.budget || 100.0,
      defaultModel: config.defaultModel || 'sonnet',
      constraints: config.constraints || {},
      enableFallback: config.enableFallback !== false,
      trackPerformance: config.trackPerformance !== false
    };

    // Model characteristics and pricing (per 1M tokens)
    this.models = {
      opus: {
        name: 'claude-opus-4',
        displayName: 'Claude Opus',
        tier: 'premium',
        inputPrice: 15.00,   // $15 per 1M input tokens
        outputPrice: 75.00,  // $75 per 1M output tokens
        capabilities: {
          complexity: 1.0,    // Handles most complex tasks
          reasoning: 1.0,     // Best reasoning capabilities
          speed: 0.6,         // Slower
          costEfficiency: 0.3 // Most expensive
        },
        bestFor: ['complex reasoning', 'code generation', 'analysis', 'research'],
        maxContextWindow: 200000
      },
      sonnet: {
        name: 'claude-sonnet-4',
        displayName: 'Claude Sonnet',
        tier: 'balanced',
        inputPrice: 3.00,    // $3 per 1M input tokens
        outputPrice: 15.00,  // $15 per 1M output tokens
        capabilities: {
          complexity: 0.8,    // Handles most tasks well
          reasoning: 0.85,    // Strong reasoning
          speed: 0.85,        // Fast
          costEfficiency: 0.8 // Good balance
        },
        bestFor: ['general tasks', 'balanced workloads', 'production'],
        maxContextWindow: 200000
      },
      haiku: {
        name: 'claude-haiku-4',
        displayName: 'Claude Haiku',
        tier: 'fast',
        inputPrice: 0.25,    // $0.25 per 1M input tokens
        outputPrice: 1.25,   // $1.25 per 1M output tokens
        capabilities: {
          complexity: 0.5,    // Best for simpler tasks
          reasoning: 0.6,     // Basic reasoning
          speed: 1.0,         // Fastest
          costEfficiency: 1.0 // Most cost-efficient
        },
        bestFor: ['simple tasks', 'classification', 'extraction', 'formatting'],
        maxContextWindow: 200000
      }
    };

    // Budget tracking
    this.budget = {
      total: this.config.budget,
      remaining: this.config.budget,
      spent: 0.0,
      breakdown: {
        opus: 0.0,
        sonnet: 0.0,
        haiku: 0.0
      }
    };

    // Performance tracking
    this.performance = {
      totalTasks: 0,
      tasksByModel: {
        opus: 0,
        sonnet: 0,
        haiku: 0
      },
      averageLatency: {
        opus: [],
        sonnet: [],
        haiku: []
      },
      successRate: {
        opus: { success: 0, total: 0 },
        sonnet: { success: 0, total: 0 },
        haiku: { success: 0, total: 0 }
      },
      fallbacks: 0
    };

    // Task history
    this.taskHistory = [];
  }

  /**
   * Classify task complexity based on multiple factors
   *
   * @param {Object} task - Task to classify
   * @param {string} task.type - Task type
   * @param {string} task.description - Task description
   * @param {number} task.estimatedTokens - Estimated token count
   * @param {Object} task.requirements - Additional requirements
   * @returns {Object} Classification result with complexity score
   *
   * @example
   * const complexity = orchestrator.classifyTask({
   *   type: 'code-generation',
   *   description: 'Generate complex authentication system',
   *   estimatedTokens: 5000
   * });
   */
  classifyTask(task) {
    let complexityScore = 0;
    const factors = [];

    // Task type complexity
    const typeComplexity = {
      'code-generation': 0.8,
      'code-review': 0.7,
      'analysis': 0.7,
      'research': 0.8,
      'reasoning': 0.9,
      'translation': 0.3,
      'summarization': 0.4,
      'classification': 0.2,
      'extraction': 0.3,
      'formatting': 0.2,
      'simple-query': 0.3,
      'general': 0.5
    };

    const taskType = task.type || 'general';
    const baseComplexity = typeComplexity[taskType] || 0.5;
    complexityScore += baseComplexity * 0.4;
    factors.push({ factor: 'taskType', weight: 0.4, value: baseComplexity });

    // Description analysis
    if (task.description) {
      const desc = task.description.toLowerCase();
      let descComplexity = 0;

      // Complex keywords
      const complexKeywords = [
        'complex', 'advanced', 'sophisticated', 'intricate',
        'multi-step', 'comprehensive', 'detailed', 'in-depth'
      ];
      const simpleKeywords = [
        'simple', 'basic', 'quick', 'easy', 'straightforward'
      ];

      complexKeywords.forEach(keyword => {
        if (desc.includes(keyword)) descComplexity += 0.1;
      });
      simpleKeywords.forEach(keyword => {
        if (desc.includes(keyword)) descComplexity -= 0.1;
      });

      // Length indicates complexity
      if (desc.length > 200) descComplexity += 0.2;
      if (desc.length > 500) descComplexity += 0.2;

      descComplexity = Math.max(0, Math.min(1, descComplexity + 0.5));
      complexityScore += descComplexity * 0.3;
      factors.push({ factor: 'description', weight: 0.3, value: descComplexity });
    }

    // Token count
    const estimatedTokens = task.estimatedTokens || 1000;
    let tokenComplexity = 0;
    if (estimatedTokens < 500) tokenComplexity = 0.2;
    else if (estimatedTokens < 2000) tokenComplexity = 0.4;
    else if (estimatedTokens < 5000) tokenComplexity = 0.6;
    else if (estimatedTokens < 10000) tokenComplexity = 0.8;
    else tokenComplexity = 1.0;

    complexityScore += tokenComplexity * 0.2;
    factors.push({ factor: 'tokens', weight: 0.2, value: tokenComplexity });

    // Requirements
    if (task.requirements) {
      let reqComplexity = 0.5;
      if (task.requirements.accuracy === 'high') reqComplexity += 0.3;
      if (task.requirements.reasoning === 'deep') reqComplexity += 0.3;
      if (task.requirements.creativity === 'high') reqComplexity += 0.2;

      reqComplexity = Math.min(1, reqComplexity);
      complexityScore += reqComplexity * 0.1;
      factors.push({ factor: 'requirements', weight: 0.1, value: reqComplexity });
    }

    // Normalize to 0-1 range
    complexityScore = Math.max(0, Math.min(1, complexityScore));

    return {
      score: complexityScore,
      level: this._getComplexityLevel(complexityScore),
      factors,
      recommendation: this._getModelRecommendation(complexityScore)
    };
  }

  /**
   * Get complexity level from score
   * @private
   */
  _getComplexityLevel(score) {
    if (score >= 0.7) return 'high';
    if (score >= 0.4) return 'medium';
    return 'low';
  }

  /**
   * Get model recommendation based on complexity
   * @private
   */
  _getModelRecommendation(complexityScore) {
    if (complexityScore >= 0.7) return 'opus';
    if (complexityScore >= 0.35) return 'sonnet';
    return 'haiku';
  }

  /**
   * Select optimal model for a task with constraints
   *
   * @param {Object} task - Task to route
   * @param {Object} constraints - Selection constraints
   * @param {number} constraints.maxCost - Maximum cost per task
   * @param {number} constraints.maxLatency - Maximum acceptable latency
   * @param {string} constraints.preferredModel - Preferred model if suitable
   * @param {boolean} constraints.prioritize - 'cost' or 'quality' or 'speed'
   * @returns {Object} Selected model with reasoning
   *
   * @example
   * const selection = orchestrator.selectModel(task, {
   *   maxCost: 0.50,
   *   prioritize: 'cost'
   * });
   */
  selectModel(task, constraints = {}) {
    // Classify task
    const classification = this.classifyTask(task);

    // Merge constraints
    const finalConstraints = {
      maxCost: constraints.maxCost || null,
      maxLatency: constraints.maxLatency || null,
      preferredModel: constraints.preferredModel || null,
      prioritize: constraints.prioritize || 'quality',
      requireCapability: constraints.requireCapability || null
    };

    // Calculate scores for each model
    const modelScores = {};

    for (const [modelKey, model] of Object.entries(this.models)) {
      let score = 0;
      const reasons = [];

      // Capability match (most important)
      const capabilityMatch = this._calculateCapabilityMatch(
        model,
        classification.score,
        task
      );
      score += capabilityMatch * 0.5;
      reasons.push(`Capability match: ${(capabilityMatch * 100).toFixed(0)}%`);

      // Cost efficiency
      const estimatedCost = this._estimateCost(
        modelKey,
        task.estimatedTokens || 1000,
        task.estimatedOutputTokens || 500
      );

      if (finalConstraints.maxCost && estimatedCost > finalConstraints.maxCost) {
        score = -1; // Disqualify
        reasons.push(`Exceeds max cost ($${estimatedCost.toFixed(4)} > $${finalConstraints.maxCost})`);
      } else {
        const costScore = model.capabilities.costEfficiency;
        score += costScore * 0.3;
        reasons.push(`Cost efficiency: ${(costScore * 100).toFixed(0)}%`);
      }

      // Speed consideration
      const speedScore = model.capabilities.speed;
      score += speedScore * 0.2;
      reasons.push(`Speed: ${(speedScore * 100).toFixed(0)}%`);

      // Budget check
      if (this.budget.remaining < estimatedCost) {
        score = -1;
        reasons.push('Insufficient budget');
      }

      // Prioritization adjustment
      if (finalConstraints.prioritize === 'cost') {
        score = score * 0.5 + model.capabilities.costEfficiency * 0.5;
      } else if (finalConstraints.prioritize === 'speed') {
        score = score * 0.5 + model.capabilities.speed * 0.5;
      } else if (finalConstraints.prioritize === 'quality') {
        score = score * 0.5 + model.capabilities.complexity * 0.5;
      }

      modelScores[modelKey] = {
        score,
        estimatedCost,
        reasons,
        model
      };
    }

    // Select best model
    let selectedModel = null;
    let bestScore = -Infinity;

    for (const [modelKey, data] of Object.entries(modelScores)) {
      if (data.score > bestScore) {
        bestScore = data.score;
        selectedModel = modelKey;
      }
    }

    // Fallback logic
    if (!selectedModel || bestScore < 0) {
      if (this.config.enableFallback) {
        selectedModel = this._selectFallbackModel(classification, finalConstraints);
        this.performance.fallbacks++;
      } else {
        selectedModel = this.config.defaultModel;
      }
    }

    return {
      selectedModel,
      modelName: this.models[selectedModel].name,
      displayName: this.models[selectedModel].displayName,
      classification,
      estimatedCost: modelScores[selectedModel].estimatedCost,
      confidence: bestScore > 0 ? Math.min(100, bestScore * 100) : 50,
      reasoning: modelScores[selectedModel].reasons,
      allScores: Object.entries(modelScores).map(([key, data]) => ({
        model: key,
        score: data.score,
        cost: data.estimatedCost
      })),
      constraints: finalConstraints
    };
  }

  /**
   * Calculate capability match between model and task
   * @private
   */
  _calculateCapabilityMatch(model, complexityScore, task) {
    // Check if model capabilities align with task complexity
    const complexityMatch = 1 - Math.abs(model.capabilities.complexity - complexityScore);

    // Bonus for perfect matches
    let match = complexityMatch;

    // If task is highly complex, prefer models with high complexity handling
    if (complexityScore > 0.7 && model.capabilities.complexity >= 0.8) {
      match += 0.2;
    }

    // If task is simple, prefer efficient models
    if (complexityScore < 0.3 && model.capabilities.costEfficiency >= 0.8) {
      match += 0.2;
    }

    return Math.min(1, match);
  }

  /**
   * Estimate cost for a task
   * @private
   */
  _estimateCost(modelKey, inputTokens, outputTokens) {
    const model = this.models[modelKey];
    const inputCost = (inputTokens / 1000000) * model.inputPrice;
    const outputCost = (outputTokens / 1000000) * model.outputPrice;
    return inputCost + outputCost;
  }

  /**
   * Select fallback model when primary selection fails
   * @private
   */
  _selectFallbackModel(classification, constraints) {
    // Try to find a model within budget
    const affordableModels = ['haiku', 'sonnet', 'opus'];

    for (const modelKey of affordableModels) {
      const estimatedCost = this._estimateCost(modelKey, 1000, 500);
      if (this.budget.remaining >= estimatedCost) {
        return modelKey;
      }
    }

    // Last resort: use default
    return this.config.defaultModel;
  }

  /**
   * Route a task to the optimal model and execute
   *
   * @param {Object} task - Task to route
   * @param {Object} constraints - Routing constraints
   * @returns {Promise<Object>} Execution result with performance metrics
   *
   * @example
   * const result = await orchestrator.routeTask({
   *   type: 'code-generation',
   *   description: 'Generate REST API',
   *   estimatedTokens: 3000,
   *   executor: async (model) => { return await callModel(model); }
   * });
   */
  async routeTask(task, constraints = {}) {
    const startTime = Date.now();

    // Select model
    const selection = this.selectModel(task, constraints);

    // Execute task (simulated or real)
    let result;
    let success = true;

    try {
      if (task.executor && typeof task.executor === 'function') {
        // Real execution
        result = await task.executor(selection.modelName);
      } else {
        // Simulated execution
        result = await this._simulateExecution(selection.selectedModel, task);
      }
    } catch (error) {
      success = false;
      result = { error: error.message };
    }

    const endTime = Date.now();
    const latency = endTime - startTime;

    // Track performance
    const actualCost = result.actualCost || selection.estimatedCost;

    this.trackPerformance({
      model: selection.selectedModel,
      latency,
      cost: actualCost,
      success,
      task: {
        type: task.type,
        complexity: selection.classification.score
      }
    });

    // Update budget
    this._updateBudget(selection.selectedModel, actualCost);

    return {
      success,
      result,
      selection,
      performance: {
        latency,
        cost: actualCost,
        model: selection.selectedModel
      },
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Simulate task execution for demo purposes
   * @private
   */
  async _simulateExecution(modelKey, task) {
    const model = this.models[modelKey];

    // Simulate latency based on model speed
    const baseLatency = 1000; // 1 second base
    const latency = baseLatency / model.capabilities.speed;

    await new Promise(resolve => setTimeout(resolve, latency * 0.1)); // Shortened for demo

    // Simulate actual token usage (with some variance)
    const actualInputTokens = (task.estimatedTokens || 1000) * (0.9 + Math.random() * 0.2);
    const actualOutputTokens = (task.estimatedOutputTokens || 500) * (0.9 + Math.random() * 0.2);

    const actualCost = this._estimateCost(modelKey, actualInputTokens, actualOutputTokens);

    return {
      output: `Simulated output from ${model.displayName}`,
      tokensUsed: {
        input: Math.round(actualInputTokens),
        output: Math.round(actualOutputTokens)
      },
      actualCost,
      quality: model.capabilities.complexity * 100
    };
  }

  /**
   * Update budget tracking
   * @private
   */
  _updateBudget(modelKey, cost) {
    this.budget.spent += cost;
    this.budget.remaining -= cost;
    this.budget.breakdown[modelKey] += cost;
  }

  /**
   * Track performance metrics for a task execution
   *
   * @param {Object} metrics - Performance metrics
   * @param {string} metrics.model - Model used
   * @param {number} metrics.latency - Task latency in ms
   * @param {number} metrics.cost - Task cost
   * @param {boolean} metrics.success - Task success status
   * @param {Object} metrics.task - Task details
   *
   * @example
   * orchestrator.trackPerformance({
   *   model: 'sonnet',
   *   latency: 1250,
   *   cost: 0.045,
   *   success: true
   * });
   */
  trackPerformance(metrics) {
    if (!this.config.trackPerformance) return;

    this.performance.totalTasks++;
    this.performance.tasksByModel[metrics.model]++;

    // Track latency
    this.performance.averageLatency[metrics.model].push(metrics.latency);

    // Track success rate
    this.performance.successRate[metrics.model].total++;
    if (metrics.success) {
      this.performance.successRate[metrics.model].success++;
    }

    // Add to history
    this.taskHistory.push({
      timestamp: new Date().toISOString(),
      model: metrics.model,
      latency: metrics.latency,
      cost: metrics.cost,
      success: metrics.success,
      task: metrics.task
    });

    // Keep history limited to last 1000 tasks
    if (this.taskHistory.length > 1000) {
      this.taskHistory.shift();
    }
  }

  /**
   * Get comprehensive performance report
   *
   * @returns {Object} Performance report with statistics
   *
   * @example
   * const report = orchestrator.getPerformanceReport();
   * console.log(`Total tasks: ${report.totalTasks}`);
   * console.log(`Average cost: $${report.averageCost}`);
   */
  getPerformanceReport() {
    const report = {
      totalTasks: this.performance.totalTasks,
      budget: {
        total: this.budget.total,
        spent: this.budget.spent,
        remaining: this.budget.remaining,
        utilization: (this.budget.spent / this.budget.total * 100).toFixed(2) + '%',
        breakdown: this.budget.breakdown
      },
      modelUsage: {},
      averageCost: this.budget.spent / this.performance.totalTasks || 0,
      totalFallbacks: this.performance.fallbacks
    };

    // Calculate per-model statistics
    for (const [model, count] of Object.entries(this.performance.tasksByModel)) {
      const latencies = this.performance.averageLatency[model];
      const avgLatency = latencies.length > 0
        ? latencies.reduce((a, b) => a + b, 0) / latencies.length
        : 0;

      const successData = this.performance.successRate[model];
      const successRate = successData.total > 0
        ? (successData.success / successData.total * 100)
        : 0;

      report.modelUsage[model] = {
        count,
        percentage: (count / this.performance.totalTasks * 100).toFixed(2) + '%',
        averageLatency: Math.round(avgLatency) + 'ms',
        successRate: successRate.toFixed(2) + '%',
        totalCost: this.budget.breakdown[model].toFixed(4)
      };
    }

    return report;
  }

  /**
   * Get budget status
   *
   * @returns {Object} Budget information
   */
  getBudgetStatus() {
    return {
      total: this.budget.total,
      spent: this.budget.spent,
      remaining: this.budget.remaining,
      breakdown: this.budget.breakdown,
      utilization: (this.budget.spent / this.budget.total * 100).toFixed(2) + '%',
      remainingTasks: this._estimateRemainingTasks()
    };
  }

  /**
   * Estimate how many average tasks can be done with remaining budget
   * @private
   */
  _estimateRemainingTasks() {
    if (this.performance.totalTasks === 0) return 'Unknown';

    const avgCostPerTask = this.budget.spent / this.performance.totalTasks;
    return Math.floor(this.budget.remaining / avgCostPerTask);
  }

  /**
   * Reset budget tracking
   *
   * @param {number} newBudget - New budget amount
   */
  resetBudget(newBudget = null) {
    if (newBudget !== null) {
      this.budget.total = newBudget;
      this.budget.remaining = newBudget;
    } else {
      this.budget.remaining = this.budget.total;
    }

    this.budget.spent = 0;
    this.budget.breakdown = {
      opus: 0,
      sonnet: 0,
      haiku: 0
    };
  }

  /**
   * Get model information
   *
   * @param {string} modelKey - Model key (opus/sonnet/haiku)
   * @returns {Object} Model information
   */
  getModelInfo(modelKey) {
    return this.models[modelKey] || null;
  }

  /**
   * Get all available models
   *
   * @returns {Object} All model configurations
   */
  getAllModels() {
    return this.models;
  }
}

module.exports = { MultiModelOrchestrator };
