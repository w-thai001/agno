"""
Meta-FSA Orchestrator - The Master Coordinator

This module provides intelligent coordination of all FSA modules,
dynamically routing tasks through optimal FSA chains based on task
characteristics, complexity, and historical performance data.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re


class MetaFSAOrchestrator:
    """
    Meta-FSA Orchestrator that intelligently coordinates all FSA modules.

    This orchestrator analyzes incoming tasks, determines optimal FSA routing,
    executes FSA chains, and learns from execution patterns to improve future
    routing decisions.
    """

    def __init__(
        self,
        fsa_1_1=None,
        fsa_1_2=None,
        fsa_2_1=None,
        fsa_2_2=None,
        fsa_3_1=None,
        fsa_3_2=None
    ):
        """
        Initialize Meta-FSA Orchestrator with all FSA dependencies.

        Args:
            fsa_1_1: Task Planning Agent (FSA-1.1)
            fsa_1_2: Task Decomposition Agent (FSA-1.2)
            fsa_2_1: Quality Assurance Agent (FSA-2.1)
            fsa_2_2: Implementation Agent (FSA-2.2)
            fsa_3_1: Integration Agent (FSA-3.1)
            fsa_3_2: Optimization Agent (FSA-3.2)

        Raises:
            ValueError: If any required FSA module is None
        """
        # Defensive null checks
        if fsa_1_1 is None:
            raise ValueError("FSA-1.1 (Task Planning Agent) cannot be None")
        if fsa_1_2 is None:
            raise ValueError("FSA-1.2 (Task Decomposition Agent) cannot be None")
        if fsa_2_1 is None:
            raise ValueError("FSA-2.1 (Quality Assurance Agent) cannot be None")
        if fsa_2_2 is None:
            raise ValueError("FSA-2.2 (Implementation Agent) cannot be None")
        if fsa_3_1 is None:
            raise ValueError("FSA-3.1 (Integration Agent) cannot be None")
        if fsa_3_2 is None:
            raise ValueError("FSA-3.2 (Optimization Agent) cannot be None")

        # Store FSA references
        self.fsa_1_1 = fsa_1_1
        self.fsa_1_2 = fsa_1_2
        self.fsa_2_1 = fsa_2_1
        self.fsa_2_2 = fsa_2_2
        self.fsa_3_1 = fsa_3_1
        self.fsa_3_2 = fsa_3_2

        # FSA registry for easy access
        self.fsa_registry = {
            "FSA-1.1": fsa_1_1,
            "FSA-1.2": fsa_1_2,
            "FSA-2.1": fsa_2_1,
            "FSA-2.2": fsa_2_2,
            "FSA-3.1": fsa_3_1,
            "FSA-3.2": fsa_3_2
        }

        # Performance tracking and meta-learning data
        self.execution_history = []
        self.performance_stats = {
            "total_executions": 0,
            "total_execution_time": 0.0,
            "avg_execution_time": 0.0,
            "complexity_stats": {
                "low": {"count": 0, "avg_time": 0.0, "total_time": 0.0},
                "medium": {"count": 0, "avg_time": 0.0, "total_time": 0.0},
                "high": {"count": 0, "avg_time": 0.0, "total_time": 0.0}
            },
            "task_type_stats": {},
            "chain_performance": {}
        }

        # Meta-learning data: stores which chains work best for which task profiles
        self.learning_data = {
            "optimal_chains": {},  # Maps task profile to best performing chain
            "chain_success_rates": {},  # Success rate for each chain pattern
            "complexity_chain_mapping": {  # Recommended chains by complexity
                "low": ["FSA-1.1", "FSA-1.2", "FSA-2.1"],
                "medium": ["FSA-1.1", "FSA-1.2", "FSA-2.2", "FSA-3.1", "FSA-2.1"],
                "high": ["FSA-1.1", "FSA-1.2", "FSA-2.2", "FSA-3.1", "FSA-3.2", "FSA-2.1"]
            }
        }

    def orchestrate(self, task: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main orchestration method that analyzes tasks and routes through optimal FSA chains.

        Args:
            task: Task specification containing description and requirements
            options: Optional configuration for orchestration behavior

        Returns:
            Orchestration result including FSA chain execution results, metrics, and metadata

        Raises:
            ValueError: If task is None or invalid
        """
        if not task:
            raise ValueError("Task cannot be None or empty")

        options = options or {}
        start_time = time.time()

        try:
            # Step 1: Analyze the task
            task_profile = self.analyzeTask(task)

            # Step 2: Select optimal FSA chain based on task profile
            selected_chain = self.selectFSAChain(task_profile, options)

            # Step 3: Execute the FSA chain
            execution_result = self.executeFSAChain(selected_chain, task, options)

            # Calculate total execution time
            total_time = time.time() - start_time

            # Step 4: Learn from this execution
            self.learnFromExecution(task_profile, selected_chain, execution_result, total_time)

            # Compile final result
            result = {
                "status": "success",
                "task_profile": task_profile,
                "selected_chain": selected_chain,
                "execution_result": execution_result,
                "total_execution_time": total_time,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "total_executions": self.performance_stats["total_executions"],
                    "learning_enabled": True
                }
            }

            return result

        except Exception as e:
            error_time = time.time() - start_time
            return {
                "status": "error",
                "error": str(e),
                "execution_time": error_time,
                "timestamp": datetime.now().isoformat()
            }

    def analyzeTask(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze task complexity, type, quality requirements, and optimization needs.

        Args:
            task: Task specification

        Returns:
            Task profile with complexity, type, and requirements analysis
        """
        if not task:
            raise ValueError("Task cannot be None")

        description = task.get("description", "").lower()

        # Complexity detection
        complexity = self._detectComplexity(description, task)

        # Task type detection
        task_type = self._detectTaskType(description, task)

        # Quality requirements detection
        quality_requirements = self._detectQualityRequirements(description, task)

        # Optimization needs detection
        optimization_needs = self._detectOptimizationNeeds(description, task)

        # Integration requirements detection
        integration_requirements = self._detectIntegrationRequirements(description, task)

        return {
            "complexity": complexity,
            "task_type": task_type,
            "quality_requirements": quality_requirements,
            "optimization_needs": optimization_needs,
            "integration_requirements": integration_requirements,
            "original_task": task
        }

    def _detectComplexity(self, description: str, task: Dict[str, Any]) -> str:
        """Detect task complexity level."""
        # Check for explicit complexity in task
        if "complexity" in task:
            return task["complexity"]

        # Complexity indicators
        high_complexity_indicators = [
            "complex", "system", "architecture", "integration", "multiple",
            "advanced", "comprehensive", "enterprise", "distributed", "microservice"
        ]
        medium_complexity_indicators = [
            "api", "rest", "endpoint", "database", "crud", "authentication",
            "middleware", "service", "module", "component"
        ]
        low_complexity_indicators = [
            "simple", "utility", "function", "helper", "basic", "single"
        ]

        # Count indicators
        high_count = sum(1 for indicator in high_complexity_indicators if indicator in description)
        medium_count = sum(1 for indicator in medium_complexity_indicators if indicator in description)
        low_count = sum(1 for indicator in low_complexity_indicators if indicator in description)

        # Determine complexity
        if high_count >= 2 or "complex" in description:
            return "high"
        elif medium_count >= 2 or any(ind in description for ind in ["api", "rest", "database"]):
            return "medium"
        elif low_count >= 1 or any(ind in description for ind in ["function", "utility"]):
            return "low"
        else:
            # Default based on description length and structure
            word_count = len(description.split())
            if word_count > 20:
                return "high"
            elif word_count > 10:
                return "medium"
            else:
                return "low"

    def _detectTaskType(self, description: str, task: Dict[str, Any]) -> str:
        """Detect task type (backend/frontend/data/testing/general)."""
        # Check for explicit type in task
        if "type" in task:
            return task["type"]

        # Task type indicators
        type_indicators = {
            "backend": ["api", "rest", "server", "endpoint", "database", "backend", "service"],
            "frontend": ["ui", "frontend", "component", "react", "vue", "angular", "interface"],
            "data": ["data", "analysis", "etl", "pipeline", "processing", "analytics"],
            "testing": ["test", "testing", "unittest", "integration test", "e2e"],
            "general": ["utility", "function", "helper", "tool"]
        }

        # Score each type
        type_scores = {}
        for task_type, indicators in type_indicators.items():
            score = sum(1 for indicator in indicators if indicator in description)
            if score > 0:
                type_scores[task_type] = score

        # Return highest scoring type or "general"
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        return "general"

    def _detectQualityRequirements(self, description: str, task: Dict[str, Any]) -> Dict[str, bool]:
        """Detect quality requirements."""
        return {
            "validation": any(word in description for word in ["validate", "validation", "check"]),
            "error_handling": any(word in description for word in ["error", "exception", "handling"]),
            "testing": any(word in description for word in ["test", "testing", "coverage"]),
            "security": any(word in description for word in ["secure", "security", "auth", "authentication"]),
            "documentation": any(word in description for word in ["document", "documentation", "comment"])
        }

    def _detectOptimizationNeeds(self, description: str, task: Dict[str, Any]) -> Dict[str, bool]:
        """Detect optimization requirements."""
        return {
            "performance": any(word in description for word in ["performance", "optimize", "fast", "speed"]),
            "scalability": any(word in description for word in ["scale", "scalability", "scalable"]),
            "memory": any(word in description for word in ["memory", "efficient", "lightweight"]),
            "required": any(word in description for word in ["optimization", "optimize", "optimized"])
        }

    def _detectIntegrationRequirements(self, description: str, task: Dict[str, Any]) -> Dict[str, bool]:
        """Detect integration requirements."""
        return {
            "multiple_components": any(word in description for word in ["multiple", "several", "components"]),
            "system_integration": any(word in description for word in ["integration", "integrate", "system"]),
            "api_integration": any(word in description for word in ["api", "endpoint", "rest"]),
            "required": any(word in description for word in ["integration", "integrate", "connect"])
        }

    def selectFSAChain(self, profile: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Select optimal FSA sequence based on task profile.

        Args:
            profile: Task profile from analyzeTask
            options: Optional configuration options

        Returns:
            List of FSA names in execution order
        """
        if not profile:
            raise ValueError("Profile cannot be None")

        options = options or {}
        complexity = profile.get("complexity", "low")

        # Start with base chain from learning data
        chain = list(self.learning_data["complexity_chain_mapping"].get(complexity, []))

        # Check for override in options
        if options.get("force_chain"):
            return options["force_chain"]

        # Adjust chain based on task requirements

        # If optimization is required, ensure FSA-3.2 is in the chain
        optimization_needs = profile.get("optimization_needs", {})
        if optimization_needs.get("required") or optimization_needs.get("performance"):
            if "FSA-3.2" not in chain:
                # Insert FSA-3.2 before final QA
                if "FSA-2.1" in chain:
                    qa_index = chain.index("FSA-2.1")
                    chain.insert(qa_index, "FSA-3.2")
                else:
                    chain.append("FSA-3.2")

        # If integration is required, ensure FSA-3.1 is in the chain
        integration_reqs = profile.get("integration_requirements", {})
        if integration_reqs.get("required") or integration_reqs.get("system_integration"):
            if "FSA-3.1" not in chain:
                # Insert FSA-3.1 before optimization or QA
                if "FSA-3.2" in chain:
                    opt_index = chain.index("FSA-3.2")
                    chain.insert(opt_index, "FSA-3.1")
                elif "FSA-2.1" in chain:
                    qa_index = chain.index("FSA-2.1")
                    chain.insert(qa_index, "FSA-3.1")
                else:
                    chain.append("FSA-3.1")

        # If implementation is needed (medium/high complexity), ensure FSA-2.2 is in the chain
        if complexity in ["medium", "high"] and "FSA-2.2" not in chain:
            # Insert FSA-2.2 after decomposition
            if "FSA-1.2" in chain:
                decomp_index = chain.index("FSA-1.2")
                chain.insert(decomp_index + 1, "FSA-2.2")
            else:
                chain.append("FSA-2.2")

        # Ensure QA is always last
        if "FSA-2.1" in chain:
            chain.remove("FSA-2.1")
            chain.append("FSA-2.1")
        else:
            chain.append("FSA-2.1")

        # Check learning data for better chains
        profile_key = self._getProfileKey(profile)
        if profile_key in self.learning_data["optimal_chains"]:
            learned_chain = self.learning_data["optimal_chains"][profile_key]
            # Use learned chain if it has better performance
            if self._isChainBetter(learned_chain, chain):
                chain = learned_chain

        return chain

    def _getProfileKey(self, profile: Dict[str, Any]) -> str:
        """Generate a key for the task profile for learning purposes."""
        complexity = profile.get("complexity", "unknown")
        task_type = profile.get("task_type", "unknown")
        optimization = profile.get("optimization_needs", {}).get("required", False)
        integration = profile.get("integration_requirements", {}).get("required", False)

        return f"{complexity}_{task_type}_opt:{optimization}_int:{integration}"

    def _isChainBetter(self, chain1: List[str], chain2: List[str]) -> bool:
        """Determine if chain1 performs better than chain2 based on historical data."""
        chain1_key = "->".join(chain1)
        chain2_key = "->".join(chain2)

        chain1_perf = self.performance_stats["chain_performance"].get(chain1_key, {})
        chain2_perf = self.performance_stats["chain_performance"].get(chain2_key, {})

        # If no data for either chain, default to False (keep current)
        if not chain1_perf or not chain2_perf:
            return False

        # Compare based on average execution time and success rate
        chain1_time = chain1_perf.get("avg_time", float('inf'))
        chain2_time = chain2_perf.get("avg_time", float('inf'))
        chain1_success = chain1_perf.get("success_rate", 0)
        chain2_success = chain2_perf.get("success_rate", 0)

        # Prefer chains with higher success rate, then lower execution time
        if chain1_success > chain2_success:
            return True
        elif chain1_success == chain2_success and chain1_time < chain2_time:
            return True

        return False

    def executeFSAChain(
        self,
        chain: List[str],
        task: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute FSA pipeline sequentially.

        Args:
            chain: List of FSA names to execute in order
            task: Task specification
            options: Optional execution options

        Returns:
            Execution results from the FSA chain
        """
        if not chain:
            raise ValueError("Chain cannot be None or empty")
        if not task:
            raise ValueError("Task cannot be None")

        options = options or {}
        results = []
        context = None
        chain_start_time = time.time()

        for fsa_name in chain:
            # Get FSA instance
            fsa = self.fsa_registry.get(fsa_name)
            if not fsa:
                raise ValueError(f"FSA {fsa_name} not found in registry")

            # Execute FSA with context from previous FSA
            try:
                fsa_result = fsa.execute(task, context)
                results.append(fsa_result)

                # Update context for next FSA
                context = fsa_result

            except Exception as e:
                # Handle FSA execution error
                results.append({
                    "fsa": fsa_name,
                    "status": "error",
                    "error": str(e),
                    "execution_time": 0
                })
                break

        chain_end_time = time.time()
        total_chain_time = chain_end_time - chain_start_time

        return {
            "chain": chain,
            "results": results,
            "total_execution_time": total_chain_time,
            "fsa_count": len(chain),
            "successful_fsas": sum(1 for r in results if r.get("status") == "success"),
            "final_context": context
        }

    def learnFromExecution(
        self,
        profile: Dict[str, Any],
        chain: List[str],
        result: Dict[str, Any],
        execution_time: float
    ) -> None:
        """
        Meta-learning from execution patterns.

        Updates performance statistics and learning data based on execution results.

        Args:
            profile: Task profile
            chain: FSA chain that was executed
            result: Execution result
            execution_time: Total execution time
        """
        if not profile or not chain or not result:
            return  # Defensive: skip if any parameter is invalid

        # Update execution history
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "profile": profile,
            "chain": chain,
            "execution_time": execution_time,
            "success": result.get("successful_fsas", 0) == len(chain),
            "result_summary": {
                "total_fsas": result.get("fsa_count", 0),
                "successful_fsas": result.get("successful_fsas", 0)
            }
        }
        self.execution_history.append(execution_record)

        # Update overall performance stats
        self.performance_stats["total_executions"] += 1
        self.performance_stats["total_execution_time"] += execution_time
        self.performance_stats["avg_execution_time"] = (
            self.performance_stats["total_execution_time"] /
            self.performance_stats["total_executions"]
        )

        # Update complexity stats
        complexity = profile.get("complexity", "low")
        if complexity in self.performance_stats["complexity_stats"]:
            comp_stats = self.performance_stats["complexity_stats"][complexity]
            comp_stats["count"] += 1
            comp_stats["total_time"] += execution_time
            comp_stats["avg_time"] = comp_stats["total_time"] / comp_stats["count"]

        # Update task type stats
        task_type = profile.get("task_type", "general")
        if task_type not in self.performance_stats["task_type_stats"]:
            self.performance_stats["task_type_stats"][task_type] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0
            }
        type_stats = self.performance_stats["task_type_stats"][task_type]
        type_stats["count"] += 1
        type_stats["total_time"] += execution_time
        type_stats["avg_time"] = type_stats["total_time"] / type_stats["count"]

        # Update chain performance
        chain_key = "->".join(chain)
        if chain_key not in self.performance_stats["chain_performance"]:
            self.performance_stats["chain_performance"][chain_key] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "successes": 0,
                "success_rate": 0.0
            }
        chain_perf = self.performance_stats["chain_performance"][chain_key]
        chain_perf["count"] += 1
        chain_perf["total_time"] += execution_time
        chain_perf["avg_time"] = chain_perf["total_time"] / chain_perf["count"]
        if execution_record["success"]:
            chain_perf["successes"] += 1
        chain_perf["success_rate"] = chain_perf["successes"] / chain_perf["count"]

        # Update learning data: track optimal chains for task profiles
        profile_key = self._getProfileKey(profile)
        if profile_key not in self.learning_data["optimal_chains"]:
            self.learning_data["optimal_chains"][profile_key] = chain
        else:
            # Update if this chain performed better
            current_optimal = self.learning_data["optimal_chains"][profile_key]
            if self._isChainBetter(chain, current_optimal):
                self.learning_data["optimal_chains"][profile_key] = chain

        # Update chain success rates in learning data
        if chain_key not in self.learning_data["chain_success_rates"]:
            self.learning_data["chain_success_rates"][chain_key] = {
                "successes": 0,
                "total": 0,
                "rate": 0.0
            }
        chain_success = self.learning_data["chain_success_rates"][chain_key]
        chain_success["total"] += 1
        if execution_record["success"]:
            chain_success["successes"] += 1
        chain_success["rate"] = chain_success["successes"] / chain_success["total"]

    def getAnalytics(self) -> Dict[str, Any]:
        """
        Return performance history and learning data.

        Returns:
            Comprehensive analytics including performance stats, execution history,
            and learning data
        """
        return {
            "performance_stats": self.performance_stats,
            "execution_history": self.execution_history,
            "learning_data": self.learning_data,
            "fsa_stats": {
                fsa_name: fsa.get_stats()
                for fsa_name, fsa in self.fsa_registry.items()
            },
            "summary": {
                "total_executions": self.performance_stats["total_executions"],
                "avg_execution_time": self.performance_stats["avg_execution_time"],
                "total_chains_learned": len(self.learning_data["optimal_chains"]),
                "unique_chains_executed": len(self.performance_stats["chain_performance"])
            }
        }
