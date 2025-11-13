"""
Task Parser for MLA Framework

Parses natural language task inputs and extracts structured information.
"""

import re
from typing import Any, Dict, List, Optional, Union


class TaskParser:
    """
    Parses task descriptions (natural language or structured) and extracts:
    - Task description
    - Explicit goals (if stated)
    - Constraints
    - Available resources/tools
    - Context
    """

    def __init__(self):
        """Initialize task parser"""
        pass

    def parse(self, task_input: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse task input into structured format.

        Args:
            task_input: Either a string (natural language) or dict (structured)

        Returns:
            Parsed task data with keys:
            - description: Main task description
            - explicit_goal: Explicitly stated goal (if any)
            - constraints: List of constraints
            - resources: List of available resources
            - context: Additional context
            - original_input: Original input verbatim
        """
        if isinstance(task_input, dict):
            return self._parse_structured(task_input)
        elif isinstance(task_input, str):
            return self._parse_natural_language(task_input)
        else:
            raise ValueError(f"Unsupported task input type: {type(task_input)}")

    def _parse_structured(self, task_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse structured task dictionary.

        Args:
            task_dict: Structured task input

        Returns:
            Parsed task data
        """
        return {
            "description": task_dict.get("description", ""),
            "explicit_goal": task_dict.get("goal"),
            "constraints": task_dict.get("constraints", []),
            "resources": task_dict.get("available_resources", []),
            "context": task_dict.get("context"),
            "original_input": str(task_dict),
            "success_criteria": task_dict.get("success_criteria", []),
            "timeline": task_dict.get("timeline"),
            "budget": task_dict.get("budget"),
        }

    def _parse_natural_language(self, task_text: str) -> Dict[str, Any]:
        """
        Parse natural language task description.

        Uses pattern matching and heuristics to extract structured information.

        Args:
            task_text: Natural language task description

        Returns:
            Parsed task data
        """
        parsed = {
            "description": task_text.strip(),
            "explicit_goal": None,
            "constraints": [],
            "resources": [],
            "context": None,
            "original_input": task_text,
            "success_criteria": [],
            "timeline": None,
            "budget": None,
        }

        # Extract explicit goal if stated
        goal_patterns = [
            r"(?:goal|objective|aim|purpose)(?:\s+is)?:?\s*(.+?)(?:\.|$)",
            r"(?:want to|need to|should)\s+(.+?)(?:\.|$)",
            r"in order to\s+(.+?)(?:\.|$)",
        ]

        for pattern in goal_patterns:
            match = re.search(pattern, task_text, re.IGNORECASE)
            if match:
                parsed["explicit_goal"] = match.group(1).strip()
                break

        # Extract constraints
        constraint_patterns = [
            r"(?:constraint|limitation|within|limited to|must)(?:\s+is)?:?\s*(.+?)(?:\.|$)",
            r"\$(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:budget|limit|cap)",
            r"(\d+)\s*(?:day|week|month|hour)(?:s)?\s*(?:timeline|timeframe|deadline)",
        ]

        for pattern in constraint_patterns:
            matches = re.findall(pattern, task_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = " ".join(match)
                if match and match.strip():
                    parsed["constraints"].append(match.strip())

        # Extract timeline
        timeline_patterns = [
            r"(?:within|in)\s+(\d+)\s+(day|week|month|hour)s?",
            r"(\d+)[-\s](day|week|month|hour)\s+(?:timeline|timeframe|deadline)",
        ]

        for pattern in timeline_patterns:
            match = re.search(pattern, task_text, re.IGNORECASE)
            if match:
                parsed["timeline"] = f"{match.group(1)} {match.group(2)}s"
                break

        # Extract budget
        budget_patterns = [
            r"\$(\d+(?:,\d+)*(?:\.\d+)?)",
            r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:dollars|USD)",
        ]

        for pattern in budget_patterns:
            match = re.search(pattern, task_text, re.IGNORECASE)
            if match:
                budget_value = match.group(1).replace(",", "")
                parsed["budget"] = float(budget_value)
                break

        # Extract resources/tools
        resource_patterns = [
            r"(?:using|with|available|have)\s+(.+?)(?:to|for|and|\.|$)",
            r"(?:tools?|resources?):?\s*(.+?)(?:\.|$)",
        ]

        for pattern in resource_patterns:
            match = re.search(pattern, task_text, re.IGNORECASE)
            if match:
                resources_text = match.group(1).strip()
                # Split by common delimiters
                resources = re.split(r"[,;&]|\s+and\s+", resources_text)
                parsed["resources"].extend([r.strip() for r in resources if r.strip()])

        # Extract success criteria
        success_patterns = [
            r"(?:success|done|complete)(?:\s+when|\s+if)?:?\s*(.+?)(?:\.|$)",
            r"should\s+(?:result in|produce|create)\s+(.+?)(?:\.|$)",
        ]

        for pattern in success_patterns:
            match = re.search(pattern, task_text, re.IGNORECASE)
            if match:
                parsed["success_criteria"].append(match.group(1).strip())

        return parsed

    def extract_task_components(self, parsed_task: Dict[str, Any]) -> List[str]:
        """
        Extract individual task components from description.

        This identifies sub-tasks or components within the main task description.

        Args:
            parsed_task: Parsed task data

        Returns:
            List of identified task components
        """
        description = parsed_task["description"]
        components = []

        # Look for enumerated lists
        # Pattern 1: "1. task, 2. task, 3. task"
        numbered_pattern = r"(?:\d+\.|\d+\))\s*([^,;.]+)"
        numbered_matches = re.findall(numbered_pattern, description)
        if numbered_matches:
            components.extend([m.strip() for m in numbered_matches])

        # Pattern 2: "first ... then ... finally ..."
        sequence_pattern = r"(?:first|then|next|after|finally|lastly),?\s*(.+?)(?=\s+(?:first|then|next|after|finally|lastly|and|$))"
        sequence_matches = re.findall(sequence_pattern, description, re.IGNORECASE)
        if sequence_matches and not numbered_matches:
            components.extend([m.strip() for m in sequence_matches])

        # Pattern 3: Actions separated by "and"
        if not components:
            and_pattern = r"([^,;.]+?)\s+and\s+"
            and_matches = re.findall(and_pattern, description)
            if len(and_matches) >= 2:
                components.extend([m.strip() for m in and_matches])

        # If no pattern matched, return the whole description as single component
        if not components:
            components = [description]

        return components

    def identify_action_verbs(self, text: str) -> List[str]:
        """
        Identify action verbs in text.

        Args:
            text: Text to analyze

        Returns:
            List of action verbs found
        """
        # Common action verbs in task descriptions
        action_verbs = [
            "build", "create", "write", "develop", "implement", "design",
            "analyze", "research", "investigate", "test", "validate",
            "deploy", "configure", "setup", "install", "integrate",
            "optimize", "refactor", "improve", "enhance", "fix",
            "document", "review", "evaluate", "plan", "organize",
        ]

        found_verbs = []
        text_lower = text.lower()

        for verb in action_verbs:
            if re.search(r"\b" + verb + r"\b", text_lower):
                found_verbs.append(verb)

        return found_verbs
