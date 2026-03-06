#!/bin/bash

# Ensure we are in the script directory
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "🚀 Starting AI Speech Tool..."
echo "Press F8 to toggle recording. Ctrl+C to exit."
python3 main.py
