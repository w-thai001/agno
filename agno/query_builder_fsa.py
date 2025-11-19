"""Query Builder Finite State Automaton for SQL query construction."""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class State(Enum):
    """FSA states for query building."""
    IDLE = "idle"
    SELECTING = "selecting"
    WHERE = "where"
    ORDERING = "ordering"
    LIMITING = "limiting"
    COMPLETED = "completed"


@dataclass
class QueryContext:
    """Context for query construction."""
    table: str
    columns: List[str] = field(default_factory=lambda: ["*"])
    where_clauses: List[str] = field(default_factory=list)
    order_by: List[Tuple[str, str]] = field(default_factory=list)
    limit_value: Optional[int] = None
    offset_value: Optional[int] = None
    parameters: List[Any] = field(default_factory=list)


class QueryBuilderFSA:
    """Finite State Automaton for building SQL queries."""

    def __init__(self):
        self.state = State.IDLE
        self.context: Optional[QueryContext] = None

    def select(self, *columns: str) -> "QueryBuilderFSA":
        """Start query with SELECT clause."""
        if self.state != State.IDLE:
            raise RuntimeError(f"Cannot SELECT in state: {self.state.value}")

        self._transition(State.IDLE, State.SELECTING)
        self.context.columns = list(columns) if columns else ["*"]
        logger.debug(f"SELECT {', '.join(self.context.columns)}")
        return self

    def from_table(self, table: str) -> "QueryBuilderFSA":
        """Initialize query builder with table."""
        if self.state != State.IDLE:
            self.reset()

        self.context = QueryContext(table=table)
        logger.debug(f"Building query for table: {table}")
        return self

    def where(self, condition: str, *params: Any) -> "QueryBuilderFSA":
        """Add WHERE condition."""
        if self.state not in (State.SELECTING, State.WHERE):
            raise RuntimeError(f"Cannot add WHERE in state: {self.state.value}")

        if self.state == State.SELECTING:
            self._transition(State.SELECTING, State.WHERE)

        self.context.where_clauses.append(condition)
        self.context.parameters.extend(params)
        logger.debug(f"WHERE: {condition}")
        return self

    def where_eq(self, column: str, value: Any) -> "QueryBuilderFSA":
        """Add WHERE column = value."""
        return self.where(f"{column} = ?", value)

    def where_in(self, column: str, values: List[Any]) -> "QueryBuilderFSA":
        """Add WHERE column IN (...)."""
        placeholders = ", ".join(["?"] * len(values))
        return self.where(f"{column} IN ({placeholders})", *values)

    def where_like(self, column: str, pattern: str) -> "QueryBuilderFSA":
        """Add WHERE column LIKE pattern."""
        return self.where(f"{column} LIKE ?", pattern)

    def where_gt(self, column: str, value: Any) -> "QueryBuilderFSA":
        """Add WHERE column > value."""
        return self.where(f"{column} > ?", value)

    def where_lt(self, column: str, value: Any) -> "QueryBuilderFSA":
        """Add WHERE column < value."""
        return self.where(f"{column} < ?", value)

    def order_by(self, column: str, direction: str = "ASC") -> "QueryBuilderFSA":
        """Add ORDER BY clause."""
        valid_states = (State.SELECTING, State.WHERE, State.ORDERING)
        if self.state not in valid_states:
            raise RuntimeError(f"Cannot add ORDER BY in state: {self.state.value}")

        if self.state in (State.SELECTING, State.WHERE):
            self._transition(self.state, State.ORDERING)

        direction = direction.upper()
        if direction not in ("ASC", "DESC"):
            raise ValueError(f"Invalid direction: {direction}")

        self.context.order_by.append((column, direction))
        logger.debug(f"ORDER BY: {column} {direction}")
        return self

    def limit(self, limit: int, offset: Optional[int] = None) -> "QueryBuilderFSA":
        """Add LIMIT clause with optional OFFSET."""
        valid_states = (State.SELECTING, State.WHERE, State.ORDERING, State.LIMITING)
        if self.state not in valid_states:
            raise RuntimeError(f"Cannot add LIMIT in state: {self.state.value}")

        if self.state != State.LIMITING:
            self._transition(self.state, State.LIMITING)

        if limit <= 0:
            raise ValueError(f"LIMIT must be positive: {limit}")

        if offset is not None and offset < 0:
            raise ValueError(f"OFFSET must be non-negative: {offset}")

        self.context.limit_value = limit
        self.context.offset_value = offset
        logger.debug(f"LIMIT: {limit}" + (f" OFFSET: {offset}" if offset else ""))
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """Build final SQL query and return with parameters."""
        if self.state == State.IDLE:
            raise RuntimeError("Cannot build query in IDLE state")

        # Ensure we have selected columns
        if self.state == State.IDLE or not self.context:
            raise RuntimeError("No query context")

        self._transition(self.state, State.COMPLETED)

        # Build SELECT clause
        columns_str = ", ".join(self.context.columns)
        query = f"SELECT {columns_str} FROM {self.context.table}"

        # Build WHERE clause
        if self.context.where_clauses:
            where_str = " AND ".join(self.context.where_clauses)
            query += f" WHERE {where_str}"

        # Build ORDER BY clause
        if self.context.order_by:
            order_parts = [f"{col} {direction}" for col, direction in self.context.order_by]
            query += f" ORDER BY {', '.join(order_parts)}"

        # Build LIMIT clause
        if self.context.limit_value:
            query += f" LIMIT {self.context.limit_value}"
            if self.context.offset_value:
                query += f" OFFSET {self.context.offset_value}"

        logger.info(f"Built query: {query}")
        return query, self.context.parameters

    def reset(self) -> "QueryBuilderFSA":
        """Reset builder to IDLE state."""
        logger.debug("Resetting query builder")
        self._transition(self.state, State.IDLE)
        self.context = None
        return self

    def _transition(self, from_state: State, to_state: State):
        """Transition between states."""
        logger.debug(f"State transition: {from_state.value} -> {to_state.value}")
        self.state = to_state
