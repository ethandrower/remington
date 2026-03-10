#!/bin/bash
# Start PM Agent Dashboard
# Simple Flask + Vue.js dashboard for monitoring checks

echo "=================================================="
echo "🤖 Starting PM Agent Dashboard"
echo "=================================================="
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Set default port
export DASHBOARD_PORT=${DASHBOARD_PORT:-8080}

echo "🚀 Starting dashboard on port $DASHBOARD_PORT"
echo "   Access at: http://localhost:$DASHBOARD_PORT"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

# Start Flask app
python src/dashboard/app.py
