#!/bin/bash

# Stock Analysis Application Startup Script

echo "================================"
echo "Stock Analysis Application"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "Starting Flask application on port 8000..."
echo "Press Ctrl+C to stop the server"
echo ""

# Run the application
python app.py