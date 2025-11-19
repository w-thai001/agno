"""Unit tests for URL Parser FSA"""

import pytest

from agno.utils.url import (
    URLParserFSA,
    parse_url,
    validate_url,
    get_hostname,
    get_query_params,
)


class TestURLParserFSA:
    """Test URL Parser FSA functionality"""

    def test_basic_http_url(self):
        """Test parsing basic HTTP URL"""
        url = "http://example.com"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.scheme == "http"
        assert result.hostname == "example.com"
        assert result.path == ""
        assert result.port is None

    def test_https_url_with_path(self):
        """Test HTTPS URL with path"""
        url = "https://example.com/path/to/resource"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.scheme == "https"
        assert result.hostname == "example.com"
        assert result.path == "/path/to/resource"

    def test_url_with_port(self):
        """Test URL with port number"""
        url = "http://example.com:8080/api"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.hostname == "example.com"
        assert result.port == 8080
        assert result.path == "/api"

    def test_url_with_query_params(self):
        """Test URL with query parameters"""
        url = "https://example.com/search?q=test&page=1&limit=10"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.hostname == "example.com"
        assert result.path == "/search"
        assert result.query == "q=test&page=1&limit=10"
        assert "q" in result.query_params
        assert result.query_params["q"] == ["test"]
        assert result.query_params["page"] == ["1"]
        assert result.query_params["limit"] == ["10"]

    def test_url_with_fragment(self):
        """Test URL with fragment"""
        url = "https://example.com/page#section"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.hostname == "example.com"
        assert result.path == "/page"
        assert result.fragment == "section"

    def test_url_with_all_components(self):
        """Test URL with all components"""
        url = "https://api.example.com:443/v1/users?id=123&active=true#profile"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.scheme == "https"
        assert result.hostname == "api.example.com"
        assert result.port == 443
        assert result.path == "/v1/users"
        assert result.query == "id=123&active=true"
        assert result.fragment == "profile"
        assert result.query_params["id"] == ["123"]
        assert result.query_params["active"] == ["true"]

    def test_url_with_subdomain(self):
        """Test URL with subdomain"""
        url = "https://api.subdomain.example.com/endpoint"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.hostname == "api.subdomain.example.com"
        assert result.path == "/endpoint"

    def test_ftp_url(self):
        """Test FTP URL"""
        url = "ftp://ftp.example.com/files"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.scheme == "ftp"
        assert result.hostname == "ftp.example.com"
        assert result.path == "/files"

    def test_websocket_url(self):
        """Test WebSocket URL"""
        url = "ws://localhost:3000/socket"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.scheme == "ws"
        assert result.hostname == "localhost"
        assert result.port == 3000
        assert result.path == "/socket"

    def test_multiple_query_params_same_key(self):
        """Test multiple values for same query parameter"""
        url = "https://example.com/search?tag=python&tag=ai&tag=ml"
        result = parse_url(url)

        assert result.is_valid is True
        assert "tag" in result.query_params
        assert len(result.query_params["tag"]) == 3
        assert "python" in result.query_params["tag"]
        assert "ai" in result.query_params["tag"]
        assert "ml" in result.query_params["tag"]

    def test_query_param_without_value(self):
        """Test query parameter without value"""
        url = "https://example.com/page?debug&verbose"
        result = parse_url(url)

        assert result.is_valid is True
        assert "debug" in result.query_params
        assert "verbose" in result.query_params
        assert result.query_params["debug"] == [""]
        assert result.query_params["verbose"] == [""]

    def test_url_with_hyphen_in_hostname(self):
        """Test URL with hyphen in hostname"""
        url = "https://my-api-server.com/endpoint"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.hostname == "my-api-server.com"

    def test_invalid_url_no_scheme(self):
        """Test invalid URL without scheme"""
        url = "example.com/path"
        result = parse_url(url)

        assert result.is_valid is False

    def test_invalid_url_missing_slashes(self):
        """Test invalid URL with missing slashes"""
        url = "http:/example.com"
        result = parse_url(url)

        assert result.is_valid is False

    def test_invalid_url_invalid_port(self):
        """Test invalid URL with invalid port"""
        url = "http://example.com:99999/path"
        result = parse_url(url)

        assert result.is_valid is False

    def test_invalid_url_empty_string(self):
        """Test invalid empty URL"""
        url = ""
        result = parse_url(url)

        assert result.is_valid is False

    def test_validate_url_function(self):
        """Test validate_url convenience function"""
        assert validate_url("https://example.com") is True
        assert validate_url("http://localhost:8080") is True
        assert validate_url("invalid-url") is False
        assert validate_url("") is False

    def test_get_hostname_function(self):
        """Test get_hostname convenience function"""
        assert get_hostname("https://example.com/path") == "example.com"
        assert get_hostname("http://api.example.com:8080") == "api.example.com"
        assert get_hostname("invalid-url") is None

    def test_get_query_params_function(self):
        """Test get_query_params convenience function"""
        params = get_query_params("https://example.com?foo=bar&baz=qux")
        assert params["foo"] == ["bar"]
        assert params["baz"] == ["qux"]

        params = get_query_params("https://example.com")
        assert params == {}

        params = get_query_params("invalid-url")
        assert params == {}

    def test_url_to_dict(self):
        """Test URLParseResult to_dict method"""
        url = "https://example.com:443/path?key=value#fragment"
        result = parse_url(url)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["scheme"] == "https"
        assert result_dict["hostname"] == "example.com"
        assert result_dict["port"] == 443
        assert result_dict["path"] == "/path"
        assert result_dict["is_valid"] is True

    def test_url_repr(self):
        """Test URLParseResult __repr__ method"""
        url = "https://example.com/path"
        result = parse_url(url)
        repr_str = repr(result)

        assert "URLParseResult" in repr_str
        assert "https" in repr_str
        assert "example.com" in repr_str

    def test_parser_reset(self):
        """Test parser reset functionality"""
        parser = URLParserFSA()
        parser.parse("https://example.com")

        assert parser.result.hostname == "example.com"

        parser.reset()
        assert parser.result.hostname == ""
        assert parser.buffer == ""

    def test_url_with_dots_in_hostname(self):
        """Test URL with multiple dots in hostname"""
        url = "https://www.api.example.co.uk/endpoint"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.hostname == "www.api.example.co.uk"

    def test_root_path(self):
        """Test URL with root path"""
        url = "https://example.com/"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.path == "/"

    def test_query_with_special_chars(self):
        """Test query with plus signs"""
        url = "https://example.com/search?q=hello+world"
        result = parse_url(url)

        assert result.is_valid is True
        assert "q" in result.query_params
        # Plus signs are converted to spaces in decoding
        assert "hello world" in result.query_params["q"][0]

    def test_scheme_case_insensitive(self):
        """Test that scheme is converted to lowercase"""
        url = "HTTPS://EXAMPLE.COM/path"
        result = parse_url(url)

        assert result.is_valid is True
        assert result.scheme == "https"
        # Note: hostname case is preserved
        assert result.hostname == "EXAMPLE.COM"
