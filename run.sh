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

echo "📦 Installing GUI dependencies..."
cd app && npm install && cd ..

echo "🚀 Starting Vocalize AI Desktop App..."
echo "Press Right Option to toggle recording. Quit the app to exit."
npm start --prefix app
