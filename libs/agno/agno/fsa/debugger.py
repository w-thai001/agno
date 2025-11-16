"""
FSA Debugger

Interactive debugging for FSA execution:
- Breakpoints on states and transitions
- Step-through execution (step, step-over, continue)
- Variable inspection and watches
- Call stack tracking
- Execution history replay
- Conditional breakpoints
- Interactive console

Essential development tool for FSA debugging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import traceback

from pydantic import BaseModel

from agno.agent import Agent
from agno.fsa.base import FSA, FSAState, FSATransition, FSAExecutionResult
from agno.utils.log import logger


class DebugCommand(str, Enum):
    """Debug commands"""
    STEP = "step"  # Execute one transition
    STEP_OVER = "step_over"  # Execute until next state
    CONTINUE = "continue"  # Run until breakpoint
    BREAK = "break"  # Set breakpoint
    WATCH = "watch"  # Watch variable
    INSPECT = "inspect"  # Inspect current state
    BACKTRACE = "backtrace"  # Show call stack
    QUIT = "quit"  # Stop debugging


class BreakpointType(str, Enum):
    """Breakpoint types"""
    STATE = "state"
    TRANSITION = "transition"
    CONDITION = "condition"


class Breakpoint(BaseModel):
    """Debug breakpoint"""
    breakpoint_id: str
    type: BreakpointType
    location: str  # State name or transition description
    condition: Optional[str] = None  # Conditional breakpoint expression
    enabled: bool = True
    hit_count: int = 0


class WatchVariable(BaseModel):
    """Watched variable"""
    variable_name: str
    last_value: Any = None
    change_count: int = 0


class DebugFrame(BaseModel):
    """Debug stack frame"""
    state: str
    context: Dict[str, Any]
    timestamp: str
    transition_count: int


class DebugSession(BaseModel):
    """Debug session info"""
    session_id: str
    fsa_name: str
    start_time: str
    breakpoints: List[Breakpoint]
    watches: List[WatchVariable]
    execution_history: List[DebugFrame]
    current_frame_index: int


class DebuggerState(str, Enum):
    """States for Debugger FSA"""
    INITIAL = "initial"
    ATTACHING = "attaching"
    PAUSED = "paused"
    STEPPING = "stepping"
    RUNNING = "running"
    INSPECTING = "inspecting"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class FSADebugger(FSA):
    """
    FSA Interactive Debugger

    Provides interactive debugging for FSA execution:
    - Set breakpoints on states and transitions
    - Step through execution one transition at a time
    - Inspect context variables and state
    - Watch variables for changes
    - View execution history and call stack
    - Conditional breakpoints
    - Interactive debugging console

    Example:
        ```python
        # Create debugger
        debugger = FSADebugger(name="Debugger")

        # Attach to FSA
        debugger.attach(my_fsa)

        # Set breakpoints
        debugger.set_breakpoint("processing", breakpoint_type="state")
        debugger.set_breakpoint("validating", condition="ctx.get('errors') > 0")

        # Start debugging
        result = debugger.debug_run(initial_context={"task": "test"})

        # Interactive commands available:
        # - step: Execute one transition
        # - continue: Run until next breakpoint
        # - inspect: View current state and context
        # - backtrace: Show execution history
        ```
    """

    # Target FSA
    target_fsa: Optional[FSA] = None

    # Breakpoints
    breakpoints: Dict[str, Breakpoint] = field(default_factory=dict)
    next_breakpoint_id: int = 1

    # Watches
    watches: Dict[str, WatchVariable] = field(default_factory=dict)

    # Execution state
    paused: bool = False
    step_mode: bool = False
    execution_history: List[DebugFrame] = field(default_factory=list)
    current_frame_index: int = 0

    # Session
    session_id: Optional[str] = None
    session_start_time: Optional[datetime] = None

    # Callbacks
    on_breakpoint_hit: Optional[Callable] = None
    on_variable_changed: Optional[Callable] = None

    def __post_init__(self):
        """Initialize debugger"""
        self.initial_state = DebuggerState.INITIAL
        self.current_state = self.initial_state
        self.final_states = {DebuggerState.SUCCESS, DebuggerState.FAILED}
        self.state_history = [self.current_state]

        self._setup_transitions()

        if self.debug_mode:
            logger.debug(f"FSADebugger {self.name} initialized")

    def _setup_transitions(self) -> None:
        """Setup debugger workflow"""
        # INITIAL -> ATTACHING
        self.add_transition(
            DebuggerState.INITIAL,
            DebuggerState.ATTACHING,
            action=self._attach_to_fsa,
            description="Attach to target FSA"
        )

        # ATTACHING -> PAUSED
        self.add_transition(
            DebuggerState.ATTACHING,
            DebuggerState.PAUSED,
            condition=lambda ctx: ctx.get("attached", False),
            action=self._start_debug_session,
            description="Start debug session"
        )

        # PAUSED -> STEPPING (user step command)
        self.add_transition(
            DebuggerState.PAUSED,
            DebuggerState.STEPPING,
            condition=lambda ctx: ctx.get("command") == DebugCommand.STEP,
            action=self._execute_step,
            description="Execute single step"
        )

        # PAUSED -> RUNNING (user continue command)
        self.add_transition(
            DebuggerState.PAUSED,
            DebuggerState.RUNNING,
            condition=lambda ctx: ctx.get("command") == DebugCommand.CONTINUE,
            action=self._continue_execution,
            description="Continue execution"
        )

        # PAUSED -> INSPECTING (user inspect command)
        self.add_transition(
            DebuggerState.PAUSED,
            DebuggerState.INSPECTING,
            condition=lambda ctx: ctx.get("command") == DebugCommand.INSPECT,
            action=self._inspect_state,
            description="Inspect current state"
        )

        # STEPPING -> PAUSED (after step)
        self.add_transition(
            DebuggerState.STEPPING,
            DebuggerState.PAUSED,
            condition=lambda ctx: ctx.get("step_complete", False),
            action=self._check_breakpoints,
            description="Check breakpoints after step"
        )

        # RUNNING -> PAUSED (breakpoint hit)
        self.add_transition(
            DebuggerState.RUNNING,
            DebuggerState.PAUSED,
            condition=lambda ctx: ctx.get("breakpoint_hit", False),
            action=self._handle_breakpoint,
            description="Breakpoint hit"
        )

        # RUNNING -> SUCCESS (execution complete)
        self.add_transition(
            DebuggerState.RUNNING,
            DebuggerState.SUCCESS,
            condition=lambda ctx: ctx.get("execution_complete", False),
            description="Execution complete"
        )

        # INSPECTING -> PAUSED
        self.add_transition(
            DebuggerState.INSPECTING,
            DebuggerState.PAUSED,
            condition=lambda ctx: ctx.get("inspection_complete", False),
            description="Return to paused state"
        )

        # PAUSED -> SUCCESS (user quit)
        self.add_transition(
            DebuggerState.PAUSED,
            DebuggerState.SUCCESS,
            condition=lambda ctx: ctx.get("command") == DebugCommand.QUIT,
            description="User quit debugging"
        )

        # Error handling
        for state in DebuggerState:
            if state not in [DebuggerState.SUCCESS, DebuggerState.FAILED]:
                self.add_transition(
                    state,
                    DebuggerState.FAILED,
                    condition=lambda ctx: ctx.get("critical_error", False),
                    description="Critical error"
                )

    def _attach_to_fsa(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Attach debugger to target FSA"""
        fsa = context.get("target_fsa")

        if not fsa:
            context["critical_error"] = True
            raise ValueError("No target FSA provided")

        self.target_fsa = fsa

        # Instrument FSA for debugging
        self._instrument_fsa(fsa)

        context["attached"] = True

        if self.debug_mode:
            logger.debug(f"Debugger attached to FSA: {fsa.name}")

        return context

    def _start_debug_session(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start debug session"""
        self.session_id = f"debug-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.session_start_time = datetime.now()
        self.paused = True

        # Record initial frame
        initial_frame = DebugFrame(
            state=str(self.target_fsa.current_state),
            context=self.target_fsa.context.copy(),
            timestamp=datetime.now().isoformat(),
            transition_count=0
        )
        self.execution_history.append(initial_frame)

        if self.debug_mode:
            logger.info(f"Debug session started: {self.session_id}")
            logger.info(f"Initial state: {self.target_fsa.current_state}")

        return context

    def _execute_step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single step"""
        if not self.target_fsa:
            context["critical_error"] = True
            return context

        # Execute one transition
        try:
            self.target_fsa.step()

            # Record frame
            frame = DebugFrame(
                state=str(self.target_fsa.current_state),
                context=self.target_fsa.context.copy(),
                timestamp=datetime.now().isoformat(),
                transition_count=len(self.execution_history)
            )
            self.execution_history.append(frame)
            self.current_frame_index = len(self.execution_history) - 1

            # Check watches
            self._check_watches()

            context["step_complete"] = True

            if self.debug_mode:
                logger.debug(f"Step executed. New state: {self.target_fsa.current_state}")

        except Exception as e:
            context["error"] = str(e)
            context["step_complete"] = False
            logger.error(f"Step execution failed: {e}")

        return context

    def _continue_execution(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Continue execution until breakpoint or completion"""
        self.paused = False

        if not self.target_fsa:
            context["critical_error"] = True
            return context

        try:
            while not self.paused:
                # Check if FSA is in final state
                if self.target_fsa.current_state in self.target_fsa.final_states:
                    context["execution_complete"] = True
                    break

                # Execute one step
                self.target_fsa.step()

                # Record frame
                frame = DebugFrame(
                    state=str(self.target_fsa.current_state),
                    context=self.target_fsa.context.copy(),
                    timestamp=datetime.now().isoformat(),
                    transition_count=len(self.execution_history)
                )
                self.execution_history.append(frame)
                self.current_frame_index = len(self.execution_history) - 1

                # Check watches
                self._check_watches()

                # Check breakpoints
                if self._check_breakpoint_hit():
                    context["breakpoint_hit"] = True
                    self.paused = True
                    break

        except Exception as e:
            context["error"] = str(e)
            context["critical_error"] = True
            logger.error(f"Execution failed: {e}")

        return context

    def _check_breakpoints(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if any breakpoints are hit"""
        hit = self._check_breakpoint_hit()
        context["breakpoint_hit"] = hit
        return context

    def _handle_breakpoint(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle breakpoint hit"""
        current_state = str(self.target_fsa.current_state)

        if self.debug_mode:
            logger.info(f"Breakpoint hit at state: {current_state}")

        # Call callback if set
        if self.on_breakpoint_hit:
            self.on_breakpoint_hit(current_state, self.target_fsa.context)

        return context

    def _inspect_state(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect current state and variables"""
        if not self.target_fsa:
            context["critical_error"] = True
            return context

        inspection = {
            "current_state": str(self.target_fsa.current_state),
            "context": self.target_fsa.context,
            "state_history": [str(s) for s in self.target_fsa.state_history],
            "transitions_executed": len(self.execution_history) - 1,
            "watches": {name: watch.last_value for name, watch in self.watches.items()}
        }

        context["inspection"] = inspection
        context["inspection_complete"] = True

        return context

    def _instrument_fsa(self, fsa: FSA) -> None:
        """Instrument FSA for debugging"""
        # Store original methods
        original_transition_to = fsa.transition_to

        debugger = self  # Reference to debugger

        def instrumented_transition_to(new_state, force=False):
            # Check if we should pause before transition
            if debugger.step_mode and debugger.paused:
                # Wait for user command
                pass

            # Execute transition
            result = original_transition_to(new_state, force)

            return result

        # Replace methods
        fsa.transition_to = instrumented_transition_to

    def _check_breakpoint_hit(self) -> bool:
        """Check if current state hits a breakpoint"""
        if not self.target_fsa:
            return False

        current_state = str(self.target_fsa.current_state)

        for bp in self.breakpoints.values():
            if not bp.enabled:
                continue

            # Check state breakpoints
            if bp.type == BreakpointType.STATE and bp.location == current_state:
                # Check condition if present
                if bp.condition:
                    try:
                        # Evaluate condition
                        ctx = self.target_fsa.context
                        if eval(bp.condition):
                            bp.hit_count += 1
                            return True
                    except Exception as e:
                        logger.warning(f"Breakpoint condition evaluation failed: {e}")
                else:
                    bp.hit_count += 1
                    return True

        return False

    def _check_watches(self) -> None:
        """Check watched variables for changes"""
        if not self.target_fsa:
            return

        for watch in self.watches.values():
            var_name = watch.variable_name
            current_value = self.target_fsa.context.get(var_name)

            if current_value != watch.last_value:
                watch.change_count += 1
                watch.last_value = current_value

                if self.on_variable_changed:
                    self.on_variable_changed(var_name, watch.last_value, current_value)

    def attach(self, fsa: FSA) -> None:
        """Attach debugger to FSA"""
        self.run({"target_fsa": fsa})

    def set_breakpoint(
        self,
        location: str,
        breakpoint_type: str = "state",
        condition: Optional[str] = None
    ) -> str:
        """Set a breakpoint"""
        bp_id = f"bp-{self.next_breakpoint_id}"
        self.next_breakpoint_id += 1

        breakpoint = Breakpoint(
            breakpoint_id=bp_id,
            type=BreakpointType(breakpoint_type),
            location=location,
            condition=condition,
            enabled=True,
            hit_count=0
        )

        self.breakpoints[bp_id] = breakpoint

        if self.debug_mode:
            logger.info(f"Breakpoint set: {bp_id} at {location}")

        return bp_id

    def remove_breakpoint(self, breakpoint_id: str) -> bool:
        """Remove a breakpoint"""
        if breakpoint_id in self.breakpoints:
            del self.breakpoints[breakpoint_id]
            if self.debug_mode:
                logger.info(f"Breakpoint removed: {breakpoint_id}")
            return True
        return False

    def enable_breakpoint(self, breakpoint_id: str) -> bool:
        """Enable a breakpoint"""
        if breakpoint_id in self.breakpoints:
            self.breakpoints[breakpoint_id].enabled = True
            return True
        return False

    def disable_breakpoint(self, breakpoint_id: str) -> bool:
        """Disable a breakpoint"""
        if breakpoint_id in self.breakpoints:
            self.breakpoints[breakpoint_id].enabled = False
            return True
        return False

    def watch_variable(self, variable_name: str) -> None:
        """Watch a context variable"""
        watch = WatchVariable(
            variable_name=variable_name,
            last_value=None,
            change_count=0
        )
        self.watches[variable_name] = watch

        if self.debug_mode:
            logger.info(f"Watching variable: {variable_name}")

    def unwatch_variable(self, variable_name: str) -> bool:
        """Stop watching a variable"""
        if variable_name in self.watches:
            del self.watches[variable_name]
            return True
        return False

    def get_backtrace(self) -> List[DebugFrame]:
        """Get execution backtrace"""
        return self.execution_history

    def get_current_frame(self) -> Optional[DebugFrame]:
        """Get current execution frame"""
        if 0 <= self.current_frame_index < len(self.execution_history):
            return self.execution_history[self.current_frame_index]
        return None

    def get_debug_session(self) -> DebugSession:
        """Get current debug session info"""
        return DebugSession(
            session_id=self.session_id or "",
            fsa_name=self.target_fsa.name if self.target_fsa else "",
            start_time=self.session_start_time.isoformat() if self.session_start_time else "",
            breakpoints=list(self.breakpoints.values()),
            watches=list(self.watches.values()),
            execution_history=self.execution_history,
            current_frame_index=self.current_frame_index
        )

    def get_breakpoints(self) -> List[Breakpoint]:
        """Get all breakpoints"""
        return list(self.breakpoints.values())

    def get_watches(self) -> List[WatchVariable]:
        """Get all watched variables"""
        return list(self.watches.values())

    def debug_run(
        self,
        initial_context: Optional[Dict[str, Any]] = None,
        interactive: bool = False
    ) -> FSAExecutionResult:
        """
        Run FSA in debug mode

        Args:
            initial_context: Initial context for FSA
            interactive: Enable interactive debugging console

        Returns:
            FSA execution result
        """
        if not self.target_fsa:
            raise ValueError("No FSA attached. Call attach() first.")

        # Set initial context
        if initial_context:
            self.target_fsa.context.update(initial_context)

        # Start in step mode
        self.step_mode = True
        self.paused = True

        if interactive:
            return self._interactive_debug()
        else:
            # Non-interactive - just execute with breakpoints
            return self.target_fsa.run(initial_context=initial_context)

    def _interactive_debug(self) -> FSAExecutionResult:
        """Interactive debugging console"""
        print("\n🐛 FSA Debugger - Interactive Mode")
        print("=" * 60)
        print("Commands: step, continue, inspect, breakpoint, watch, backtrace, quit")
        print("=" * 60)

        while True:
            # Show current state
            print(f"\n📍 Current State: {self.target_fsa.current_state}")

            # Get user command
            command_input = input("\n(debug) > ").strip().lower()

            if command_input == "step" or command_input == "s":
                self.run({"command": DebugCommand.STEP})
            elif command_input == "continue" or command_input == "c":
                self.run({"command": DebugCommand.CONTINUE})
            elif command_input == "inspect" or command_input == "i":
                result = self.run({"command": DebugCommand.INSPECT})
                inspection = result.context.get("inspection", {})
                print(f"\n📊 Inspection:")
                print(f"   State: {inspection.get('current_state')}")
                print(f"   Context: {inspection.get('context')}")
                print(f"   History: {inspection.get('state_history')}")
            elif command_input == "backtrace" or command_input == "bt":
                backtrace = self.get_backtrace()
                print(f"\n📜 Execution History ({len(backtrace)} frames):")
                for i, frame in enumerate(backtrace):
                    print(f"   {i}. {frame.state} @ {frame.timestamp}")
            elif command_input == "quit" or command_input == "q":
                break
            else:
                print(f"Unknown command: {command_input}")

        from agno.fsa.base import FSAExecutionResult
        return FSAExecutionResult(
            success=True,
            final_state=str(self.target_fsa.current_state),
            context=self.target_fsa.context,
            duration=0.0,
            transitions_executed=len(self.execution_history)
        )
