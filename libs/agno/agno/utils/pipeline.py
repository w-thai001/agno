"""Data Pipeline FSA - simple state machine for data processing pipelines."""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PipelineState(Enum):
    """Pipeline execution states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineResult:
    """Result of pipeline execution"""
    def __init__(self, data: Any = None, state: PipelineState = PipelineState.PENDING):
        self.data = data
        self.state = state
        self.error: Optional[str] = None
        self.stage_results: List[Dict[str, Any]] = []

    def is_success(self) -> bool:
        return self.state == PipelineState.COMPLETED

    def to_dict(self) -> dict:
        return {"data": self.data, "state": self.state.value, "error": self.error, "stages": self.stage_results}


class DataPipelineFSA:
    """Finite State Automaton for data pipeline processing"""

    def __init__(self):
        self.stages: List[tuple[str, Callable]] = []
        self.state = PipelineState.PENDING
        self.current_stage = 0

    def add_stage(self, name: str, transform: Callable[[Any], Any]) -> "DataPipelineFSA":
        """Add processing stage to pipeline"""
        self.stages.append((name, transform))
        return self

    def process(self, data: Any) -> PipelineResult:
        """Execute pipeline on input data"""
        result = PipelineResult(data, PipelineState.PROCESSING)
        self.state = PipelineState.PROCESSING
        self.current_stage = 0

        try:
            current_data = data
            for stage_name, transform in self.stages:
                self.current_stage += 1
                stage_input = current_data
                current_data = transform(current_data)
                result.stage_results.append({"stage": stage_name, "input": stage_input, "output": current_data})

            result.data = current_data
            result.state = PipelineState.COMPLETED
            self.state = PipelineState.COMPLETED
        except Exception as e:
            result.state = PipelineState.FAILED
            result.error = str(e)
            self.state = PipelineState.FAILED

        return result

    def reset(self):
        """Reset pipeline state"""
        self.state = PipelineState.PENDING
        self.current_stage = 0


# Convenience function
def create_pipeline(*stages: tuple[str, Callable]) -> DataPipelineFSA:
    """Create pipeline with stages"""
    pipeline = DataPipelineFSA()
    for name, transform in stages:
        pipeline.add_stage(name, transform)
    return pipeline
