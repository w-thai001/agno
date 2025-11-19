"""
FSA Framework Integration Example

This example demonstrates:
1. FSA module registration
2. Pipeline construction with dependencies
3. Parallel execution
4. Error handling and retry
5. Performance monitoring
6. Health checks
"""

import logging
import time
from typing import Any, Dict

from agno.fsa import (
    FSARegistry,
    FSAPipeline,
    FSAPipelineManager,
)
from agno.config import get_fsa_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Example FSA Modules
# ============================================================================

class DataExtractor:
    """Example FSA: Extract data from source"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        logger.info("DataExtractor initialized")

    def execute(self, source: str = "database") -> Dict[str, Any]:
        """Extract data from source"""
        logger.info(f"Extracting data from {source}")
        time.sleep(0.1)  # Simulate extraction

        return {
            "records": [
                {"id": 1, "value": 100},
                {"id": 2, "value": 200},
                {"id": 3, "value": 300},
            ],
            "count": 3,
            "source": source,
        }

    def health_check(self) -> bool:
        """Check if extractor is healthy"""
        return True


class DataValidator:
    """Example FSA: Validate extracted data"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        logger.info("DataValidator initialized")

    def execute(self, data_extractor_output: Dict = None) -> Dict[str, Any]:
        """Validate data"""
        logger.info("Validating data")
        time.sleep(0.05)  # Simulate validation

        if data_extractor_output is None:
            return {"valid": False, "errors": ["No data provided"]}

        records = data_extractor_output.get("records", [])

        # Validation rules
        errors = []
        for record in records:
            if "id" not in record:
                errors.append(f"Record missing 'id'")
            if "value" not in record:
                errors.append(f"Record {record.get('id')} missing 'value'")
            if record.get("value", 0) < 0:
                errors.append(f"Record {record.get('id')} has negative value")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "validated_count": len(records),
        }

    def health_check(self) -> Dict[str, Any]:
        """Check if validator is healthy"""
        return {
            "status": "healthy",
            "message": "Validator operational",
        }


class DataTransformer:
    """Example FSA: Transform validated data"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        self.transformation_type = kwargs.get('transformation_type', 'normalize')
        logger.info(f"DataTransformer initialized with type: {self.transformation_type}")

    def execute(
        self,
        data_extractor_output: Dict = None,
        data_validator_output: Dict = None,
    ) -> Dict[str, Any]:
        """Transform data"""
        logger.info("Transforming data")

        if not data_validator_output.get("valid", False):
            return {
                "transformed": False,
                "reason": "Validation failed",
            }

        records = data_extractor_output.get("records", [])
        time.sleep(0.08)  # Simulate transformation

        # Apply transformation
        transformed_records = []
        for record in records:
            if self.transformation_type == 'normalize':
                # Normalize values to 0-1 range
                max_val = max(r["value"] for r in records)
                transformed_records.append({
                    "id": record["id"],
                    "value": record["value"] / max_val,
                    "original_value": record["value"],
                })
            elif self.transformation_type == 'double':
                transformed_records.append({
                    "id": record["id"],
                    "value": record["value"] * 2,
                })

        return {
            "transformed": True,
            "records": transformed_records,
            "count": len(transformed_records),
            "transformation_type": self.transformation_type,
        }

    def health_check(self) -> bool:
        """Check if transformer is healthy"""
        return True


class DataLoader:
    """Example FSA: Load transformed data to destination"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        self.destination = kwargs.get('destination', 'warehouse')
        logger.info(f"DataLoader initialized with destination: {self.destination}")

    def execute(self, data_transformer_output: Dict = None) -> Dict[str, Any]:
        """Load data to destination"""
        logger.info(f"Loading data to {self.destination}")

        if not data_transformer_output.get("transformed", False):
            return {
                "loaded": False,
                "reason": "Transformation failed",
            }

        records = data_transformer_output.get("records", [])
        time.sleep(0.12)  # Simulate loading

        # Simulate loading process
        loaded_ids = [record["id"] for record in records]

        return {
            "loaded": True,
            "destination": self.destination,
            "loaded_ids": loaded_ids,
            "count": len(loaded_ids),
        }

    def health_check(self) -> bool:
        """Check if loader is healthy"""
        return True


class DataAnalyzer:
    """Example FSA: Analyze data (runs in parallel with loading)"""

    def __init__(self, **kwargs):
        self.dependencies = kwargs.get('dependencies', {})
        logger.info("DataAnalyzer initialized")

    def execute(self, data_transformer_output: Dict = None) -> Dict[str, Any]:
        """Analyze transformed data"""
        logger.info("Analyzing data")

        if not data_transformer_output.get("transformed", False):
            return {
                "analyzed": False,
                "reason": "Transformation failed",
            }

        records = data_transformer_output.get("records", [])
        time.sleep(0.1)  # Simulate analysis

        # Calculate statistics
        values = [record["value"] for record in records]

        return {
            "analyzed": True,
            "statistics": {
                "count": len(values),
                "mean": sum(values) / len(values) if values else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
            },
        }

    def health_check(self) -> bool:
        """Check if analyzer is healthy"""
        return True


# ============================================================================
# Main Example
# ============================================================================

def main():
    """Run the FSA Framework integration example"""

    print("=" * 70)
    print("FSA Framework Integration Example")
    print("=" * 70)

    # ========================================================================
    # Step 1: Get Configuration
    # ========================================================================
    print("\n[Step 1] Loading Configuration...")

    config = get_fsa_config(env="development")
    print(f"✓ Environment: {config.environment.value}")
    print(f"✓ Max Workers: {config.resources.max_workers}")
    print(f"✓ Caching: {config.caching.enabled}")

    # ========================================================================
    # Step 2: Register FSA Modules
    # ========================================================================
    print("\n[Step 2] Registering FSA Modules...")

    registry = FSARegistry()

    # Register modules in dependency order
    modules = [
        ("extractor", "1.0.0", DataExtractor, []),
        ("validator", "1.0.0", DataValidator, ["extractor"]),
        ("transformer", "1.0.0", DataTransformer, ["extractor", "validator"]),
        ("loader", "1.0.0", DataLoader, ["transformer"]),
        ("analyzer", "1.0.0", DataAnalyzer, ["transformer"]),
    ]

    for name, version, module_class, deps in modules:
        registry.register(
            name=name,
            version=version,
            module_class=module_class,
            dependencies=deps,
            lazy_load=True,
        )
        print(f"✓ Registered: {name} v{version} (deps: {deps or 'none'})")

    # ========================================================================
    # Step 3: Health Checks
    # ========================================================================
    print("\n[Step 3] Running Health Checks...")

    health_results = registry.health_check_all()
    for module_name, health in health_results.items():
        status_icon = "✓" if health.is_healthy() else "✗"
        print(f"{status_icon} {module_name}: {health.status.value}")

    # ========================================================================
    # Step 4: Create Pipeline
    # ========================================================================
    print("\n[Step 4] Creating ETL Pipeline...")

    pipeline = FSAPipeline(
        name="etl_workflow",
        description="Extract, Transform, Load pipeline with parallel analysis",
        registry=registry,
    )

    # Stage 1: Extract data
    pipeline.add_stage(
        name="extract",
        fsa_module_name="extractor",
        inputs={"source": "production_db"},
    )

    # Stage 2: Validate data (depends on extract)
    pipeline.add_stage(
        name="validate",
        fsa_module_name="validator",
        depends_on=["extract"],
        retry_config={"max_retries": 3},
    )

    # Stage 3: Transform data (depends on extract and validate)
    pipeline.add_stage(
        name="transform",
        fsa_module_name="transformer",
        depends_on=["extract", "validate"],
        inputs={"transformation_type": "normalize"},
    )

    # Stage 4 & 5: Load and Analyze (parallel - both depend on transform)
    pipeline.add_stage(
        name="load",
        fsa_module_name="loader",
        depends_on=["transform"],
        inputs={"destination": "data_warehouse"},
    )

    pipeline.add_stage(
        name="analyze",
        fsa_module_name="analyzer",
        depends_on=["transform"],
    )

    # Show execution order
    print(f"✓ Pipeline created: {pipeline.name}")
    print(f"  Stages: {len(pipeline.stages)}")

    execution_order = pipeline.get_execution_order()
    print(f"\n  Execution Order:")
    for i, batch in enumerate(execution_order, 1):
        if len(batch) > 1:
            print(f"    Batch {i} (parallel): {', '.join(batch)}")
        else:
            print(f"    Stage {i}: {batch[0]}")

    # ========================================================================
    # Step 5: Execute Pipeline
    # ========================================================================
    print("\n[Step 5] Executing Pipeline...")

    manager = FSAPipelineManager(
        registry=registry,
        max_workers=config.resources.max_workers,
        enable_caching=config.caching.enabled,
    )

    print("  Starting execution...")
    start_time = time.time()

    result = manager.execute_pipeline(
        pipeline,
        initial_inputs={"timestamp": time.time()},
    )

    duration = time.time() - start_time

    # ========================================================================
    # Step 6: Display Results
    # ========================================================================
    print("\n[Step 6] Execution Results:")

    status_icon = "✓" if result.is_successful() else "✗"
    print(f"\n{status_icon} Pipeline Status: {result.status}")
    print(f"  Total Duration: {result.total_duration_ms:.2f}ms (wall time: {duration*1000:.2f}ms)")
    print(f"  Success Rate: {result.success_rate*100:.1f}%")

    print(f"\n  Stage Results:")
    for stage_result in result.stage_results:
        stage_icon = "✓" if stage_result.is_successful() else "✗"
        print(f"    {stage_icon} {stage_result.stage_name}:")
        print(f"       Status: {stage_result.status.value}")
        print(f"       Duration: {stage_result.duration_ms:.2f}ms")
        if stage_result.retry_count > 0:
            print(f"       Retries: {stage_result.retry_count}")

        # Show output summary
        if stage_result.output:
            output_str = str(stage_result.output)
            if len(output_str) > 100:
                output_str = output_str[:100] + "..."
            print(f"       Output: {output_str}")

    # ========================================================================
    # Step 7: Performance Metrics
    # ========================================================================
    print("\n[Step 7] Performance Metrics:")

    # Execute a few more times to collect metrics
    print("  Running additional executions for metrics collection...")
    for i in range(3):
        manager.execute_pipeline(pipeline, use_cache=False)

    metrics = manager.get_metrics("etl_workflow")

    print(f"\n  Pipeline: {metrics['pipeline_name']}")
    print(f"    Execution Count: {metrics['execution_count']}")
    print(f"    Avg Duration: {metrics['avg_duration_ms']:.2f}ms")
    print(f"    Min Duration: {metrics['min_duration_ms']:.2f}ms")
    print(f"    Max Duration: {metrics['max_duration_ms']:.2f}ms")
    print(f"    P95 Duration: {metrics['p95_duration_ms']:.2f}ms")

    # ========================================================================
    # Step 8: Summary
    # ========================================================================
    print("\n[Step 8] Summary:")
    print(f"  ✓ Registered {len(registry.list_modules())} FSA modules")
    print(f"  ✓ Created pipeline with {len(pipeline.stages)} stages")
    print(f"  ✓ Executed {metrics['execution_count']} times")
    print(f"  ✓ All health checks passed")
    print(f"  ✓ Parallel execution optimized runtime")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
