#!/bin/bash

# Construction Analysis Agent - Start Script
# Version 2.0.0 with LangChain 0.3.12 and LangGraph 0.2.63

echo "🏗️  Construction Analysis Agent System"
echo "====================================="
echo "Version: 2.0.0"
echo "LangChain: 0.3.12 | LangGraph: 0.2.63"
echo ""

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "⚠️  Python 3.9+ is required. Current version: $python_version"
    exit 1
fi
echo "✅ Python $python_version detected"

# Check if .env file exists
if [ ! -f "backend/.env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp backend/.env.example backend/.env
    echo "📝 Please edit backend/.env with your OpenAI API key"
    echo "Press any key to continue after editing..."
    read -n 1
fi

# Install backend dependencies
echo ""
echo "📦 Installing backend dependencies..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Backend dependencies installed"

# Start backend server
echo ""
echo "🚀 Starting backend server..."
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Backend server started with PID: $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
sleep 5

# Check backend health
curl -s http://localhost:8000/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed"
fi

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install
fi

echo "✅ Frontend dependencies installed"

# Start frontend
echo ""
echo "🎨 Starting frontend..."
npm start &
FRONTEND_PID=$!

echo "Frontend started with PID: $FRONTEND_PID"

# Display access information
echo ""
echo "🎉 System is ready!"
echo "=================="
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "💡 Features:"
echo "  • Conversational AI Chat"
echo "  • Nano Banana Image Analysis"
echo "  • Document Processing"
echo "  • Progress Monitoring"
echo "  • JSON Report Generation"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for interrupt
trap "echo '\nStopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait