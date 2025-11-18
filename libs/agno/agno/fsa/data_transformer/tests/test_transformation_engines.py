"""
Tests for transformation engines.
"""

import pytest

from ..transformation_engines import (
    AggregationEngine,
    DataEnricher,
    DataValidator,
    FieldMapper,
    FilterEngine,
    TypeConverter,
    ValueNormalizer,
)
from ..types import Enricher


class TestFieldMapper:
    """Tests for FieldMapper."""

    def test_rename_field(self):
        """Test renaming a field."""
        data = {"old_name": "value"}
        result = FieldMapper.rename_field(data, "old_name", "new_name")

        assert "new_name" in result
        assert "old_name" not in result
        assert result["new_name"] == "value"

    def test_rename_multiple_fields(self):
        """Test renaming multiple fields."""
        data = {"first": "Alice", "last": "Doe"}
        mapping = {"first": "firstName", "last": "lastName"}

        result = FieldMapper.rename_fields(data, mapping)
        assert "firstName" in result
        assert "lastName" in result

    def test_nest_fields(self):
        """Test nesting fields."""
        data = {"street": "123 Main", "city": "NYC", "zip": "10001"}
        result = FieldMapper.nest_fields(data, ["street", "city", "zip"], "address")

        assert "address" in result
        assert "street" in result["address"]

    def test_flatten_fields(self):
        """Test flattening fields."""
        data = {"address": {"street": "123 Main", "city": "NYC"}}
        result = FieldMapper.flatten_fields(data, "address")

        assert "address_street" in result
        assert "address_city" in result

    def test_split_field(self):
        """Test splitting a field."""
        data = {"full_name": "Alice Doe"}
        result = FieldMapper.split_field(data, "full_name", " ", ["first", "last"])

        assert result["first"] == "Alice"
        assert result["last"] == "Doe"
        assert "full_name" not in result

    def test_merge_fields(self):
        """Test merging fields."""
        data = {"first": "Alice", "last": "Doe"}
        result = FieldMapper.merge_fields(data, ["first", "last"], "full_name")

        assert result["full_name"] == "Alice Doe"
        assert "first" not in result

    def test_select_fields(self):
        """Test selecting fields."""
        data = {"name": "Alice", "age": 30, "email": "alice@example.com"}
        result = FieldMapper.select_fields(data, ["name", "age"])

        assert "name" in result
        assert "age" in result
        assert "email" not in result

    def test_exclude_fields(self):
        """Test excluding fields."""
        data = {"name": "Alice", "password": "secret", "age": 30}
        result = FieldMapper.exclude_fields(data, ["password"])

        assert "name" in result
        assert "password" not in result

    def test_copy_field(self):
        """Test copying a field."""
        data = {"name": "Alice"}
        result = FieldMapper.copy_field(data, "name", "display_name")

        assert result["name"] == "Alice"
        assert result["display_name"] == "Alice"


class TestTypeConverter:
    """Tests for TypeConverter."""

    def test_to_string(self):
        """Test converting to string."""
        assert TypeConverter.to_string(123) == "123"
        assert TypeConverter.to_string(None) == ""

    def test_to_int(self):
        """Test converting to int."""
        assert TypeConverter.to_int("123") == 123
        assert TypeConverter.to_int("123.45") == 123
        assert TypeConverter.to_int(None) is None

    def test_to_int_with_default(self):
        """Test converting to int with default."""
        assert TypeConverter.to_int("invalid", default=0) == 0

    def test_to_float(self):
        """Test converting to float."""
        assert TypeConverter.to_float("123.45") == 123.45
        assert TypeConverter.to_float("123") == 123.0

    def test_to_bool(self):
        """Test converting to boolean."""
        assert TypeConverter.to_bool("true") is True
        assert TypeConverter.to_bool("false") is False
        assert TypeConverter.to_bool("1") is True
        assert TypeConverter.to_bool("0") is False

    def test_to_datetime(self):
        """Test converting to datetime."""
        result = TypeConverter.to_datetime("2023-01-15")
        assert result is not None
        assert result.year == 2023

    def test_to_datetime_with_format(self):
        """Test converting to datetime with format."""
        result = TypeConverter.to_datetime("15/01/2023", format="%d/%m/%Y")
        assert result is not None

    def test_convert_field(self):
        """Test converting a field type."""
        data = {"age": "30"}
        result = TypeConverter.convert_field(data, "age", "int")

        assert result["age"] == 30
        assert isinstance(result["age"], int)


class TestValueNormalizer:
    """Tests for ValueNormalizer."""

    def test_trim(self):
        """Test trimming whitespace."""
        assert ValueNormalizer.trim("  hello  ") == "hello"
        assert ValueNormalizer.trim(123) == 123

    def test_uppercase(self):
        """Test converting to uppercase."""
        assert ValueNormalizer.uppercase("hello") == "HELLO"

    def test_lowercase(self):
        """Test converting to lowercase."""
        assert ValueNormalizer.lowercase("HELLO") == "hello"

    def test_titlecase(self):
        """Test converting to title case."""
        assert ValueNormalizer.titlecase("hello world") == "Hello World"

    def test_replace(self):
        """Test replacing patterns."""
        assert ValueNormalizer.replace("hello world", "world", "python") == "hello python"

    def test_replace_regex(self):
        """Test replacing with regex."""
        result = ValueNormalizer.replace("abc123def456", r"\d+", "X", regex=True)
        assert "X" in result

    def test_normalize_phone(self):
        """Test normalizing phone numbers."""
        result = ValueNormalizer.normalize_phone("(555) 123-4567", format="digits")
        assert result == "5551234567"

    def test_normalize_date(self):
        """Test normalizing dates."""
        result = ValueNormalizer.normalize_date("2023-01-15")
        assert result == "2023-01-15"

    def test_normalize_whitespace(self):
        """Test normalizing whitespace."""
        assert ValueNormalizer.normalize_whitespace("hello   world") == "hello world"

    def test_remove_special_chars(self):
        """Test removing special characters."""
        result = ValueNormalizer.remove_special_chars("hello@world!")
        assert "@" not in result
        assert "!" not in result


class TestDataValidator:
    """Tests for DataValidator."""

    def test_validate_required(self):
        """Test validating required fields."""
        data = {"name": "Alice"}
        missing = DataValidator.validate_required(data, ["name", "age"])

        assert "age" in missing
        assert "name" not in missing

    def test_validate_type(self):
        """Test validating field type."""
        data = {"name": "Alice", "age": 30}

        assert DataValidator.validate_type(data, "name", str)
        assert DataValidator.validate_type(data, "age", int)
        assert not DataValidator.validate_type(data, "age", str)

    def test_validate_regex(self):
        """Test validating with regex."""
        data = {"email": "alice@example.com"}

        assert DataValidator.validate_regex(data, "email", r"^[\w\.-]+@[\w\.-]+\.\w+$")

    def test_validate_range(self):
        """Test validating range."""
        data = {"age": 25}

        assert DataValidator.validate_range(data, "age", min_value=18, max_value=65)
        assert not DataValidator.validate_range(data, "age", min_value=30)

    def test_validate_length(self):
        """Test validating length."""
        data = {"name": "Alice"}

        assert DataValidator.validate_length(data, "name", min_length=1, max_length=10)
        assert not DataValidator.validate_length(data, "name", min_length=10)

    def test_validate_enum(self):
        """Test validating enum values."""
        data = {"status": "active"}

        assert DataValidator.validate_enum(data, "status", ["active", "inactive"])
        assert not DataValidator.validate_enum(data, "status", ["pending", "completed"])

    def test_validate_email(self):
        """Test validating email format."""
        assert DataValidator.validate_email({"email": "alice@example.com"}, "email")
        assert not DataValidator.validate_email({"email": "invalid-email"}, "email")

    def test_validate_url(self):
        """Test validating URL format."""
        assert DataValidator.validate_url({"url": "https://example.com"}, "url")
        assert not DataValidator.validate_url({"url": "not-a-url"}, "url")


class TestDataEnricher:
    """Tests for DataEnricher."""

    def test_add_lookup_table(self):
        """Test adding lookup table."""
        enricher = DataEnricher()
        enricher.add_lookup_table("countries", {"US": "United States"})

        assert "countries" in enricher.lookup_tables

    def test_lookup_enrich(self):
        """Test enrichment with lookup table."""
        enricher = DataEnricher()
        enricher.add_lookup_table("countries", {"US": "United States"})

        data = {"country_code": "US"}
        result = enricher.lookup_enrich(data, "country_code", "country_name", "countries")

        assert result["country_name"] == "United States"

    def test_computed_field(self):
        """Test adding computed field."""
        enricher = DataEnricher()
        data = {"price": 100, "quantity": 3}

        result = enricher.computed_field(
            data, "total", lambda p, q: p * q, ["price", "quantity"]
        )

        assert result["total"] == 300

    def test_enrich_with_function(self):
        """Test enrichment with function."""
        enricher_engine = DataEnricher()

        def add_category(source_fields):
            amount = source_fields.get("amount", 0)
            if amount > 1000:
                return {"category": "high"}
            else:
                return {"category": "low"}

        enricher = Enricher(
            name="categorize",
            enricher_function=add_category,
            source_fields=["amount"],
            target_fields=["category"],
        )

        data = {"amount": 1500}
        result = enricher_engine.enrich_with_function(data, enricher)

        assert result["category"] == "high"


class TestAggregationEngine:
    """Tests for AggregationEngine."""

    def test_group_by(self):
        """Test grouping data."""
        data = [
            {"category": "A", "value": 10},
            {"category": "A", "value": 20},
            {"category": "B", "value": 30},
        ]

        groups = AggregationEngine.group_by(data, ["category"])
        assert len(groups) == 2

    def test_aggregate_sum(self):
        """Test aggregation with sum."""
        data = [
            {"category": "A", "amount": 100},
            {"category": "A", "amount": 200},
            {"category": "B", "amount": 150},
        ]

        result = AggregationEngine.aggregate(
            data, ["category"], {"amount": ["sum"]}
        )

        assert len(result) == 2
        a_group = next(r for r in result if r["category"] == "A")
        assert a_group["amount_sum"] == 300

    def test_aggregate_multiple_functions(self):
        """Test aggregation with multiple functions."""
        data = [
            {"category": "A", "amount": 100},
            {"category": "A", "amount": 200},
        ]

        result = AggregationEngine.aggregate(
            data, ["category"], {"amount": ["sum", "avg", "count"]}
        )

        assert result[0]["amount_sum"] == 300
        assert result[0]["amount_avg"] == 150
        assert result[0]["amount_count"] == 2


class TestFilterEngine:
    """Tests for FilterEngine."""

    def test_filter_records(self):
        """Test filtering records."""
        data = [{"age": 25}, {"age": 30}, {"age": 18}]

        result = FilterEngine.filter_records(data, lambda x: x["age"] >= 21)
        assert len(result) == 2

    def test_filter_by_value(self):
        """Test filtering by specific value."""
        data = [{"status": "active"}, {"status": "inactive"}, {"status": "active"}]

        result = FilterEngine.filter_by_value(data, "status", "active")
        assert len(result) == 2

    def test_filter_by_range(self):
        """Test filtering by range."""
        data = [{"value": 10}, {"value": 50}, {"value": 100}]

        result = FilterEngine.filter_by_range(data, "value", min_value=20, max_value=80)
        assert len(result) == 1

    def test_filter_by_regex(self):
        """Test filtering by regex."""
        data = [{"email": "alice@example.com"}, {"email": "bob@test.com"}]

        result = FilterEngine.filter_by_regex(data, "email", r".*@example\.com$")
        assert len(result) == 1

    def test_filter_nulls(self):
        """Test filtering null values."""
        data = [{"name": "Alice"}, {"name": None}, {"name": "Bob"}]

        result = FilterEngine.filter_nulls(data, ["name"])
        assert len(result) == 2

    def test_filter_duplicates(self):
        """Test removing duplicates."""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

        result = FilterEngine.filter_duplicates(data, ["id"])
        assert len(result) == 2
