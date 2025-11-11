"""
FSA-4.1: Meta-FSA Orchestrator

Coordinates all FSA components with intelligent task decomposition,
optimal FSA sequencing, and meta-learning capabilities.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# Import all FSA components
from agno.builder import MultiStepCodeBuilder
from agno.orchestrator import MultiModelOrchestrator
from agno.optimizer import PromptOptimizer
from agno.rsi import RSICodeOptimizer
from agno.templates import CodeTemplateLibrary
from agno.validator import CodeQualityValidator


class FSAType(Enum):
    """FSA component types."""

    PROMPT_OPTIMIZER = "fsa_1_1"  # FSA-1.1
    TEMPLATE_LIBRARY = "fsa_1_2"  # FSA-1.2
    QUALITY_VALIDATOR = "fsa_2_1"  # FSA-2.1
    MODEL_ORCHESTRATOR = "fsa_2_2"  # FSA-2.2
    CODE_BUILDER = "fsa_3_1"  # FSA-3.1
    RSI_OPTIMIZER = "fsa_3_2"  # FSA-3.2


class TaskType(Enum):
    """High-level task categories."""

    CODE_GENERATION = "code_generation"
    CODE_OPTIMIZATION = "code_optimization"
    CODE_VALIDATION = "code_validation"
    PROJECT_BUILD = "project_build"
    PROMPT_ANALYSIS = "prompt_analysis"
    TEMPLATE_RETRIEVAL = "template_retrieval"


@dataclass
class FSANode:
    """Represents an FSA component in the execution graph."""

    fsa_type: FSAType
    instance: Any
    dependencies: List[FSAType] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    execution_count: int = 0
    total_time_ms: float = 0.0
    success_rate: float = 1.0


@dataclass
class TaskComponent:
    """Decomposed task component."""

    task_type: TaskType
    description: str
    required_fsas: List[FSAType]
    input_data: Dict[str, Any]
    dependencies: List[int] = field(default_factory=list)  # Indices of dependent tasks
    priority: int = 1
    estimated_complexity: float = 0.5  # 0-1 scale


@dataclass
class FSAExecutionResult:
    """Result from FSA execution."""

    fsa_type: FSAType
    success: bool
    output: Any
    execution_time_ms: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class OrchestrationResult:
    """Complete orchestration result."""

    success: bool
    task_components: List[TaskComponent]
    execution_sequence: List[FSAType]
    results: List[FSAExecutionResult]
    total_time_ms: float
    final_output: Any
    metrics: Dict[str, Any] = field(default_factory=dict)
    learned_patterns: List[str] = field(default_factory=list)


class MetaFSAOrchestrator:
    """
    Meta-FSA Orchestrator coordinating all FSA components.

    Capabilities:
    - Intelligent task decomposition
    - Optimal FSA sequencing based on dependencies
    - Performance tracking across all FSAs
    - Meta-learning from execution history
    - Unified API for FSA invocation
    """

    def __init__(self):
        """Initialize Meta-FSA Orchestrator with all FSA components."""
        # Initialize FSA components
        self.fsas: Dict[FSAType, FSANode] = {
            FSAType.PROMPT_OPTIMIZER: FSANode(
                fsa_type=FSAType.PROMPT_OPTIMIZER,
                instance=PromptOptimizer(),
                dependencies=[],
            ),
            FSAType.TEMPLATE_LIBRARY: FSANode(
                fsa_type=FSAType.TEMPLATE_LIBRARY,
                instance=CodeTemplateLibrary(),
                dependencies=[],
            ),
            FSAType.QUALITY_VALIDATOR: FSANode(
                fsa_type=FSAType.QUALITY_VALIDATOR,
                instance=CodeQualityValidator(),
                dependencies=[FSAType.PROMPT_OPTIMIZER, FSAType.TEMPLATE_LIBRARY],
            ),
            FSAType.MODEL_ORCHESTRATOR: FSANode(
                fsa_type=FSAType.MODEL_ORCHESTRATOR,
                instance=MultiModelOrchestrator(),
                dependencies=[],
            ),
            FSAType.CODE_BUILDER: FSANode(
                fsa_type=FSAType.CODE_BUILDER,
                instance=MultiStepCodeBuilder(),
                dependencies=[
                    FSAType.PROMPT_OPTIMIZER,
                    FSAType.TEMPLATE_LIBRARY,
                    FSAType.QUALITY_VALIDATOR,
                    FSAType.MODEL_ORCHESTRATOR,
                ],
            ),
            FSAType.RSI_OPTIMIZER: FSANode(
                fsa_type=FSAType.RSI_OPTIMIZER,
                instance=RSICodeOptimizer(),
                dependencies=[FSAType.QUALITY_VALIDATOR],
            ),
        }

        # Execution history for meta-learning
        self.execution_history: List[OrchestrationResult] = []
        self.learned_patterns: List[Dict[str, Any]] = []

    def orchestrate(
        self,
        task: str,
        task_type: TaskType,
        language: str = "python",
        config: Optional[Dict[str, Any]] = None,
    ) -> OrchestrationResult:
        """
        Main orchestration method coordinating all FSAs.

        Args:
            task: High-level task description
            task_type: Type of task to orchestrate
            language: Programming language
            config: Optional configuration (budget, quality_target, etc.)

        Returns:
            OrchestrationResult with complete execution details
        """
        start_time = time.time()
        config = config or {}

        print(f"\n{'='*80}")
        print(f"  META-FSA ORCHESTRATION: {task_type.value.upper()}")
        print(f"{'='*80}\n")
        print(f"Task: {task}")
        print(f"Language: {language}")
        print(f"Config: {config}\n")

        try:
            # Step 1: Decompose task into components
            print("📋 Step 1: Task Decomposition")
            task_components = self.decompose(task, task_type, language, config)
            print(f"   Decomposed into {len(task_components)} components\n")

            # Step 2: Select optimal FSA sequence
            print("🔍 Step 2: FSA Selection")
            execution_sequence = self.selectFSAs(task_components)
            print(f"   Selected FSA chain: {' → '.join([fsa.value for fsa in execution_sequence])}\n")

            # Step 3: Execute FSA sequence
            print("⚙️  Step 3: FSA Chain Execution")
            results = self.executeSequence(execution_sequence, task_components, language, config)

            # Step 4: Aggregate final output
            final_output = self._aggregateOutput(results, task_type)

            # Step 5: Track performance
            total_time_ms = (time.time() - start_time) * 1000
            metrics = self._computeMetrics(results, total_time_ms)

            # Step 6: Learn from execution
            learned = self.learnFromExecution(task_components, execution_sequence, results)

            orchestration_result = OrchestrationResult(
                success=all(r.success for r in results),
                task_components=task_components,
                execution_sequence=execution_sequence,
                results=results,
                total_time_ms=total_time_ms,
                final_output=final_output,
                metrics=metrics,
                learned_patterns=learned,
            )

            # Store in history
            self.execution_history.append(orchestration_result)

            print(f"\n✅ Orchestration complete in {total_time_ms:.0f}ms")
            return orchestration_result

        except Exception as e:
            print(f"\n❌ Orchestration failed: {e}")
            return OrchestrationResult(
                success=False,
                task_components=[],
                execution_sequence=[],
                results=[],
                total_time_ms=(time.time() - start_time) * 1000,
                final_output=None,
                metrics={"error": str(e)},
            )

    def decompose(
        self,
        task: str,
        task_type: TaskType,
        language: str,
        config: Dict[str, Any],
    ) -> List[TaskComponent]:
        """
        Decompose high-level task into FSA-appropriate components.

        Args:
            task: Task description
            task_type: Type of task
            language: Programming language
            config: Configuration

        Returns:
            List of TaskComponent objects
        """
        components: List[TaskComponent] = []

        if task_type == TaskType.PROJECT_BUILD:
            # Complex multi-FSA workflow
            components = [
                TaskComponent(
                    task_type=TaskType.PROMPT_ANALYSIS,
                    description="Optimize prompts for code generation",
                    required_fsas=[FSAType.PROMPT_OPTIMIZER],
                    input_data={"task": task, "language": language},
                    priority=1,
                    estimated_complexity=0.2,
                ),
                TaskComponent(
                    task_type=TaskType.TEMPLATE_RETRIEVAL,
                    description="Retrieve code templates",
                    required_fsas=[FSAType.TEMPLATE_LIBRARY],
                    input_data={"task": task, "language": language},
                    priority=1,
                    estimated_complexity=0.1,
                ),
                TaskComponent(
                    task_type=TaskType.CODE_GENERATION,
                    description="Generate project code",
                    required_fsas=[FSAType.CODE_BUILDER, FSAType.MODEL_ORCHESTRATOR],
                    input_data={"task": task, "language": language, "config": config},
                    dependencies=[0, 1],  # Depends on prompts and templates
                    priority=2,
                    estimated_complexity=0.7,
                ),
                TaskComponent(
                    task_type=TaskType.CODE_VALIDATION,
                    description="Validate generated code quality",
                    required_fsas=[FSAType.QUALITY_VALIDATOR],
                    input_data={"language": language},
                    dependencies=[2],  # Depends on code generation
                    priority=3,
                    estimated_complexity=0.3,
                ),
                TaskComponent(
                    task_type=TaskType.CODE_OPTIMIZATION,
                    description="Optimize code through RSI",
                    required_fsas=[FSAType.RSI_OPTIMIZER],
                    input_data={"language": language, "max_iterations": config.get("rsi_iterations", 3)},
                    dependencies=[2, 3],  # Depends on code generation and validation
                    priority=4,
                    estimated_complexity=0.6,
                ),
            ]

        elif task_type == TaskType.CODE_OPTIMIZATION:
            # RSI-focused workflow
            components = [
                TaskComponent(
                    task_type=TaskType.CODE_VALIDATION,
                    description="Validate initial code quality",
                    required_fsas=[FSAType.QUALITY_VALIDATOR],
                    input_data={"code": task, "language": language},
                    priority=1,
                    estimated_complexity=0.3,
                ),
                TaskComponent(
                    task_type=TaskType.CODE_OPTIMIZATION,
                    description="Apply recursive self-improvement",
                    required_fsas=[FSAType.RSI_OPTIMIZER],
                    input_data={"code": task, "language": language, "max_iterations": config.get("rsi_iterations", 5)},
                    dependencies=[0],
                    priority=2,
                    estimated_complexity=0.7,
                ),
            ]

        elif task_type == TaskType.CODE_VALIDATION:
            # Validation-focused workflow
            components = [
                TaskComponent(
                    task_type=TaskType.PROMPT_ANALYSIS,
                    description="Optimize validation prompts",
                    required_fsas=[FSAType.PROMPT_OPTIMIZER],
                    input_data={"task": task, "language": language},
                    priority=1,
                    estimated_complexity=0.2,
                ),
                TaskComponent(
                    task_type=TaskType.CODE_VALIDATION,
                    description="Perform quality validation",
                    required_fsas=[FSAType.QUALITY_VALIDATOR],
                    input_data={"code": task, "language": language},
                    dependencies=[0],
                    priority=2,
                    estimated_complexity=0.5,
                ),
            ]

        else:
            # Default: single-FSA execution
            components = [
                TaskComponent(
                    task_type=task_type,
                    description=task,
                    required_fsas=[self._inferFSA(task_type)],
                    input_data={"task": task, "language": language, "config": config},
                    priority=1,
                    estimated_complexity=0.5,
                )
            ]

        return components

    def selectFSAs(self, task_components: List[TaskComponent]) -> List[FSAType]:
        """
        Select optimal FSA execution sequence based on task components.

        Args:
            task_components: Decomposed task components

        Returns:
            Ordered list of FSA types to execute
        """
        # Collect all required FSAs
        required_fsas = set()
        for component in task_components:
            required_fsas.update(component.required_fsas)

        # Build dependency-aware execution order
        execution_order: List[FSAType] = []
        remaining = set(required_fsas)

        # Topological sort based on dependencies
        while remaining:
            # Find FSAs with no unresolved dependencies
            ready = [
                fsa
                for fsa in remaining
                if all(dep in execution_order or dep not in required_fsas for dep in self.fsas[fsa].dependencies)
            ]

            if not ready:
                # Circular dependency or missing dependency - add remaining in arbitrary order
                ready = list(remaining)

            # Sort by historical performance (better performing FSAs first)
            ready.sort(key=lambda fsa: self.fsas[fsa].success_rate, reverse=True)

            # Add to execution order
            execution_order.extend(ready)
            remaining -= set(ready)

        return execution_order

    def executeSequence(
        self,
        fsa_sequence: List[FSAType],
        task_components: List[TaskComponent],
        language: str,
        config: Dict[str, Any],
    ) -> List[FSAExecutionResult]:
        """
        Execute FSA sequence with proper data flow.

        Args:
            fsa_sequence: Ordered FSA types to execute
            task_components: Task components
            language: Programming language
            config: Configuration

        Returns:
            List of FSAExecutionResult objects
        """
        results: List[FSAExecutionResult] = []
        context: Dict[str, Any] = {
            "language": language,
            "config": config,
            "task_components": task_components,
        }

        for i, fsa_type in enumerate(fsa_sequence):
            print(f"   [{i+1}/{len(fsa_sequence)}] Executing {fsa_type.value}...")

            start_time = time.time()
            fsa_node = self.fsas[fsa_type]

            try:
                # Find relevant task component
                component = next(
                    (tc for tc in task_components if fsa_type in tc.required_fsas),
                    None,
                )

                if not component:
                    # No specific component, skip
                    continue

                # Execute FSA based on type
                output, metrics = self._executeFSA(fsa_type, fsa_node.instance, component, context)

                execution_time_ms = (time.time() - start_time) * 1000

                result = FSAExecutionResult(
                    fsa_type=fsa_type,
                    success=True,
                    output=output,
                    execution_time_ms=execution_time_ms,
                    metrics=metrics,
                )

                # Update context with output for downstream FSAs
                context[fsa_type.value] = output

                # Track FSA performance
                self.trackPerformance(fsa_type, execution_time_ms, True)

                results.append(result)
                print(f"      ✓ Completed in {execution_time_ms:.1f}ms")

            except Exception as e:
                execution_time_ms = (time.time() - start_time) * 1000
                result = FSAExecutionResult(
                    fsa_type=fsa_type,
                    success=False,
                    output=None,
                    execution_time_ms=execution_time_ms,
                    error=str(e),
                )
                results.append(result)
                self.trackPerformance(fsa_type, execution_time_ms, False)
                print(f"      ✗ Failed: {e}")

        return results

    def trackPerformance(self, fsa_type: FSAType, execution_time_ms: float, success: bool):
        """
        Track FSA performance metrics.

        Args:
            fsa_type: FSA type
            execution_time_ms: Execution time
            success: Whether execution succeeded
        """
        node = self.fsas[fsa_type]
        node.execution_count += 1
        node.total_time_ms += execution_time_ms

        # Update success rate with exponential moving average
        alpha = 0.3
        node.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * node.success_rate

        # Store metrics
        node.metrics["avg_time_ms"] = node.total_time_ms / node.execution_count
        node.metrics["success_rate"] = node.success_rate
        node.metrics["total_executions"] = node.execution_count

    def learnFromExecution(
        self,
        task_components: List[TaskComponent],
        execution_sequence: List[FSAType],
        results: List[FSAExecutionResult],
    ) -> List[str]:
        """
        Learn patterns from execution for future optimizations.

        Args:
            task_components: Task components executed
            execution_sequence: FSA sequence used
            results: Execution results

        Returns:
            List of learned pattern descriptions
        """
        learned = []

        # Pattern 1: Identify successful FSA chains
        if all(r.success for r in results):
            pattern = {
                "type": "successful_chain",
                "sequence": [fsa.value for fsa in execution_sequence],
                "avg_time_ms": sum(r.execution_time_ms for r in results) / len(results) if results else 0,
            }
            self.learned_patterns.append(pattern)
            learned.append(f"Successful FSA chain: {' → '.join(pattern['sequence'])}")

        # Pattern 2: Identify bottlenecks
        if results:
            slowest = max(results, key=lambda r: r.execution_time_ms)
            if slowest.execution_time_ms > 100:  # >100ms
                learned.append(f"Performance bottleneck: {slowest.fsa_type.value} ({slowest.execution_time_ms:.0f}ms)")

        # Pattern 3: Track component complexity vs execution time
        for component in task_components:
            relevant_results = [r for r in results if r.fsa_type in component.required_fsas]
            if relevant_results:
                avg_time = sum(r.execution_time_ms for r in relevant_results) / len(relevant_results)
                if avg_time / (component.estimated_complexity + 0.1) > 500:
                    learned.append(
                        f"Component complexity underestimated: {component.task_type.value} "
                        f"(estimated {component.estimated_complexity}, actual time {avg_time:.0f}ms)"
                    )

        return learned

    def getPerformanceDashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive performance dashboard across all FSAs.

        Returns:
            Dashboard data with metrics for all FSAs
        """
        dashboard = {
            "total_orchestrations": len(self.execution_history),
            "fsas": {},
            "learned_patterns": self.learned_patterns[-10:],  # Last 10 patterns
        }

        for fsa_type, node in self.fsas.items():
            dashboard["fsas"][fsa_type.value] = {
                "executions": node.execution_count,
                "avg_time_ms": node.metrics.get("avg_time_ms", 0),
                "success_rate": node.success_rate * 100,
                "total_time_ms": node.total_time_ms,
            }

        return dashboard

    def _executeFSA(
        self,
        fsa_type: FSAType,
        fsa_instance: Any,
        component: TaskComponent,
        context: Dict[str, Any],
    ) -> Tuple[Any, Dict[str, Any]]:
        """Execute specific FSA based on type."""
        metrics = {}

        if fsa_type == FSAType.PROMPT_OPTIMIZER:
            # FSA-1.1: Prompt Optimizer
            from agno.optimizer import AnalysisType

            task = component.input_data.get("task", "")
            language = component.input_data.get("language", "python")
            optimized = fsa_instance.optimize_for_analysis(task, language, AnalysisType.SECURITY)
            metrics["prompt_length"] = len(optimized.prompt)
            return optimized, metrics

        elif fsa_type == FSAType.TEMPLATE_LIBRARY:
            # FSA-1.2: Template Library
            language = component.input_data.get("language", "python")
            templates = fsa_instance.get_templates_by_language(language=language)
            metrics["template_count"] = len(templates)
            return templates, metrics

        elif fsa_type == FSAType.QUALITY_VALIDATOR:
            # FSA-2.1: Quality Validator
            code = component.input_data.get("code") or context.get("generated_code", "")
            language = component.input_data.get("language", "python")

            if code:
                validation = fsa_instance.validateCode(code, language)
                metrics["quality_score"] = validation.report.overall_score
                metrics["issues_found"] = len(validation.top_issues)
                return validation, metrics
            return None, metrics

        elif fsa_type == FSAType.MODEL_ORCHESTRATOR:
            # FSA-2.2: Model Orchestrator
            task = component.input_data.get("task", "")
            budget = component.input_data.get("config", {}).get("budget")
            # Note: Actual execution would happen within CODE_BUILDER
            metrics["model_selected"] = "sonnet"  # Would be determined by orchestrator
            return {"task": task, "budget": budget}, metrics

        elif fsa_type == FSAType.CODE_BUILDER:
            # FSA-3.1: Code Builder
            task = component.input_data.get("task", "")
            language = component.input_data.get("language", "python")
            config = component.input_data.get("config", {})

            result = fsa_instance.buildProject(
                requirements=task,
                project_name="meta_orchestrated_project",
                language=language,
                budget=config.get("budget"),
            )

            metrics["steps_completed"] = len(result.steps)
            metrics["overall_quality"] = result.overall_quality_score
            # Extract generated code from steps
            generated_code = "\n\n".join([step.generated_code for step in result.steps if step.generated_code])
            context["generated_code"] = generated_code  # Store for validation
            return result, metrics

        elif fsa_type == FSAType.RSI_OPTIMIZER:
            # FSA-3.2: RSI Optimizer
            code = component.input_data.get("code") or context.get("generated_code", "")
            language = component.input_data.get("language", "python")
            max_iterations = component.input_data.get("max_iterations", 3)

            if code:
                result = fsa_instance.optimizeCode(code, language, max_iterations)
                metrics["iterations"] = len(result.iterations)
                metrics["quality_improvement"] = result.total_improvement
                context["optimized_code"] = result.optimized_code  # Store final code
                return result, metrics

        return None, metrics

    def _inferFSA(self, task_type: TaskType) -> FSAType:
        """Infer FSA type from task type."""
        mapping = {
            TaskType.CODE_GENERATION: FSAType.CODE_BUILDER,
            TaskType.CODE_OPTIMIZATION: FSAType.RSI_OPTIMIZER,
            TaskType.CODE_VALIDATION: FSAType.QUALITY_VALIDATOR,
            TaskType.PROJECT_BUILD: FSAType.CODE_BUILDER,
            TaskType.PROMPT_ANALYSIS: FSAType.PROMPT_OPTIMIZER,
            TaskType.TEMPLATE_RETRIEVAL: FSAType.TEMPLATE_LIBRARY,
        }
        return mapping.get(task_type, FSAType.CODE_BUILDER)

    def _aggregateOutput(self, results: List[FSAExecutionResult], task_type: TaskType) -> Any:
        """Aggregate FSA outputs into final result."""
        # Return the most relevant output based on task type
        if task_type == TaskType.PROJECT_BUILD:
            # Return code builder output
            for result in results:
                if result.fsa_type == FSAType.CODE_BUILDER and result.success:
                    return result.output

        elif task_type == TaskType.CODE_OPTIMIZATION:
            # Return RSI optimizer output
            for result in results:
                if result.fsa_type == FSAType.RSI_OPTIMIZER and result.success:
                    return result.output

        elif task_type == TaskType.CODE_VALIDATION:
            # Return validator output
            for result in results:
                if result.fsa_type == FSAType.QUALITY_VALIDATOR and result.success:
                    return result.output

        # Default: return last successful result
        for result in reversed(results):
            if result.success:
                return result.output

        return None

    def _computeMetrics(self, results: List[FSAExecutionResult], total_time_ms: float) -> Dict[str, Any]:
        """Compute aggregate metrics."""
        return {
            "total_fsas_executed": len(results),
            "successful_fsas": sum(1 for r in results if r.success),
            "failed_fsas": sum(1 for r in results if not r.success),
            "total_time_ms": total_time_ms,
            "avg_fsa_time_ms": sum(r.execution_time_ms for r in results) / len(results) if results else 0,
            "success_rate": sum(1 for r in results if r.success) / len(results) if results else 0,
        }
