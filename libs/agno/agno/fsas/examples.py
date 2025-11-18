"""
Example usage of FSA Generator

This module demonstrates various ways to use the FSA Generator to create
Functional Specialist Agents automatically.
"""

from pathlib import Path

from agno.fsas import FSAGenerator, FSACategory, InvalidSpecificationError


def example_basic_generation():
    """Example 1: Basic FSA generation with minimal specification"""
    print("\n" + "="*60)
    print("Example 1: Basic FSA Generation")
    print("="*60)

    # Create generator
    generator = FSAGenerator(auto_commit=False)

    # Simple specification
    spec = {
        "name": "EmailSender",
        "category": "Integration",
        "purpose": "Send emails via SMTP with attachments and templates"
    }

    try:
        implementation = generator.generate_fsa(spec)
        print(f"✓ Generated {implementation.spec.class_name}")
        print(f"  File: {implementation.file_path}")
        print(f"  Tests: {implementation.test_file_path}")
        print(f"  LOC: {len(implementation.code.splitlines())}")
        return implementation
    except Exception as e:
        print(f"✗ Failed: {e}")
        return None


def example_detailed_specification():
    """Example 2: FSA generation with detailed specification"""
    print("\n" + "="*60)
    print("Example 2: Detailed FSA Generation")
    print("="*60)

    generator = FSAGenerator(auto_commit=False)

    spec = {
        "name": "DataValidator",
        "category": "Domain",
        "purpose": "Validate data quality and integrity across multiple sources",
        "key_capabilities": [
            "Schema validation",
            "Data type checking",
            "Range and constraint validation",
            "Duplicate detection",
            "Missing value analysis"
        ],
        "dependencies": ["pydantic", "jsonschema"],
        "complexity_target": "600-800 LOC",
        "custom_methods": {
            "validate_schema": "Validate data against JSON schema",
            "check_constraints": "Check business rule constraints",
            "find_duplicates": "Identify duplicate records",
            "analyze_missing": "Analyze missing value patterns"
        }
    }

    try:
        implementation = generator.generate_fsa(spec)
        print(f"✓ Generated {implementation.spec.class_name}")
        print(f"  Category: {implementation.spec.category.value}")
        print(f"  Capabilities: {len(implementation.spec.key_capabilities)}")
        print(f"  Custom Methods: {len(implementation.spec.custom_methods)}")
        print(f"  Dependencies: {', '.join(implementation.spec.dependencies)}")
        return implementation
    except Exception as e:
        print(f"✗ Failed: {e}")
        generator.error_recovery(e)
        return None


def example_from_json_file():
    """Example 3: Generate FSA from JSON specification file"""
    print("\n" + "="*60)
    print("Example 3: Generation from JSON File")
    print("="*60)

    import json
    import tempfile

    generator = FSAGenerator(auto_commit=False)

    # Create temporary JSON file
    spec_dict = {
        "name": "CacheManager",
        "category": "Core",
        "purpose": "Manage distributed cache with TTL and invalidation",
        "key_capabilities": [
            "Set/Get cache entries",
            "TTL-based expiration",
            "Cache invalidation",
            "Statistics tracking"
        ],
        "dependencies": ["redis", "pickle"],
        "complexity_target": "400-600 LOC"
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(spec_dict, f)
        spec_file = f.name

    try:
        implementation = generator.generate_fsa(spec_file)
        print(f"✓ Generated from JSON: {implementation.spec.class_name}")
        print(f"  Source: {spec_file}")
        return implementation
    except Exception as e:
        print(f"✗ Failed: {e}")
        return None
    finally:
        Path(spec_file).unlink(missing_ok=True)


def example_meta_fsa():
    """Example 4: Generate a Meta FSA"""
    print("\n" + "="*60)
    print("Example 4: Meta FSA Generation")
    print("="*60)

    generator = FSAGenerator(auto_commit=False)

    spec = {
        "name": "FSAAnalyzer",
        "category": "Meta",
        "purpose": "Analyze FSA performance and suggest optimizations",
        "key_capabilities": [
            "Profile FSA execution time",
            "Analyze memory usage",
            "Identify bottlenecks",
            "Suggest optimization strategies"
        ],
        "dependencies": ["psutil", "memory_profiler"],
        "complexity_target": "500-700 LOC",
        "custom_methods": {
            "profile_execution": "Profile FSA execution time",
            "analyze_memory": "Analyze memory consumption",
            "find_bottlenecks": "Identify performance bottlenecks",
            "suggest_optimizations": "Suggest optimization strategies"
        }
    }

    try:
        implementation = generator.generate_fsa(spec)
        print(f"✓ Generated Meta FSA: {implementation.spec.class_name}")
        print(f"  A Meta FSA that operates on other FSAs!")
        return implementation
    except Exception as e:
        print(f"✗ Failed: {e}")
        return None


def example_error_handling():
    """Example 5: Demonstrate error handling"""
    print("\n" + "="*60)
    print("Example 5: Error Handling")
    print("="*60)

    generator = FSAGenerator(auto_commit=False)

    # Invalid specification (lowercase name)
    invalid_spec = {
        "name": "invalidName",  # Should be PascalCase
        "category": "Core",
        "purpose": "Test error handling"
    }

    try:
        implementation = generator.generate_fsa(invalid_spec)
    except InvalidSpecificationError as e:
        print(f"✓ Caught expected error: {type(e).__name__}")
        recovery = generator.error_recovery(e)
        print("\nRecovery suggestions received:")
        print(recovery)

    # Another invalid spec (invalid category)
    invalid_spec2 = {
        "name": "TestFSA",
        "category": "InvalidCategory",  # Not a valid category
        "purpose": "Test error handling"
    }

    try:
        implementation = generator.generate_fsa(invalid_spec2)
    except Exception as e:
        print(f"\n✓ Caught error: {type(e).__name__}")
        print(f"  Message: {str(e)[:100]}...")


def example_validation():
    """Example 6: Validate generated FSA"""
    print("\n" + "="*60)
    print("Example 6: FSA Validation")
    print("="*60)

    generator = FSAGenerator(auto_commit=False)

    spec = {
        "name": "QuickValidator",
        "category": "Core",
        "purpose": "Quick data validation"
    }

    implementation = generator.generate_fsa(spec)

    # Validate syntax
    if implementation.validate_syntax():
        print("✓ Code syntax is valid")
    else:
        print("✗ Code has syntax errors")

    # Validate tests
    if implementation.validate_tests():
        print("✓ Test syntax is valid")
    else:
        print("✗ Tests have syntax errors")

    # Full validation
    if generator.validate_fsa(implementation):
        print("✓ FSA passed all validation checks")
    else:
        print("✗ FSA failed validation")

    return implementation


def example_batch_generation():
    """Example 7: Generate multiple FSAs in batch"""
    print("\n" + "="*60)
    print("Example 7: Batch Generation")
    print("="*60)

    generator = FSAGenerator(auto_commit=False)

    # Define multiple FSA specifications
    specs = [
        {
            "name": "Logger",
            "category": "Core",
            "purpose": "Centralized logging with multiple outputs"
        },
        {
            "name": "ConfigManager",
            "category": "Core",
            "purpose": "Manage application configuration"
        },
        {
            "name": "MetricsCollector",
            "category": "Core",
            "purpose": "Collect and aggregate metrics"
        },
        {
            "name": "DatabaseConnector",
            "category": "Integration",
            "purpose": "Connect to multiple database types"
        },
        {
            "name": "APIClient",
            "category": "Integration",
            "purpose": "Generic REST API client"
        }
    ]

    results = []
    for spec in specs:
        try:
            implementation = generator.generate_fsa(spec)
            results.append((spec["name"], True, implementation))
            print(f"✓ {spec['name']}: Success")
        except Exception as e:
            results.append((spec["name"], False, str(e)))
            print(f"✗ {spec['name']}: Failed - {str(e)[:50]}...")

    print(f"\nBatch Complete:")
    print(f"  Successful: {sum(1 for _, success, _ in results if success)}/{len(specs)}")
    print(f"  Failed: {sum(1 for _, success, _ in results if not success)}/{len(specs)}")

    return results


def example_custom_templates():
    """Example 8: Using all FSA categories"""
    print("\n" + "="*60)
    print("Example 8: FSA Categories")
    print("="*60)

    generator = FSAGenerator(auto_commit=False)

    categories = {
        "Core": {
            "name": "CoreExample",
            "category": "Core",
            "purpose": "Core infrastructure FSA"
        },
        "Integration": {
            "name": "IntegrationExample",
            "category": "Integration",
            "purpose": "External integration FSA"
        },
        "Meta": {
            "name": "MetaExample",
            "category": "Meta",
            "purpose": "Meta FSA that operates on FSAs"
        },
        "Domain": {
            "name": "DomainExample",
            "category": "Domain",
            "purpose": "Domain-specific FSA"
        }
    }

    for category, spec in categories.items():
        try:
            implementation = generator.generate_fsa(spec)
            print(f"✓ {category}: {implementation.spec.class_name}")
        except Exception as e:
            print(f"✗ {category}: Failed - {e}")


def run_all_examples():
    """Run all examples"""
    print("\n" + "="*80)
    print(" FSA Generator - Comprehensive Examples ".center(80, "="))
    print("="*80)

    examples = [
        example_basic_generation,
        example_detailed_specification,
        example_from_json_file,
        example_meta_fsa,
        example_error_handling,
        example_validation,
        example_batch_generation,
        example_custom_templates,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\n✗ Example failed: {e}")

    print("\n" + "="*80)
    print(" Examples Complete ".center(80, "="))
    print("="*80)


if __name__ == "__main__":
    # Run all examples
    run_all_examples()

    # Or run individual examples:
    # example_basic_generation()
    # example_detailed_specification()
    # example_from_json_file()
    # example_meta_fsa()
    # example_error_handling()
    # example_validation()
    # example_batch_generation()
    # example_custom_templates()
