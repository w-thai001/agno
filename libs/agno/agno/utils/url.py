"""URL Parser Finite State Automaton - lightweight parser for URL validation and parsing."""

from enum import Enum
from typing import Dict, List, Optional


class State(Enum):
    """FSA states for URL parsing"""
    START = "start"
    SCHEME = "scheme"
    SCHEME_SEP1 = "scheme_sep1"
    SCHEME_SEP2 = "scheme_sep2"
    HOSTNAME = "hostname"
    PORT = "port"
    PATH = "path"
    QUERY = "query"
    FRAGMENT = "fragment"
    ERROR = "error"


class URLParseResult:
    """Result of URL parsing"""

    def __init__(self):
        self.scheme: str = ""
        self.hostname: str = ""
        self.port: Optional[int] = None
        self.path: str = ""
        self.query: str = ""
        self.fragment: str = ""
        self.query_params: Dict[str, List[str]] = {}
        self.is_valid: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary representation"""
        return {
            "scheme": self.scheme,
            "hostname": self.hostname,
            "port": self.port,
            "path": self.path,
            "query": self.query,
            "fragment": self.fragment,
            "query_params": self.query_params,
            "is_valid": self.is_valid,
        }

    def __repr__(self) -> str:
        return f"URLParseResult(scheme={self.scheme!r}, hostname={self.hostname!r}, path={self.path!r})"


class URLParserFSA:
    """Finite State Automaton for URL parsing"""

    VALID_SCHEMES = {"http", "https", "ftp", "ftps", "ws", "wss", "file"}

    def __init__(self):
        self.state = State.START
        self.result = URLParseResult()
        self.buffer = ""
        self.position = 0

    def parse(self, url: str) -> URLParseResult:
        """Parse URL using FSA"""
        if not url or not isinstance(url, str):
            return self.result
        self.reset()
        for i, char in enumerate(url):
            self.position = i
            self._process_char(char)
            if self.state == State.ERROR:
                return self.result
        self._finalize()
        return self.result

    def validate(self, url: str) -> bool:
        """Validate URL format"""
        result = self.parse(url)
        return result.is_valid

    def reset(self):
        """Reset parser state"""
        self.state = State.START
        self.result = URLParseResult()
        self.buffer = ""
        self.position = 0

    def _process_char(self, char: str):
        """Process single character based on current state"""
        if self.state == State.START:
            self._handle_start(char)
        elif self.state == State.SCHEME:
            self._handle_scheme(char)
        elif self.state == State.SCHEME_SEP1:
            self._handle_scheme_sep1(char)
        elif self.state == State.SCHEME_SEP2:
            self._handle_scheme_sep2(char)
        elif self.state == State.HOSTNAME:
            self._handle_hostname(char)
        elif self.state == State.PORT:
            self._handle_port(char)
        elif self.state == State.PATH:
            self._handle_path(char)
        elif self.state == State.QUERY:
            self._handle_query(char)
        elif self.state == State.FRAGMENT:
            self._handle_fragment(char)

    def _handle_start(self, char: str):
        """Handle START state"""
        if char.isalpha():
            self.buffer = char
            self.state = State.SCHEME
        else:
            self.state = State.ERROR

    def _handle_scheme(self, char: str):
        """Handle SCHEME state"""
        if char == ':':
            self.result.scheme = self.buffer.lower()
            self.buffer = ""
            self.state = State.SCHEME_SEP1
        elif char.isalnum() or char in ['+', '-', '.']:
            self.buffer += char
        else:
            self.state = State.ERROR

    def _handle_scheme_sep1(self, char: str):
        """Handle first separator after scheme (:)"""
        if char == '/':
            self.state = State.SCHEME_SEP2
        else:
            self.state = State.ERROR

    def _handle_scheme_sep2(self, char: str):
        """Handle second separator after scheme (//)"""
        if char == '/':
            self.state = State.HOSTNAME
            self.buffer = ""
        else:
            self.state = State.ERROR

    def _handle_hostname(self, char: str):
        """Handle HOSTNAME state"""
        if char == ':':
            self.result.hostname = self.buffer
            self.buffer = ""
            self.state = State.PORT
        elif char == '/':
            self.result.hostname = self.buffer
            self.buffer = char
            self.state = State.PATH
        elif char == '?':
            self.result.hostname = self.buffer
            self.buffer = ""
            self.state = State.QUERY
        elif char == '#':
            self.result.hostname = self.buffer
            self.buffer = ""
            self.state = State.FRAGMENT
        elif char.isalnum() or char in ['-', '.', '_', '~']:
            self.buffer += char
        else:
            self.state = State.ERROR

    def _handle_port(self, char: str):
        """Handle PORT state"""
        if char.isdigit():
            self.buffer += char
        elif char in ['/', '?', '#']:
            try:
                self.result.port = int(self.buffer)
                self.buffer = char if char == '/' else ""
                self.state = State.PATH if char == '/' else (State.QUERY if char == '?' else State.FRAGMENT)
            except ValueError:
                self.state = State.ERROR
        else:
            self.state = State.ERROR

    def _handle_path(self, char: str):
        """Handle PATH state"""
        if char == '?':
            self.result.path = self.buffer
            self.buffer = ""
            self.state = State.QUERY
        elif char == '#':
            self.result.path = self.buffer
            self.buffer = ""
            self.state = State.FRAGMENT
        else:
            self.buffer += char

    def _handle_query(self, char: str):
        """Handle QUERY state"""
        if char == '#':
            self.result.query = self.buffer
            self._parse_query_params()
            self.buffer = ""
            self.state = State.FRAGMENT
        else:
            self.buffer += char

    def _handle_fragment(self, char: str):
        """Handle FRAGMENT state"""
        self.buffer += char

    def _finalize(self):
        """Finalize parsing and validate"""
        if self.state == State.HOSTNAME:
            self.result.hostname = self.buffer
        elif self.state == State.PORT:
            try:
                self.result.port = int(self.buffer)
            except ValueError:
                self.state = State.ERROR
        elif self.state == State.PATH:
            self.result.path = self.buffer
        elif self.state == State.QUERY:
            self.result.query = self.buffer
            self._parse_query_params()
        elif self.state == State.FRAGMENT:
            self.result.fragment = self.buffer
        self.result.is_valid = self._validate_result()

    def _parse_query_params(self):
        """Parse query string into parameters"""
        if not self.result.query:
            return

        params: Dict[str, List[str]] = {}

        for pair in self.result.query.split('&'):
            if not pair:
                continue

            if '=' in pair:
                key, value = pair.split('=', 1)
                key = self._decode_component(key)
                value = self._decode_component(value)
            else:
                key = self._decode_component(pair)
                value = ""

            if key in params:
                params[key].append(value)
            else:
                params[key] = [value]

        self.result.query_params = params

    def _decode_component(self, component: str) -> str:
        """Simple URL decode for component"""
        return component.replace('+', ' ')

    def _validate_result(self) -> bool:
        """Validate parsed URL components"""
        if self.result.scheme not in self.VALID_SCHEMES:
            return False
        if self.result.scheme != "file" and not self.result.hostname:
            return False
        if self.result.port is not None and not (0 < self.result.port <= 65535):
            return False
        if self.state == State.ERROR:
            return False
        return True


# Convenience functions
def parse_url(url: str) -> URLParseResult:
    """Parse URL and return result"""
    parser = URLParserFSA()
    return parser.parse(url)


def validate_url(url: str) -> bool:
    """Validate URL format"""
    parser = URLParserFSA()
    return parser.validate(url)


def get_hostname(url: str) -> Optional[str]:
    """Extract hostname from URL"""
    result = parse_url(url)
    return result.hostname if result.is_valid else None


def get_query_params(url: str) -> Dict[str, List[str]]:
    """Extract query parameters from URL"""
    result = parse_url(url)
    return result.query_params if result.is_valid else {}
