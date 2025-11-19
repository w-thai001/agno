"""Generated FSA code."""

from typing import Dict, List, Optional, Any


class TrafficLight:
    """
    A simple traffic light FSA that cycles through red, green, and yellow states.
    """

    def __init__(self):
        self.state = "red"  # Initial state
        self.states = ['red', 'yellow', 'green']
        self.transitions = {
            ("red", "timer"): "green",
            ("green", "timer"): "yellow",
            ("yellow", "timer"): "red",
        }
        self.history: List[str] = []
    def transition(self, input_symbol: str) -> bool:
        """
        Perform a state transition based on input.
        
        Args:
            input_symbol: Input symbol to trigger transition
            
        Returns:
            True if transition was successful, False otherwise
        """
        key = (self.state, input_symbol)
        if key in self.transitions:
            self.history.append(self.state)
            self.state = self.transitions[key]
            return True
        return False

    def reset(self) -> None:
        """Reset FSA to initial state."""
        self.state = "red"
        self.history = []

    def get_state(self) -> str:
        """Get current state."""
        return self.state

    def get_history(self) -> List[str]:
        """Get state transition history."""
        return self.history.copy()

    def is_valid_transition(self, input_symbol: str) -> bool:
        """Check if transition is valid from current state."""
        return (self.state, input_symbol) in self.transitions

    def get_available_transitions(self) -> List[str]:
        """Get all available input symbols from current state."""
        return [
            input_sym
            for (state, input_sym) in self.transitions.keys()
            if state == self.state
        ]

    def run(self, inputs: List[str]) -> Dict[str, Any]:
        """
        Run FSA with sequence of inputs.
        
        Args:
            inputs: List of input symbols
            
        Returns:
            Dictionary with final state, success status, and history
        """
        self.reset()
        success = True
        
        for input_symbol in inputs:
            if not self.transition(input_symbol):
                success = False
                break
        
        return {
            "final_state": self.state,
            "success": success,
            "history": self.get_history(),
        }
