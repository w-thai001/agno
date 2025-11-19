"""JSON Parser using Finite State Automaton (FSA) - validate, parse, stringify functions"""
from typing import Any, Union, List, Dict
from enum import Enum


class State(Enum):
    """FSA states for JSON parsing"""
    IN_STRING = "in_string"
    STRING_ESCAPE = "string_escape"


class JSONParserError(Exception):
    """Custom exception for JSON parsing errors"""
    pass


class JSONParser:
    """FSA-based JSON Parser"""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def skip_whitespace(self):
        while self.pos < self.length and self.text[self.pos] in ' \t\n\r':
            self.pos += 1

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < self.length else ''

    def consume(self) -> str:
        if self.pos < self.length:
            char = self.text[self.pos]
            self.pos += 1
            return char
        return ''

    def parse_string(self) -> str:
        """Parse JSON string using FSA"""
        if self.peek() != '"':
            raise JSONParserError(f"Expected '\"' at position {self.pos}")
        self.consume()
        result = []
        state = State.IN_STRING
        escape_map = {'"': '"', '\\': '\\', '/': '/', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t'}
        while self.pos < self.length:
            char = self.consume()
            if state == State.IN_STRING:
                if char == '"':
                    return ''.join(result)
                elif char == '\\':
                    state = State.STRING_ESCAPE
                else:
                    result.append(char)
            elif state == State.STRING_ESCAPE:
                if char in escape_map:
                    result.append(escape_map[char])
                    state = State.IN_STRING
                elif char == 'u':
                    hex_digits = self.text[self.pos:self.pos + 4]
                    if len(hex_digits) == 4:
                        result.append(chr(int(hex_digits, 16)))
                        self.pos += 4
                        state = State.IN_STRING
                    else:
                        raise JSONParserError(f"Invalid unicode escape at {self.pos}")
                else:
                    raise JSONParserError(f"Invalid escape sequence at {self.pos}")
        raise JSONParserError("Unterminated string")

    def parse_number(self) -> Union[int, float]:
        """Parse JSON number using FSA"""
        start = self.pos
        has_decimal = has_exponent = False
        if self.peek() == '-':
            self.consume()
        if not self.peek().isdigit():
            raise JSONParserError(f"Invalid number at {self.pos}")
        while self.peek().isdigit():
            self.consume()
        next_char = self.peek()
        if next_char == '.':
            has_decimal = True
            self.consume()
            if not self.peek().isdigit():
                raise JSONParserError(f"Invalid number at {self.pos}")
            while self.peek().isdigit():
                self.consume()
            next_char = self.peek()
        if next_char and next_char in 'eE':
            has_exponent = True
            self.consume()
            if self.peek() in '+-':
                self.consume()
            if not self.peek().isdigit():
                raise JSONParserError(f"Invalid number at {self.pos}")
            while self.peek().isdigit():
                self.consume()
        number_str = self.text[start:self.pos]
        return float(number_str) if (has_decimal or has_exponent) else int(number_str)

    def parse_literal(self, literal: str, value: Any) -> Any:
        """Parse JSON literal (true, false, null)"""
        for expected_char in literal:
            if self.consume() != expected_char:
                raise JSONParserError(f"Invalid literal at {self.pos}")
        return value

    def parse_array(self) -> List[Any]:
        """Parse JSON array using FSA"""
        if self.peek() != '[':
            raise JSONParserError(f"Expected '[' at {self.pos}")
        self.consume()
        self.skip_whitespace()
        result = []
        if self.peek() == ']':
            self.consume()
            return result
        while True:
            self.skip_whitespace()
            result.append(self.parse_value())
            self.skip_whitespace()
            if self.peek() == ']':
                self.consume()
                return result
            elif self.peek() == ',':
                self.consume()
            else:
                raise JSONParserError(f"Expected ',' or ']' at {self.pos}")

    def parse_object(self) -> Dict[str, Any]:
        """Parse JSON object using FSA"""
        if self.peek() != '{':
            raise JSONParserError(f"Expected '{{' at {self.pos}")
        self.consume()
        self.skip_whitespace()
        result = {}
        if self.peek() == '}':
            self.consume()
            return result
        while True:
            self.skip_whitespace()
            if self.peek() != '"':
                raise JSONParserError(f"Expected string key at {self.pos}")
            key = self.parse_string()
            self.skip_whitespace()
            if self.peek() != ':':
                raise JSONParserError(f"Expected ':' at {self.pos}")
            self.consume()
            self.skip_whitespace()
            result[key] = self.parse_value()
            self.skip_whitespace()
            if self.peek() == '}':
                self.consume()
                return result
            elif self.peek() == ',':
                self.consume()
            else:
                raise JSONParserError(f"Expected ',' or '}}' at {self.pos}")

    def parse_value(self) -> Any:
        """Parse any JSON value using FSA state transitions"""
        self.skip_whitespace()
        char = self.peek()
        if char == '"':
            return self.parse_string()
        elif char == '{':
            return self.parse_object()
        elif char == '[':
            return self.parse_array()
        elif char == 't':
            return self.parse_literal('true', True)
        elif char == 'f':
            return self.parse_literal('false', False)
        elif char == 'n':
            return self.parse_literal('null', None)
        elif char == '-' or char.isdigit():
            return self.parse_number()
        else:
            raise JSONParserError(f"Unexpected character '{char}' at {self.pos}")

    def parse(self) -> Any:
        """Main parse method"""
        value = self.parse_value()
        self.skip_whitespace()
        if self.pos < self.length:
            raise JSONParserError(f"Unexpected content after JSON at {self.pos}")
        return value


class JSONStringifier:
    """Convert Python objects to JSON strings"""

    @staticmethod
    def stringify_value(value: Any, indent: int = 0, compact: bool = True) -> str:
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return JSONStringifier.stringify_string(value)
        elif isinstance(value, list):
            return JSONStringifier.stringify_array(value, indent, compact)
        elif isinstance(value, dict):
            return JSONStringifier.stringify_object(value, indent, compact)
        else:
            raise JSONParserError(f"Unsupported type: {type(value)}")

    @staticmethod
    def stringify_string(s: str) -> str:
        escape_map = {'"': '\\"', '\\': '\\\\', '\b': '\\b', '\f': '\\f', '\n': '\\n', '\r': '\\r', '\t': '\\t'}
        result = ['"']
        for char in s:
            if char in escape_map:
                result.append(escape_map[char])
            elif ord(char) < 32:
                result.append(f'\\u{ord(char):04x}')
            else:
                result.append(char)
        result.append('"')
        return ''.join(result)

    @staticmethod
    def stringify_array(arr: List[Any], indent: int = 0, compact: bool = True) -> str:
        if not arr:
            return '[]'
        if compact:
            items = [JSONStringifier.stringify_value(item, indent, compact) for item in arr]
            return '[' + ', '.join(items) + ']'
        else:
            items = [JSONStringifier.stringify_value(item, indent + 2, compact) for item in arr]
            ind = ' ' * (indent + 2)
            return '[\n' + ind + (',\n' + ind).join(items) + '\n' + ' ' * indent + ']'

    @staticmethod
    def stringify_object(obj: Dict[str, Any], indent: int = 0, compact: bool = True) -> str:
        if not obj:
            return '{}'
        if compact:
            items = [f'{JSONStringifier.stringify_string(k)}: {JSONStringifier.stringify_value(v, indent, compact)}'
                     for k, v in obj.items()]
            return '{' + ', '.join(items) + '}'
        else:
            items = [f'{JSONStringifier.stringify_string(k)}: {JSONStringifier.stringify_value(v, indent + 2, compact)}'
                     for k, v in obj.items()]
            ind = ' ' * (indent + 2)
            return '{\n' + ind + (',\n' + ind).join(items) + '\n' + ' ' * indent + '}'


# Public API Functions

def validate(json_str: str) -> bool:
    """Validate if a string is valid JSON. Returns True if valid, False otherwise."""
    try:
        parser = JSONParser(json_str)
        parser.parse()
        return True
    except (JSONParserError, Exception):
        return False


def parse(json_str: str) -> Any:
    """Parse a JSON string into a Python object. Raises JSONParserError if invalid."""
    parser = JSONParser(json_str)
    return parser.parse()


def stringify(obj: Any, compact: bool = True) -> str:
    """Convert a Python object to a JSON string. Raises JSONParserError if unsupported type."""
    return JSONStringifier.stringify_value(obj, compact=compact)
