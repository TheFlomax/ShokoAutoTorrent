#!/bin/bash
# Startup script for ShokoAutoTorrent with optional Discord bot
set -e

echo "🚀 Starting ShokoAutoTorrent..."

# Track if cleanup has run
CLEANUP_DONE=false

# Cleanup function for graceful shutdown
cleanup() {
    if [ "$CLEANUP_DONE" = true ]; then
        return
    fi
    CLEANUP_DONE=true
    
    echo "🛑 Stopping services..."
    
    # Stop Python app first
    if [ -n "$PYTHON_PID" ] && kill -0 $PYTHON_PID 2>/dev/null; then
        kill -TERM $PYTHON_PID 2>/dev/null || true
        wait $PYTHON_PID 2>/dev/null || true
    fi
    
    # Then stop Discord bot
    if [ -n "$DISCORD_PID" ] && kill -0 $DISCORD_PID 2>/dev/null; then
        kill -TERM $DISCORD_PID 2>/dev/null || true
        wait $DISCORD_PID 2>/dev/null || true
    fi
    
    echo "✅ All services stopped"
}

trap cleanup SIGINT SIGTERM EXIT

# Start Discord bot if token is provided
if [ -n "$DISCORD_BOT_TOKEN" ]; then
    echo "🤖 Starting Discord bot..."
    cd /app/discord_bot
    node index.js &
    DISCORD_PID=$!
    cd /app
    echo "✅ Discord bot started (PID: $DISCORD_PID)"
else
    echo "⚠️  DISCORD_BOT_TOKEN not set, skipping Discord bot"
    DISCORD_PID=""
fi

# Small delay to let Discord bot initialize
sleep 2

# Start Python application
echo "🐍 Starting Python application..."
python main.py "$@" &
PYTHON_PID=$!
echo "✅ Python application started (PID: $PYTHON_PID)"

# Wait for both processes
if [ -n "$DISCORD_PID" ]; then
    wait $PYTHON_PID $DISCORD_PID
else
    wait $PYTHON_PID
fi
