#!/bin/bash

# Checkpoint file recovery script for Linux
# Using ONLY direct path operations - no file listing

# Define checkpoint paths (Linux temp directory is /tmp)
checkpoint_paths=(
    "/tmp/fsa_marathon_state.json"
    "/tmp/fsa_marathon_recovery.json"
    "/tmp/fsa_marathon_checkpoint.json"
    "/tmp/fsa_state.json"
    "/tmp/agno_checkpoint.json"
    "$HOME/.agno/fsa_marathon_state.json"
    "$HOME/.agno/fsa_state.json"
    "$HOME/.cache/fsa_marathon_state.json"
    "/tmp/.agno/fsa_marathon_state.json"
)

# Initialize recovery data structure
echo "{"
echo "  \"timestamp\": \"$(date '+%Y-%m-%d %H:%M:%S')\","
echo "  \"files_found\": ["

found_files=()
missing_files=()
recovered_data=()

# Check each path
for path in "${checkpoint_paths[@]}"; do
    if [ -f "$path" ]; then
        found_files+=("$path")
    else
        missing_files+=("$path")
    fi
done

# Print found files
for i in "${!found_files[@]}"; do
    echo -n "    \"${found_files[$i]}\""
    if [ $i -lt $((${#found_files[@]} - 1)) ]; then
        echo ","
    else
        echo ""
    fi
done

echo "  ],"
echo "  \"files_missing\": ["

# Print missing files
for i in "${!missing_files[@]}"; do
    echo -n "    \"${missing_files[$i]}\""
    if [ $i -lt $((${#missing_files[@]} - 1)) ]; then
        echo ","
    else
        echo ""
    fi
done

echo "  ],"
echo "  \"recovered_data\": {"

# Recover data from found files
for i in "${!found_files[@]}"; do
    path="${found_files[$i]}"
    echo "    \"$path\": "

    # Try to read and validate JSON
    if content=$(cat "$path" 2>/dev/null); then
        # Check if it's valid JSON
        if echo "$content" | python3 -m json.tool > /dev/null 2>&1; then
            echo "$content" | python3 -m json.tool | sed 's/^/      /'
        else
            echo "      \"Error: Invalid JSON content\""
        fi
    else
        echo "      \"Error: Cannot read file\""
    fi

    if [ $i -lt $((${#found_files[@]} - 1)) ]; then
        echo "    ,"
    else
        echo ""
    fi
done

echo "  }"
echo "}"
