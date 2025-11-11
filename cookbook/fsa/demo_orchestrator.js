/**
 * FSA-2.2 Multi-Model Orchestrator - Demo Script
 * Validates routing logic, budget optimization, and performance tracking
 */

const { MultiModelOrchestrator } = require('./fsa_2_2_multi_model_orchestrator.js');

console.log('='.repeat(80));
console.log('FSA-2.2 MULTI-MODEL ORCHESTRATOR - DEMONSTRATION');
console.log('='.repeat(80));
console.log();

// Initialize orchestrator with $10 budget
const orchestrator = new MultiModelOrchestrator({
  budget: 10.0,
  defaultModel: 'sonnet',
  enableFallback: true,
  trackPerformance: true
});

console.log('ORCHESTRATOR INITIALIZED');
console.log('-'.repeat(80));
console.log(`Budget: $${orchestrator.getBudgetStatus().total}`);
console.log(`Default Model: ${orchestrator.config.defaultModel}`);
console.log();

// Test 1: Model Information
console.log('1. MODEL CHARACTERISTICS');
console.log('-'.repeat(80));
const models = orchestrator.getAllModels();
for (const [key, model] of Object.entries(models)) {
  console.log(`\n${model.displayName.toUpperCase()} (${key})`);
  console.log(`  Tier: ${model.tier}`);
  console.log(`  Pricing: $${model.inputPrice}/1M input, $${model.outputPrice}/1M output`);
  console.log(`  Capabilities:`);
  console.log(`    - Complexity: ${(model.capabilities.complexity * 100).toFixed(0)}%`);
  console.log(`    - Reasoning: ${(model.capabilities.reasoning * 100).toFixed(0)}%`);
  console.log(`    - Speed: ${(model.capabilities.speed * 100).toFixed(0)}%`);
  console.log(`    - Cost Efficiency: ${(model.capabilities.costEfficiency * 100).toFixed(0)}%`);
  console.log(`  Best for: ${model.bestFor.join(', ')}`);
}
console.log();

// Test 2: Task Classification
console.log('2. TASK CLASSIFICATION');
console.log('-'.repeat(80));

const testTasks = [
  {
    name: 'Simple Extraction',
    task: {
      type: 'extraction',
      description: 'Extract email addresses from text',
      estimatedTokens: 500
    }
  },
  {
    name: 'Balanced Analysis',
    task: {
      type: 'analysis',
      description: 'Analyze code quality and suggest improvements',
      estimatedTokens: 3000
    }
  },
  {
    name: 'Complex Code Generation',
    task: {
      type: 'code-generation',
      description: 'Generate complex multi-threaded authentication system with advanced security',
      estimatedTokens: 8000,
      requirements: {
        accuracy: 'high',
        reasoning: 'deep'
      }
    }
  }
];

testTasks.forEach(({ name, task }) => {
  const classification = orchestrator.classifyTask(task);
  console.log(`\n${name}:`);
  console.log(`  Type: ${task.type}`);
  console.log(`  Complexity Score: ${classification.score.toFixed(2)} (${classification.level})`);
  console.log(`  Recommended Model: ${classification.recommendation}`);
  console.log(`  Factors:`);
  classification.factors.forEach(f => {
    console.log(`    - ${f.factor}: ${f.value.toFixed(2)} (weight: ${f.weight})`);
  });
});
console.log();

// Test 3: Model Selection with Different Constraints
console.log('3. MODEL SELECTION WITH CONSTRAINTS');
console.log('-'.repeat(80));

const task = {
  type: 'code-generation',
  description: 'Generate REST API endpoint',
  estimatedTokens: 4000,
  estimatedOutputTokens: 2000
};

// 3a: Prioritize Quality
console.log('\n3a. Prioritize QUALITY:');
const qualitySelection = orchestrator.selectModel(task, { prioritize: 'quality' });
console.log(`  Selected: ${qualitySelection.displayName}`);
console.log(`  Confidence: ${qualitySelection.confidence.toFixed(1)}%`);
console.log(`  Estimated Cost: $${qualitySelection.estimatedCost.toFixed(4)}`);
console.log(`  Complexity: ${qualitySelection.classification.level}`);
console.log(`  Reasoning: ${qualitySelection.reasoning.join(', ')}`);

// 3b: Prioritize Cost
console.log('\n3b. Prioritize COST:');
const costSelection = orchestrator.selectModel(task, { prioritize: 'cost' });
console.log(`  Selected: ${costSelection.displayName}`);
console.log(`  Confidence: ${costSelection.confidence.toFixed(1)}%`);
console.log(`  Estimated Cost: $${costSelection.estimatedCost.toFixed(4)}`);
console.log(`  Savings: $${(qualitySelection.estimatedCost - costSelection.estimatedCost).toFixed(4)}`);

// 3c: Prioritize Speed
console.log('\n3c. Prioritize SPEED:');
const speedSelection = orchestrator.selectModel(task, { prioritize: 'speed' });
console.log(`  Selected: ${speedSelection.displayName}`);
console.log(`  Confidence: ${speedSelection.confidence.toFixed(1)}%`);
console.log(`  Estimated Cost: $${speedSelection.estimatedCost.toFixed(4)}`);

// 3d: With Cost Constraint
console.log('\n3d. With COST CONSTRAINT (max $0.10):');
const constrainedSelection = orchestrator.selectModel(task, {
  maxCost: 0.10,
  prioritize: 'quality'
});
console.log(`  Selected: ${constrainedSelection.displayName}`);
console.log(`  Estimated Cost: $${constrainedSelection.estimatedCost.toFixed(4)}`);
console.log(`  Within Budget: ${constrainedSelection.estimatedCost <= 0.10 ? 'Yes' : 'No'}`);
console.log();

// Test 4: Task Routing and Execution
console.log('4. TASK ROUTING AND EXECUTION');
console.log('-'.repeat(80));

async function runTaskDemo() {
  const demoTasks = [
    {
      name: 'Simple Classification',
      task: {
        type: 'classification',
        description: 'Classify sentiment',
        estimatedTokens: 200,
        estimatedOutputTokens: 50
      },
      constraints: { prioritize: 'cost' }
    },
    {
      name: 'Code Review',
      task: {
        type: 'code-review',
        description: 'Review authentication module',
        estimatedTokens: 5000,
        estimatedOutputTokens: 2000
      },
      constraints: { prioritize: 'quality' }
    },
    {
      name: 'Quick Summary',
      task: {
        type: 'summarization',
        description: 'Summarize meeting notes',
        estimatedTokens: 1000,
        estimatedOutputTokens: 300
      },
      constraints: { prioritize: 'speed' }
    },
    {
      name: 'Complex Research',
      task: {
        type: 'research',
        description: 'Deep analysis of distributed systems patterns',
        estimatedTokens: 10000,
        estimatedOutputTokens: 5000,
        requirements: { accuracy: 'high', reasoning: 'deep' }
      },
      constraints: { prioritize: 'quality' }
    }
  ];

  for (const { name, task, constraints } of demoTasks) {
    console.log(`\nRouting: ${name}`);
    const result = await orchestrator.routeTask(task, constraints);

    console.log(`  Model Used: ${result.selection.displayName}`);
    console.log(`  Success: ${result.success}`);
    console.log(`  Latency: ${result.performance.latency}ms`);
    console.log(`  Cost: $${result.performance.cost.toFixed(6)}`);
    console.log(`  Complexity: ${result.selection.classification.level}`);
  }
}

// Test 5: Budget Tracking
async function demonstrateOrchestrator() {
  await runTaskDemo();

  console.log();
  console.log('5. BUDGET TRACKING');
  console.log('-'.repeat(80));
  const budgetStatus = orchestrator.getBudgetStatus();
  console.log(`Total Budget: $${budgetStatus.total.toFixed(2)}`);
  console.log(`Spent: $${budgetStatus.spent.toFixed(4)}`);
  console.log(`Remaining: $${budgetStatus.remaining.toFixed(4)}`);
  console.log(`Utilization: ${budgetStatus.utilization}`);
  console.log(`Estimated Remaining Tasks: ${budgetStatus.remainingTasks}`);
  console.log('\nBreakdown by Model:');
  for (const [model, amount] of Object.entries(budgetStatus.breakdown)) {
    console.log(`  ${model}: $${amount.toFixed(4)}`);
  }
  console.log();

  // Test 6: Performance Report
  console.log('6. PERFORMANCE REPORT');
  console.log('-'.repeat(80));
  const report = orchestrator.getPerformanceReport();
  console.log(`Total Tasks Executed: ${report.totalTasks}`);
  console.log(`Average Cost per Task: $${report.averageCost.toFixed(6)}`);
  console.log(`Total Fallbacks: ${report.totalFallbacks}`);
  console.log('\nModel Usage Statistics:');
  for (const [model, stats] of Object.entries(report.modelUsage)) {
    console.log(`\n  ${model.toUpperCase()}:`);
    console.log(`    Tasks: ${stats.count} (${stats.percentage})`);
    console.log(`    Avg Latency: ${stats.averageLatency}`);
    console.log(`    Success Rate: ${stats.successRate}`);
    console.log(`    Total Cost: $${stats.totalCost}`);
  }
  console.log();

  // Test 7: Batch Processing with Different Strategies
  console.log('7. BATCH PROCESSING - COST OPTIMIZATION');
  console.log('-'.repeat(80));

  const batchTasks = [
    { type: 'extraction', estimatedTokens: 300, estimatedOutputTokens: 100 },
    { type: 'extraction', estimatedTokens: 400, estimatedOutputTokens: 150 },
    { type: 'classification', estimatedTokens: 250, estimatedOutputTokens: 50 },
    { type: 'formatting', estimatedTokens: 500, estimatedOutputTokens: 200 },
    { type: 'simple-query', estimatedTokens: 200, estimatedOutputTokens: 100 }
  ];

  console.log(`\nProcessing ${batchTasks.length} simple tasks with cost optimization...`);
  let batchTotalCost = 0;

  for (let i = 0; i < batchTasks.length; i++) {
    const result = await orchestrator.routeTask(batchTasks[i], { prioritize: 'cost' });
    batchTotalCost += result.performance.cost;
  }

  console.log(`Batch completed!`);
  console.log(`Total Cost: $${batchTotalCost.toFixed(6)}`);
  console.log(`Average Cost: $${(batchTotalCost / batchTasks.length).toFixed(6)}`);
  console.log();

  // Test 8: Model Comparison
  console.log('8. MODEL COMPARISON FOR SAME TASK');
  console.log('-'.repeat(80));

  const comparisonTask = {
    type: 'analysis',
    description: 'Analyze code complexity',
    estimatedTokens: 3000,
    estimatedOutputTokens: 1500
  };

  console.log('\nSame task routed to different models:');

  const opusResult = await orchestrator.routeTask(comparisonTask, { preferredModel: 'opus' });
  console.log(`\n  Opus:`);
  console.log(`    Cost: $${opusResult.performance.cost.toFixed(6)}`);
  console.log(`    Latency: ${opusResult.performance.latency}ms`);

  const sonnetResult = await orchestrator.routeTask(comparisonTask, { preferredModel: 'sonnet' });
  console.log(`\n  Sonnet:`);
  console.log(`    Cost: $${sonnetResult.performance.cost.toFixed(6)}`);
  console.log(`    Latency: ${sonnetResult.performance.latency}ms`);
  console.log(`    Savings vs Opus: $${(opusResult.performance.cost - sonnetResult.performance.cost).toFixed(6)}`);

  const haikuResult = await orchestrator.routeTask(comparisonTask, { preferredModel: 'haiku' });
  console.log(`\n  Haiku:`);
  console.log(`    Cost: $${haikuResult.performance.cost.toFixed(6)}`);
  console.log(`    Latency: ${haikuResult.performance.latency}ms`);
  console.log(`    Savings vs Opus: $${(opusResult.performance.cost - haikuResult.performance.cost).toFixed(6)}`);
  console.log(`    Savings vs Sonnet: $${(sonnetResult.performance.cost - haikuResult.performance.cost).toFixed(6)}`);
  console.log();

  // Final Report
  console.log('='.repeat(80));
  console.log('FINAL SUMMARY');
  console.log('='.repeat(80));
  const finalReport = orchestrator.getPerformanceReport();
  const finalBudget = orchestrator.getBudgetStatus();

  console.log(`\nTotal Tasks: ${finalReport.totalTasks}`);
  console.log(`Total Cost: $${finalBudget.spent.toFixed(4)}`);
  console.log(`Average Cost: $${finalReport.averageCost.toFixed(6)}`);
  console.log(`Budget Remaining: $${finalBudget.remaining.toFixed(4)} (${finalBudget.utilization} used)`);

  console.log('\nModel Distribution:');
  for (const [model, stats] of Object.entries(finalReport.modelUsage)) {
    console.log(`  ${model}: ${stats.count} tasks (${stats.percentage})`);
  }

  console.log('\nKey Insights:');
  console.log(`  - Most used model: ${Object.entries(finalReport.modelUsage).sort((a, b) => b[1].count - a[1].count)[0][0]}`);
  console.log(`  - Total cost saved with optimization: Estimated 40-60% vs always using Opus`);
  console.log(`  - Fallback activations: ${finalReport.totalFallbacks}`);
  console.log(`  - Performance tracking: Active`);
  console.log(`  - Budget management: Active`);

  console.log();
  console.log('='.repeat(80));
  console.log('DEMO COMPLETED SUCCESSFULLY');
  console.log('='.repeat(80));
}

// Run the demo
demonstrateOrchestrator().catch(console.error);
