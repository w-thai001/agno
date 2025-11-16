"""💾 FSA Serialization Example

This example demonstrates saving and loading FSA state for persistence.

Run `pip install agno` to install dependencies.
"""

from agno.fsa.serialization import FSASerialization, SerializationFormat
from agno.fsa.base import FSA, FSAState


def main():
    """Demonstrate FSA Serialization"""

    print("\n" + "=" * 60)
    print("FSA SERIALIZATION")
    print("=" * 60)

    # Create serialization manager
    serializer = FSASerialization(
        name="Serializer",
        default_format=SerializationFormat.JSON,
        debug_mode=True
    )

    # Create an FSA to serialize
    test_fsa = FSA(name="TestFSA", initial_state=FSAState.INITIAL)
    test_fsa.add_transition(FSAState.INITIAL, FSAState.RUNNING,
                           action=lambda ctx: {**ctx, "step": 1})
    test_fsa.add_transition(FSAState.RUNNING, FSAState.SUCCESS,
                           condition=lambda ctx: ctx.get("step", 0) >= 1)

    # Run FSA partway
    test_fsa.step()  # Execute first transition
    test_fsa.context["data"] = "important state"

    print(f"\n✅ Created FSA: {test_fsa.name}")
    print(f"   Current state: {test_fsa.current_state}")
    print(f"   Context: {test_fsa.context}")

    # Example 1: Create checkpoint
    print("\n--- Example 1: Create Checkpoint ---")

    checkpoint = serializer.create_checkpoint(
        test_fsa,
        checkpoint_id="checkpoint-1",
        metadata={"description": "Mid-execution checkpoint"}
    )

    print(f"\n✅ Created checkpoint: {checkpoint.checkpoint_id}")
    print(f"   FSA: {checkpoint.fsa_name}")
    print(f"   State: {checkpoint.current_state}")
    print(f"   Timestamp: {checkpoint.timestamp}")
    print(f"   Context size: {len(str(checkpoint.context))} chars")

    # Example 2: Save checkpoint to file
    print("\n--- Example 2: Save Checkpoint to File ---")

    # Save as JSON
    json_file = "/tmp/checkpoint.json"
    serializer.save_checkpoint(checkpoint, json_file, format=SerializationFormat.JSON)
    print(f"\n✅ Saved checkpoint to JSON: {json_file}")

    # Save as YAML (if available)
    try:
        yaml_file = "/tmp/checkpoint.yaml"
        serializer.save_checkpoint(checkpoint, yaml_file, format=SerializationFormat.YAML)
        print(f"✅ Saved checkpoint to YAML: {yaml_file}")
    except ImportError:
        print("⚠️  YAML format not available (install PyYAML)")

    # Example 3: Load checkpoint
    print("\n--- Example 3: Load Checkpoint ---")

    loaded_checkpoint = serializer.load_checkpoint(json_file)
    print(f"\n✅ Loaded checkpoint: {loaded_checkpoint.checkpoint_id}")
    print(f"   FSA: {loaded_checkpoint.fsa_name}")
    print(f"   State: {loaded_checkpoint.current_state}")
    print(f"   Context: {loaded_checkpoint.context}")

    # Example 4: Export/Import Configuration
    print("\n--- Example 4: Export Configuration ---")

    config = serializer.export_configuration(test_fsa)
    print(f"\n✅ Exported configuration:")
    print(f"   Name: {config.name}")
    print(f"   Initial state: {config.initial_state}")
    print(f"   Final states: {config.final_states}")
    print(f"   Max transitions: {config.max_transitions}")
    print(f"   Debug mode: {config.debug_mode}")

    # Save configuration
    config_file = "/tmp/fsa_config.json"
    serializer.save_configuration(config, config_file)
    print(f"\n✅ Saved configuration to: {config_file}")

    # Load configuration
    loaded_config = serializer.load_configuration(config_file)
    print(f"✅ Loaded configuration: {loaded_config.name}")

    # Example 5: List checkpoints
    print("\n--- Example 5: Checkpoint Management ---")

    # Create more checkpoints
    for i in range(2, 5):
        test_fsa.step()
        serializer.create_checkpoint(test_fsa, checkpoint_id=f"checkpoint-{i}")

    checkpoints = serializer.list_checkpoints()
    print(f"\n✅ Total checkpoints: {len(checkpoints)}")

    for i, cp in enumerate(checkpoints, 1):
        print(f"   {i}. {cp.checkpoint_id}")
        print(f"      State: {cp.current_state}")
        print(f"      Time: {cp.timestamp}")

    # Get latest checkpoint
    latest = serializer.get_latest_checkpoint("TestFSA")
    if latest:
        print(f"\n✅ Latest checkpoint: {latest.checkpoint_id}")
        print(f"   State: {latest.current_state}")

    # Example 6: Export all checkpoints
    print("\n--- Example 6: Batch Export/Import ---")

    export_dir = "/tmp/fsa_checkpoints"
    exported_files = serializer.export_all_checkpoints(
        export_dir,
        format=SerializationFormat.JSON
    )

    print(f"\n✅ Exported {len(exported_files)} checkpoints to: {export_dir}")
    for f in exported_files[:3]:  # Show first 3
        print(f"   - {f}")

    # Example 7: Import checkpoints from directory
    print("\n--- Example 7: Import from Directory ---")

    # Create new serializer
    new_serializer = FSASerialization(name="NewSerializer")

    imported_count = new_serializer.import_checkpoints_from_directory(
        export_dir,
        format=SerializationFormat.JSON
    )

    print(f"\n✅ Imported {imported_count} checkpoints")

    # Show summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nCheckpoints created: {len(serializer.checkpoints)}")
    print(f"Checkpoints exported: {len(exported_files)}")
    print(f"Checkpoints imported: {imported_count}")
    print(f"\n💾 Serialization enables:")
    print("   - State persistence across restarts")
    print("   - Checkpoint and resume execution")
    print("   - Configuration management")
    print("   - Distributed FSA state sharing")


if __name__ == "__main__":
    main()
