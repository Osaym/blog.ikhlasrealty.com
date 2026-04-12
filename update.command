#!/bin/bash

# Simple monthly blog update
# Double-click this file to run the update

cd "$(dirname "$0")"

echo "======================================"
echo "Monthly Blog Update"
echo "======================================"
echo ""

# Check if venv exists
if [ ! -d "automation/.venv" ]; then
    echo "Setting up Python environment..."
    python3 -m venv automation/.venv
    automation/.venv/bin/pip install -q -r automation/requirements.txt
    echo ""
fi

# Run the update
automation/.venv/bin/python automation/update.py

echo ""
echo "======================================"
echo "Done! Review the files, then push via"
echo "GitHub Desktop to publish."
echo "======================================"
echo ""
echo "Press any key to close..."
read -n 1
