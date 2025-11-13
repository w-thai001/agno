"""
Main interface for FSA-0.1 MLA Task Deconstructor

Orchestrates all components to process tasks and generate MLA-optimized breakdowns.
"""

import json
import uuid
from typing import Any, Dict, List, Union

from agno.fsa_0_1_mla_task_deconstructor.core.decomposer import TaskDecomposer
from agno.fsa_0_1_mla_task_deconstructor.core.goal_analyzer import GoalAnalyzer
from agno.fsa_0_1_mla_task_deconstructor.core.lq_calculator import LQCalculator
from agno.fsa_0_1_mla_task_deconstructor.core.task_parser import TaskParser
from agno.fsa_0_1_mla_task_deconstructor.models.action_model import Action
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal
from agno.fsa_0_1_mla_task_deconstructor.models.mla_framework import MLAFramework
from agno.fsa_0_1_mla_task_deconstructor.utils.context_elicitor import ContextElicitor
from agno.fsa_0_1_mla_task_deconstructor.utils.validators import Validator


class TaskDeconstructionResult:
    """
    Result of task deconstruction with MLA analysis.
    """

    def __init__(
        self,
        task_id: str,
        original_task: str,
        inferred_goal: Goal,
        action_set: List[Action],
        recommended_sequence: List[str],
        context_elicitation: List[str],
        validation: Dict[str, Any],
        parsed_task: Dict[str, Any],
    ):
        self.task_id = task_id
        self.original_task = original_task
        self.inferred_goal = inferred_goal
        self.action_set = action_set
        self.recommended_sequence = recommended_sequence
        self.context_elicitation = context_elicitation
        self.validation = validation
        self.parsed_task = parsed_task

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format (matches spec)"""
        # Get atomic tasks from action decomposition
        atomic_tasks = []
        for action in self.action_set:
            if action.atomic:
                atomic_tasks.append(
                    {
                        "task": action.description,
                        "dependencies": action.dependencies,
                        "LQ_MLA": round(action.calculate_lq_mla(), 2),
                    }
                )
            else:
                # Include subtasks if composite
                for subtask in action.subtasks:
                    atomic_tasks.append(
                        {
                            "task": subtask.description,
                            "dependencies": subtask.dependencies,
                            "LQ_MLA": round(subtask.calculate_lq_mla(), 2),
                        }
                    )

        return {
            "task_id": self.task_id,
            "original_task": self.original_task,
            "inferred_goal": self.inferred_goal.to_dict(),
            "context_elicitation": self.context_elicitation,
            "action_set": [action.to_dict() for action in self.action_set],
            "recommended_sequence": self.recommended_sequence,
            "decomposition": {"atomic_tasks": atomic_tasks},
            "validation": self.validation,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert result to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)

    def print_summary(self):
        """Print a human-readable summary"""
        print("=" * 80)
        print(f"MLA TASK DECONSTRUCTION RESULT")
        print("=" * 80)
        print(f"\nTask ID: {self.task_id}")
        print(f"\nOriginal Task:\n  {self.original_task}")
        print(f"\nInferred Goal:")
        print(f"  G: {self.inferred_goal.G}")
        print(f"  O_G: {self.inferred_goal.O_G}")
        print(f"  Confidence: {self.inferred_goal.confidence:.0%}")
        print(f"  Source: {'Explicit' if self.inferred_goal.explicit else 'Inferred'}")

        if self.context_elicitation:
            print(f"\nClarifying Questions:")
            for i, q in enumerate(self.context_elicitation, 1):
                print(f"  {i}. {q}")

        print(f"\nAction Set (ranked by LQ_MLA):")
        for action in self.action_set:
            lq = action.calculate_lq_mla()
            rank = action.rank or 0
            print(f"  {rank}. [{action.action_id}] LQ={lq:.2f} - {action.description}")
            if action.dependencies:
                print(f"     Dependencies: {', '.join(action.dependencies)}")

        print(f"\nRecommended Sequence:")
        for i, action_id in enumerate(self.recommended_sequence, 1):
            action = next((a for a in self.action_set if a.action_id == action_id), None)
            if action:
                print(f"  {i}. {action_id}: {action.description}")

        print(f"\nValidation:")
        val = self.validation
        print(f"  Goal Alignment: {val.get('goal_alignment_check', 'N/A')}")
        if val.get("risk_assessment"):
            print(f"  Risks:")
            for risk in val["risk_assessment"]:
                print(f"    - {risk}")

        print("=" * 80)


class MLATaskDeconstructor:
    """
    Main interface for MLA Task Deconstructor.

    Processes tasks through the complete MLA pipeline:
    1. Parse input
    2. Analyze and infer goal
    3. Decompose into actions
    4. Calculate LQ_MLA scores
    5. Rank and sequence actions
    6. Validate alignment
    7. Generate structured output
    """

    def __init__(self):
        """Initialize MLA Task Deconstructor"""
        self.task_parser = TaskParser()
        self.goal_analyzer = GoalAnalyzer()
        self.lq_calculator = LQCalculator()
        self.decomposer = TaskDecomposer(lq_calculator=self.lq_calculator)
        self.context_elicitor = ContextElicitor()
        self.validator = Validator()
        self.mla_framework = MLAFramework()

    def process(self, task_input: Union[str, Dict[str, Any]]) -> TaskDeconstructionResult:
        """
        Process a task through the complete MLA pipeline.

        Args:
            task_input: Task description (string or structured dict)

        Returns:
            TaskDeconstructionResult with complete analysis
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]

        # 1. Parse task input
        parsed_task = self.task_parser.parse(task_input)

        # 2. Analyze and infer goal
        goal = self.goal_analyzer.analyze(parsed_task)

        # 3. Generate context elicitation questions
        context_questions = self.goal_analyzer.generate_clarifying_questions(goal, parsed_task)

        # 4. Decompose task into actions
        task_description = parsed_task["description"]
        context = {
            "budget": parsed_task.get("budget"),
            "timeline": parsed_task.get("timeline"),
            "resources": parsed_task.get("resources", []),
        }

        actions = self.decomposer.decompose(task_description, goal, context)

        # 5. Rank actions by LQ_MLA
        ranked_actions = self.mla_framework.rank_actions(actions, goal)

        # 6. Generate optimal sequence
        recommended_sequence = self.mla_framework.optimize_sequence(ranked_actions, goal)

        # 7. Validate goal alignment
        alignment_validation = self.validator.validate_goal_alignment(goal, ranked_actions)

        # 8. Assess risks
        risks = self.validator.assess_risks(goal, ranked_actions, context)

        # 9. Generate validation output
        validation = {
            "goal_alignment_check": alignment_validation.message,
            "risk_assessment": risks,
            "global_context_check": "Alignment validated against MLA v3.0 principles",
            "fractal_alignment": all(
                self.mla_framework.validate_fractal_alignment(a, goal) for a in ranked_actions
            ),
        }

        # Create result
        result = TaskDeconstructionResult(
            task_id=task_id,
            original_task=parsed_task["original_input"],
            inferred_goal=goal,
            action_set=ranked_actions,
            recommended_sequence=recommended_sequence,
            context_elicitation=context_questions,
            validation=validation,
            parsed_task=parsed_task,
        )

        return result

    def process_and_print(self, task_input: Union[str, Dict[str, Any]]):
        """
        Process task and print human-readable summary.

        Args:
            task_input: Task description
        """
        result = self.process(task_input)
        result.print_summary()
        return result

    def process_to_json(self, task_input: Union[str, Dict[str, Any]], indent: int = 2) -> str:
        """
        Process task and return JSON output.

        Args:
            task_input: Task description
            indent: JSON indentation

        Returns:
            JSON string
        """
        result = self.process(task_input)
        return result.to_json(indent=indent)


def main():
    """CLI interface for MLA Task Deconstructor"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FSA-0.1: MLA Task Deconstructor & Goal Aligner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a simple task
  python -m agno.fsa_0_1_mla_task_deconstructor.main "Write a grant proposal for AI edtech"

  # Process with JSON output
  python -m agno.fsa_0_1_mla_task_deconstructor.main --json "Build a revenue system"

  # Process from JSON file
  python -m agno.fsa_0_1_mla_task_deconstructor.main --input task.json
        """,
    )

    parser.add_argument("task", nargs="?", help="Task description (string)")
    parser.add_argument("--input", "-i", help="Input JSON file with task specification")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    args = parser.parse_args()

    # Get task input
    if args.input:
        with open(args.input, "r") as f:
            task_input = json.load(f)
    elif args.task:
        task_input = args.task
    else:
        parser.print_help()
        return

    # Process task
    deconstructor = MLATaskDeconstructor()

    if args.json:
        output = deconstructor.process_to_json(task_input)
    else:
        result = deconstructor.process(task_input)
        result.print_summary()
        output = result.to_json()

    # Write output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\nOutput written to: {args.output}")
    elif args.json:
        print(output)


if __name__ == "__main__":
    main()
