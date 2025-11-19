"""Unit tests for Data Pipeline FSA"""

import pytest

from agno.utils.pipeline import DataPipelineFSA, PipelineState, create_pipeline


class TestDataPipelineFSA:
    """Test Data Pipeline FSA functionality"""

    def test_simple_string_pipeline(self):
        """Test basic string transformation pipeline"""
        pipeline = DataPipelineFSA()
        pipeline.add_stage("uppercase", lambda x: x.upper())
        pipeline.add_stage("add_prefix", lambda x: f"PROCESSED: {x}")

        result = pipeline.process("hello")

        assert result.is_success() is True
        assert result.state == PipelineState.COMPLETED
        assert result.data == "PROCESSED: HELLO"
        assert len(result.stage_results) == 2

    def test_numeric_pipeline(self):
        """Test numeric transformation pipeline"""
        pipeline = create_pipeline(
            ("multiply", lambda x: x * 2),
            ("add", lambda x: x + 10),
            ("square", lambda x: x**2),
        )

        result = pipeline.process(5)

        assert result.is_success() is True
        assert result.data == 400  # ((5 * 2) + 10) ** 2
        assert result.stage_results[0]["output"] == 10
        assert result.stage_results[1]["output"] == 20
        assert result.stage_results[2]["output"] == 400

    def test_list_processing_pipeline(self):
        """Test list processing pipeline"""
        pipeline = create_pipeline(
            ("filter_even", lambda x: [i for i in x if i % 2 == 0]),
            ("double", lambda x: [i * 2 for i in x]),
            ("sum", lambda x: sum(x)),
        )

        result = pipeline.process([1, 2, 3, 4, 5, 6])

        assert result.is_success() is True
        assert result.data == 24  # sum([4, 8, 12])

    def test_error_handling(self):
        """Test pipeline error handling"""
        pipeline = DataPipelineFSA()
        pipeline.add_stage("parse_int", lambda x: int(x))
        pipeline.add_stage("divide", lambda x: 100 / x)

        result = pipeline.process("not_a_number")

        assert result.is_success() is False
        assert result.state == PipelineState.FAILED
        assert result.error is not None
        assert "invalid literal" in result.error

    def test_division_by_zero_error(self):
        """Test division by zero error handling"""
        pipeline = create_pipeline(("divide", lambda x: 100 / x))

        result = pipeline.process(0)

        assert result.state == PipelineState.FAILED
        assert "division by zero" in result.error

    def test_chaining_stages(self):
        """Test method chaining for adding stages"""
        pipeline = (
            DataPipelineFSA()
            .add_stage("step1", lambda x: x + 1)
            .add_stage("step2", lambda x: x * 2)
            .add_stage("step3", lambda x: x - 5)
        )

        result = pipeline.process(10)

        assert result.is_success() is True
        assert result.data == 17  # ((10 + 1) * 2) - 5

    def test_empty_pipeline(self):
        """Test pipeline with no stages"""
        pipeline = DataPipelineFSA()
        result = pipeline.process("test_data")

        assert result.is_success() is True
        assert result.data == "test_data"
        assert len(result.stage_results) == 0

    def test_stage_results_tracking(self):
        """Test that stage results are properly tracked"""
        pipeline = create_pipeline(
            ("add_one", lambda x: x + 1),
            ("multiply_two", lambda x: x * 2),
        )

        result = pipeline.process(5)

        assert len(result.stage_results) == 2
        assert result.stage_results[0]["stage"] == "add_one"
        assert result.stage_results[0]["input"] == 5
        assert result.stage_results[0]["output"] == 6
        assert result.stage_results[1]["stage"] == "multiply_two"
        assert result.stage_results[1]["input"] == 6
        assert result.stage_results[1]["output"] == 12

    def test_pipeline_reset(self):
        """Test pipeline reset functionality"""
        pipeline = DataPipelineFSA()
        pipeline.add_stage("test", lambda x: x)
        pipeline.process("data")

        assert pipeline.state == PipelineState.COMPLETED
        assert pipeline.current_stage > 0

        pipeline.reset()

        assert pipeline.state == PipelineState.PENDING
        assert pipeline.current_stage == 0

    def test_result_to_dict(self):
        """Test PipelineResult to_dict method"""
        pipeline = create_pipeline(("double", lambda x: x * 2))
        result = pipeline.process(5)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["data"] == 10
        assert result_dict["state"] == "completed"
        assert result_dict["error"] is None
        assert len(result_dict["stages"]) == 1

    def test_dict_transformation_pipeline(self):
        """Test pipeline with dictionary transformations"""
        pipeline = create_pipeline(
            ("add_field", lambda x: {**x, "processed": True}),
            ("uppercase_name", lambda x: {**x, "name": x["name"].upper()}),
            ("add_count", lambda x: {**x, "count": len(x["name"])}),
        )

        result = pipeline.process({"name": "john"})

        assert result.is_success() is True
        assert result.data["name"] == "JOHN"
        assert result.data["processed"] is True
        assert result.data["count"] == 4

    def test_complex_data_structure(self):
        """Test pipeline with complex nested data"""
        pipeline = create_pipeline(
            ("extract_values", lambda x: [item["value"] for item in x]),
            ("filter_positive", lambda x: [v for v in x if v > 0]),
            ("calculate_average", lambda x: sum(x) / len(x) if x else 0),
        )

        data = [{"value": 10}, {"value": -5}, {"value": 20}, {"value": 30}]
        result = pipeline.process(data)

        assert result.is_success() is True
        assert result.data == 20.0  # average of [10, 20, 30]
