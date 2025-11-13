"""
FSA-0.1: MLA Task Deconstructor & Goal Aligner

A Python-based system that receives a user task/goal and applies the MLA
(Maximized Leverage Action) framework to:
1. Decompose the task into fundamental components
2. Infer or validate the optimal goal G
3. Identify the action set S
4. Calculate LQ_MLA scores for potential approaches
5. Output a structured, actionable task breakdown

LQ_MLA Score: 95.7 (Highest priority foundational FSA)
Tier: 0 (Foundation)
"""

from agno.fsa_0_1_mla_task_deconstructor.main import MLATaskDeconstructor
from agno.fsa_0_1_mla_task_deconstructor.models.action_model import Action
from agno.fsa_0_1_mla_task_deconstructor.models.goal_model import Goal
from agno.fsa_0_1_mla_task_deconstructor.models.mla_framework import MLAFramework

__all__ = [
    "MLATaskDeconstructor",
    "Action",
    "Goal",
    "MLAFramework",
]

__version__ = "0.1.0"
