"""
Unit tests for Task Parser
"""

import pytest

from agno.fsa_0_1_mla_task_deconstructor.core.task_parser import TaskParser


class TestTaskParser:
    """Test cases for TaskParser"""

    def setup_method(self):
        """Setup test fixtures"""
        self.parser = TaskParser()

    def test_parse_simple_string(self):
        """Test parsing a simple string task"""
        task = "Build a web application"
        result = self.parser.parse(task)

        assert result["description"] == task
        assert result["original_input"] == task
        assert isinstance(result["constraints"], list)
        assert isinstance(result["resources"], list)

    def test_parse_structured_dict(self):
        """Test parsing a structured dictionary"""
        task = {
            "description": "Build a revenue system",
            "constraints": ["$975 budget", "6-day timeline"],
            "available_resources": ["Python", "Claude Code"],
        }

        result = self.parser.parse(task)

        assert result["description"] == "Build a revenue system"
        assert len(result["constraints"]) == 2
        assert len(result["resources"]) == 2

    def test_extract_explicit_goal(self):
        """Test extraction of explicit goal"""
        task = "Build a system. Goal: maximize revenue through automation"
        result = self.parser.parse(task)

        assert result["explicit_goal"] is not None
        assert "revenue" in result["explicit_goal"].lower()

    def test_extract_constraints(self):
        """Test extraction of constraints"""
        task = "Build a system within $1000 budget and 5 days"
        result = self.parser.parse(task)

        # Should extract budget
        assert result["budget"] == 1000.0

    def test_extract_timeline(self):
        """Test extraction of timeline"""
        task = "Complete the project within 3 days"
        result = self.parser.parse(task)

        assert result["timeline"] is not None
        assert "day" in result["timeline"]

    def test_extract_resources(self):
        """Test extraction of resources"""
        task = "Build using Python, Docker, and PostgreSQL"
        result = self.parser.parse(task)

        assert len(result["resources"]) > 0

    def test_extract_task_components(self):
        """Test extraction of task components"""
        task = "1. Setup infrastructure, 2. Build API, 3. Test system"
        parsed = self.parser.parse(task)

        components = self.parser.extract_task_components(parsed)

        assert len(components) >= 3

    def test_identify_action_verbs(self):
        """Test identification of action verbs"""
        text = "Build, create, and test the application"
        verbs = self.parser.identify_action_verbs(text)

        assert "build" in verbs
        assert "create" in verbs
        assert "test" in verbs
