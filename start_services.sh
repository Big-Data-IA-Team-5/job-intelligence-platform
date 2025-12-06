#!/bin/bash
# Startup script for Job Intelligence Platform

echo "🚀 Starting Job Intelligence Platform..."

# Kill any existing processes
pkill -f "uvicorn.*8000" 2>/dev/null
pkill -f "streamlit.*8501" 2>/dev/null
sleep 2

# Start backend
echo "📡 Starting Backend API (port 8000)..."
cd /Users/pranavpatel/Desktop/job-intelligence-platform/backend
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend started with PID: $BACKEND_PID"

sleep 3

# Start frontend
echo "🎨 Starting Frontend (port 8501)..."
cd /Users/pranavpatel/Desktop/job-intelligence-platform/frontend
nohup streamlit run Home.py --server.port 8501 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend started with PID: $FRONTEND_PID"

sleep 3

# Check status
echo ""
echo "✅ Services Status:"
if ps -p $BACKEND_PID > /dev/null; then
    echo "   ✅ Backend API: http://localhost:8000"
else
    echo "   ❌ Backend failed to start (check /tmp/backend.log)"
fi

if ps -p $FRONTEND_PID > /dev/null; then
    echo "   ✅ Frontend:    http://localhost:8501"
else
    echo "   ❌ Frontend failed to start (check /tmp/frontend.log)"
fi

echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "🛑 To stop services:"
echo "   pkill -f 'uvicorn.*8000'"
echo "   pkill -f 'streamlit.*8501'"
