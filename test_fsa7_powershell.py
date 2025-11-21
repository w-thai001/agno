"""
Test script for FSA-7 PowerShell file operations
"""

from fsa7_ontology_builder import OntologyBuilder
import os
import sys

def test_powershell_operations():
    """Test PowerShell-only file operations"""
    print("Testing FSA-7 PowerShell File Operations")
    print("=" * 80)

    # Initialize ontology
    print("\n1. Initializing ontology...")
    ontology = OntologyBuilder()
    print(f"   ✓ Loaded {len(ontology.entities)} FSAs")

    # Test JSON export
    print("\n2. Testing JSON export via PowerShell...")
    json_file = "fsa7_ontology_export.json"
    try:
        ontology.save_to_file_powershell(json_file, format='json')
        print(f"   ✓ Successfully exported to {json_file}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test GraphML export
    print("\n3. Testing GraphML export via PowerShell...")
    graphml_file = "fsa7_ontology_export.graphml"
    try:
        ontology.save_to_file_powershell(graphml_file, format='graphml')
        print(f"   ✓ Successfully exported to {graphml_file}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test JSON import
    print("\n4. Testing JSON import via PowerShell...")
    try:
        new_ontology = OntologyBuilder()
        new_ontology.entities.clear()  # Clear default data
        new_ontology.relationships.clear()
        new_ontology.load_from_file_powershell(json_file, format='json')
        print(f"   ✓ Successfully imported {len(new_ontology.entities)} FSAs")
        print(f"   ✓ Successfully imported {len(new_ontology.relationships)} relationships")

        # Verify data integrity
        if len(new_ontology.entities) == len(ontology.entities):
            print("   ✓ Data integrity verified")
        else:
            print("   ✗ Data integrity check failed")
            return False

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test semantic queries on loaded ontology
    print("\n5. Testing semantic queries on loaded ontology...")
    try:
        deps = new_ontology.find_dependencies("FSA-2")
        print(f"   ✓ Found {len(deps)} dependencies for FSA-2")

        path = new_ontology.calculate_curriculum_path("FSA-1", "FSA-8")
        print(f"   ✓ Calculated curriculum path with {len(path)} FSAs")

        validation = new_ontology.validate_workflow(["FSA-1", "FSA-7", "FSA-8"])
        print(f"   ✓ Workflow validation: {validation.is_valid}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    print("\n" + "=" * 80)
    print("All PowerShell file operations tests passed! ✓")
    print("=" * 80)

    return True

if __name__ == "__main__":
    success = test_powershell_operations()
    sys.exit(0 if success else 1)
