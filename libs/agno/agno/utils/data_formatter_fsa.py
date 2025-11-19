"""Data Formatter FSA (Finite State Automaton) for agno.

Simple state-based formatter for dates, currency, percentages, and numbers.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Optional, Union


class State(Enum):
    """FSA states for data formatting."""
    IDLE = "idle"
    PARSING = "parsing"
    VALIDATING = "validating"
    FORMATTING = "formatting"
    COMPLETE = "complete"
    ERROR = "error"


class DataType(Enum):
    """Supported data types for formatting."""
    DATE = "date"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    NUMBER = "number"


@dataclass
class FormatConfig:
    """Configuration for data formatting."""
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    currency_symbol: str = "$"
    currency_position: str = "prefix"
    currency_decimals: int = 2
    decimal_places: int = 2
    thousands_separator: str = ","
    decimal_separator: str = "."
    percentage_decimals: int = 1
    percentage_multiply: bool = True


@dataclass
class FormatResult:
    """Result of formatting operation."""
    success: bool
    formatted_value: Optional[str] = None
    original_value: Any = None
    data_type: Optional[DataType] = None
    error: Optional[str] = None
    state: State = State.IDLE


class DataFormatterFSA:
    """Finite State Automaton for data formatting.

    Example:
        >>> formatter = DataFormatterFSA()
        >>> result = formatter.format_currency(1234.56)
        >>> print(result.formatted_value)  # "$1,234.56"
    """

    def __init__(self, config: Optional[FormatConfig] = None):
        self.config = config or FormatConfig()
        self._state = State.IDLE
        self._current_value: Any = None
        self._current_type: Optional[DataType] = None

    @property
    def state(self) -> State:
        return self._state

    def _transition(self, new_state: State) -> None:
        self._state = new_state

    def _reset(self) -> None:
        self._state = State.IDLE
        self._current_value = None
        self._current_type = None

    def _error(self, message: str, original_value: Any) -> FormatResult:
        self._transition(State.ERROR)
        result = FormatResult(
            success=False, original_value=original_value,
            error=message, state=State.ERROR
        )
        self._reset()
        return result

    def _complete(self, formatted: str, original: Any, data_type: DataType) -> FormatResult:
        self._transition(State.COMPLETE)
        result = FormatResult(
            success=True, formatted_value=formatted,
            original_value=original, data_type=data_type,
            state=State.COMPLETE
        )
        self._reset()
        return result

    def format_date(
        self, value: Union[datetime, str, int, float],
        format_string: Optional[str] = None
    ) -> FormatResult:
        """Format a date/datetime value."""
        self._transition(State.PARSING)
        original = value
        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(value)
            elif isinstance(value, datetime):
                dt = value
            else:
                return self._error(f"Unsupported date type: {type(value)}", original)

            self._transition(State.VALIDATING)
            self._transition(State.FORMATTING)

            fmt = format_string or self.config.date_format
            if dt.hour or dt.minute or dt.second:
                fmt = format_string or self.config.datetime_format
            formatted = dt.strftime(fmt)
            return self._complete(formatted, original, DataType.DATE)
        except (ValueError, AttributeError, OSError) as e:
            return self._error(f"Date parsing error: {str(e)}", original)

    def format_currency(
        self, value: Union[int, float, Decimal, str],
        symbol: Optional[str] = None
    ) -> FormatResult:
        """Format a currency value."""
        self._transition(State.PARSING)
        original = value
        try:
            if isinstance(value, str):
                num = Decimal(value.replace(",", "").replace(
                    symbol or self.config.currency_symbol, "").strip())
            else:
                num = Decimal(str(value))

            self._transition(State.VALIDATING)
            self._transition(State.FORMATTING)

            formatted_num = self._format_number_with_separators(
                num, self.config.currency_decimals)
            sym = symbol or self.config.currency_symbol

            if self.config.currency_position == "prefix":
                formatted = f"{sym}{formatted_num}"
            else:
                formatted = f"{formatted_num}{sym}"
            return self._complete(formatted, original, DataType.CURRENCY)
        except (InvalidOperation, ValueError) as e:
            return self._error(f"Currency parsing error: {str(e)}", original)

    def format_percentage(
        self, value: Union[int, float, Decimal, str],
        decimals: Optional[int] = None
    ) -> FormatResult:
        """Format a percentage value."""
        self._transition(State.PARSING)
        original = value
        try:
            if isinstance(value, str):
                num = float(value.replace("%", "").replace(",", "").strip())
            else:
                num = float(value)

            self._transition(State.VALIDATING)
            if self.config.percentage_multiply and 0 <= num <= 1:
                num = num * 100

            self._transition(State.FORMATTING)
            dec = decimals if decimals is not None else self.config.percentage_decimals
            formatted = f"{num:.{dec}f}%"
            return self._complete(formatted, original, DataType.PERCENTAGE)
        except (ValueError, TypeError) as e:
            return self._error(f"Percentage parsing error: {str(e)}", original)

    def format_number(
        self, value: Union[int, float, Decimal, str],
        decimals: Optional[int] = None
    ) -> FormatResult:
        """Format a number with thousands separators."""
        self._transition(State.PARSING)
        original = value
        try:
            if isinstance(value, str):
                num = Decimal(value.replace(",", "").strip())
            else:
                num = Decimal(str(value))

            self._transition(State.VALIDATING)
            self._transition(State.FORMATTING)

            dec = decimals if decimals is not None else self.config.decimal_places
            formatted = self._format_number_with_separators(num, dec)
            return self._complete(formatted, original, DataType.NUMBER)
        except (InvalidOperation, ValueError) as e:
            return self._error(f"Number parsing error: {str(e)}", original)

    def _format_number_with_separators(self, value: Decimal, decimals: int) -> str:
        """Format number with thousands and decimal separators."""
        rounded = round(value, decimals)
        parts = str(rounded).split(".")
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "0" * decimals
        decimal_part = decimal_part.ljust(decimals, "0")[:decimals]

        is_negative = integer_part.startswith("-")
        if is_negative:
            integer_part = integer_part[1:]

        formatted_int = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_int = self.config.thousands_separator + formatted_int
            formatted_int = digit + formatted_int

        if is_negative:
            formatted_int = "-" + formatted_int

        if decimals > 0:
            return f"{formatted_int}{self.config.decimal_separator}{decimal_part}"
        return formatted_int
