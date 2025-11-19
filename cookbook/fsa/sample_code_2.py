"""Sample code file 2 - Data processor with higher complexity."""

import json
from typing import List, Dict, Any, Optional


class DataProcessor:
    """Process and validate data records."""

    def __init__(self, strict_mode=True):
        self.strict_mode = strict_mode
        self.errors = []
        self.processed_count = 0

    def validate_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate a data record with complex rules.

        This method has intentionally high complexity for demonstration.
        """
        if not isinstance(record, dict):
            return False

        # Check required fields
        if "id" not in record or "name" not in record or "value" not in record:
            if self.strict_mode:
                self.errors.append("Missing required fields")
                return False

        # Validate ID
        if "id" in record:
            if not isinstance(record["id"], (int, str)):
                return False
            if isinstance(record["id"], str) and len(record["id"]) == 0:
                return False
            if isinstance(record["id"], int) and record["id"] < 0:
                return False

        # Validate name
        if "name" in record:
            if not isinstance(record["name"], str):
                return False
            if len(record["name"]) < 2 or len(record["name"]) > 100:
                return False
            if not record["name"].strip():
                return False

        # Validate value with complex conditions
        if "value" in record:
            value = record["value"]
            if isinstance(value, int):
                if value < 0 or value > 1000000:
                    return False
            elif isinstance(value, float):
                if value < 0.0 or value > 1000000.0:
                    return False
            elif isinstance(value, str):
                try:
                    float_val = float(value)
                    if float_val < 0.0 or float_val > 1000000.0:
                        return False
                except ValueError:
                    return False
            else:
                return False

        # Validate optional status field
        if "status" in record:
            valid_statuses = ["active", "inactive", "pending", "completed"]
            if record["status"] not in valid_statuses:
                if self.strict_mode:
                    return False

        # Validate optional metadata
        if "metadata" in record:
            if not isinstance(record["metadata"], dict):
                return False
            for key, val in record["metadata"].items():
                if not isinstance(key, str):
                    return False
                if key.startswith("_"):
                    return False

        return True

    def process_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of records."""
        processed = []

        for record in records:
            if self.validate_record(record):
                processed_record = self.transform_record(record)
                processed.append(processed_record)
                self.processed_count += 1
            else:
                if self.strict_mode:
                    raise ValueError(f"Invalid record: {record}")

        return processed

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a record."""
        transformed = record.copy()

        # Normalize value
        if "value" in transformed:
            transformed["value"] = float(transformed["value"])

        # Add processed flag
        transformed["processed"] = True

        return transformed

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "processed_count": self.processed_count,
            "error_count": len(self.errors),
            "errors": self.errors,
        }


def process_file(file_path: str, strict_mode: bool = True) -> Optional[List[Dict]]:
    """Process a JSON file containing records."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return None

        processor = DataProcessor(strict_mode=strict_mode)
        return processor.process_batch(data)

    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
    except Exception as e:
        return None
