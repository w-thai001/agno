"""Test script for FSA Generator."""

import sys
sys.path.insert(0, '/home/user/agno/libs/agno')

from agno.fsa.generator import FSAGenerator


def test_traffic_light_fsa():
    """Test generating a traffic light FSA."""
    generator = FSAGenerator()

    # Define a simple traffic light FSA
    fsa_name = "TrafficLight"
    states = ["red", "yellow", "green"]
    transitions = {
        ("red", "timer"): "green",
        ("green", "timer"): "yellow",
        ("yellow", "timer"): "red",
    }
    purpose = "A simple traffic light FSA that cycles through red, green, and yellow states."

    # Generate the FSA code
    code = generator.generate(fsa_name, states, transitions, purpose)

    print("=" * 80)
    print("Generated Traffic Light FSA Code:")
    print("=" * 80)
    print(code)
    print("=" * 80)

    # Save to file
    output_file = "/home/user/agno/generated_traffic_light_fsa.py"
    generator.save_to_file(output_file)
    print(f"\nSaved to: {output_file}")

    # Test the generated FSA by executing it
    exec(code, globals())
    traffic_light = TrafficLight()

    print("\nTesting generated TrafficLight FSA:")
    print(f"Initial state: {traffic_light.get_state()}")

    # Run through a sequence
    result = traffic_light.run(["timer", "timer", "timer", "timer"])
    print(f"After 4 timer inputs: {result}")

    print("\nManual transitions:")
    traffic_light.reset()
    print(f"State: {traffic_light.get_state()}")
    traffic_light.transition("timer")
    print(f"After timer: {traffic_light.get_state()}")
    traffic_light.transition("timer")
    print(f"After timer: {traffic_light.get_state()}")
    print(f"Available transitions: {traffic_light.get_available_transitions()}")


def test_door_fsa():
    """Test generating a door FSA."""
    generator = FSAGenerator()

    fsa_name = "Door"
    states = ["locked", "closed", "open"]
    transitions = {
        ("locked", "unlock"): "closed",
        ("closed", "lock"): "locked",
        ("closed", "open"): "open",
        ("open", "close"): "closed",
    }
    purpose = "A door FSA that models locked, closed, and open states."

    code = generator.generate(fsa_name, states, transitions, purpose)

    print("\n" + "=" * 80)
    print("Generated Door FSA Code:")
    print("=" * 80)
    print(code)
    print("=" * 80)

    # Save to file
    output_file = "/home/user/agno/generated_door_fsa.py"
    generator.save_to_file(output_file)
    print(f"\nSaved to: {output_file}")

    # Test the generated FSA
    exec(code, globals())
    door = Door()

    print("\nTesting generated Door FSA:")
    print(f"Initial state: {door.get_state()}")

    result = door.run(["unlock", "open", "close", "lock"])
    print(f"After unlock->open->close->lock: {result}")


if __name__ == "__main__":
    print("Testing FSA Generator\n")
    test_traffic_light_fsa()
    test_door_fsa()
    print("\n✓ All tests completed successfully!")
