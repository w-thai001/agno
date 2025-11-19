#!/usr/bin/env python3
"""
FSA Marathon State Recovery Script
Phase 1: Locate and load checkpoint files
"""

import os
import json
import glob
from pathlib import Path
from datetime import datetime

def find_checkpoint_files():
    """Search for checkpoint files in multiple locations"""
    search_paths = [
        '/tmp/fsa_marathon_*.json',
        '/home/user/fsa_marathon_*.json',
        '/home/user/.cache/fsa_marathon_*.json',
        '/home/user/agno/fsa_marathon_*.json',
        '/home/user/agno/.fsa_marathon_*.json',
        './fsa_marathon_*.json',
    ]

    found_files = []
    for pattern in search_paths:
        matches = glob.glob(pattern)
        found_files.extend(matches)

    return list(set(found_files))  # Remove duplicates

def load_json_safe(filepath):
    """Safely load JSON file with error handling"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return {'success': True, 'data': data, 'error': None}
    except FileNotFoundError:
        return {'success': False, 'data': None, 'error': 'File not found'}
    except json.JSONDecodeError as e:
        return {'success': False, 'data': None, 'error': f'JSON decode error: {str(e)}'}
    except Exception as e:
        return {'success': False, 'data': None, 'error': f'Error: {str(e)}'}

def main():
    print("="*70)
    print("FSA MARATHON - PHASE 1: STATE RECOVERY")
    print("="*70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")
    print()

    # Search for checkpoint files
    print("Searching for checkpoint files...")
    checkpoint_files = find_checkpoint_files()

    if checkpoint_files:
        print(f"\n✓ Found {len(checkpoint_files)} checkpoint file(s):")
        for f in checkpoint_files:
            size = os.path.getsize(f)
            mtime = datetime.fromtimestamp(os.path.getmtime(f))
            print(f"  - {f}")
            print(f"    Size: {size} bytes, Modified: {mtime}")
    else:
        print("\n⚠ No checkpoint files found in standard locations")
        print("Searched patterns:")
        for pattern in ['/tmp/fsa_marathon_*.json', '/home/user/fsa_marathon_*.json',
                        '/home/user/.cache/fsa_marathon_*.json', './fsa_marathon_*.json']:
            print(f"  - {pattern}")

    print()

    # Try to load checkpoint data
    recovery_data = {}
    checkpoint_names = ['state', 'recovery', 'checkpoint', 'progress', 'session']

    for name in checkpoint_names:
        for base_path in ['/tmp', '/home/user', '/home/user/.cache', '/home/user/agno', '.']:
            filepath = os.path.join(base_path, f'fsa_marathon_{name}.json')
            if os.path.exists(filepath):
                result = load_json_safe(filepath)
                if result['success']:
                    recovery_data[name] = result['data']
                    print(f"✓ Loaded: {filepath}")
                else:
                    print(f"✗ Failed to load {filepath}: {result['error']}")

    # Save recovery summary
    recovery_summary = {
        'timestamp': datetime.now().isoformat(),
        'checkpoint_files_found': checkpoint_files,
        'recovery_data_keys': list(recovery_data.keys()),
        'recovery_data': recovery_data,
        'working_directory': os.getcwd()
    }

    output_file = '/tmp/fsa_recovery_summary.json'
    with open(output_file, 'w') as f:
        json.dump(recovery_summary, f, indent=2)

    print()
    print("="*70)
    print("PHASE 1 SUMMARY")
    print("="*70)
    print(f"Checkpoint files found: {len(checkpoint_files)}")
    print(f"Data sets recovered: {len(recovery_data)}")
    print(f"Recovery summary saved to: {output_file}")
    print()

    if recovery_data:
        print("Recovered data contains:")
        for key, data in recovery_data.items():
            if isinstance(data, dict):
                print(f"  - {key}: {len(data)} keys")
            elif isinstance(data, list):
                print(f"  - {key}: {len(data)} items")
            else:
                print(f"  - {key}: {type(data).__name__}")

    return recovery_summary

if __name__ == '__main__':
    summary = main()
