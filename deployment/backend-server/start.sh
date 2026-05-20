#!/bin/bash
# Backend Start Script

set -e

BACKEND_DIR="/var/www/chatbot-backend"

echo "=== Starting Chatbot Backend ==="

# Check if .env file exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "ERROR: .env file not found at $BACKEND_DIR/.env"
    echo "Please copy .env.example to .env and update with your configuration"
    exit 1
fi

# Activate virtual environment and start backend
cd "$BACKEND_DIR"
source venv/bin/activate

echo "Starting Backend Service..."
sudo systemctl start chatbot-backend

echo "Checking service status..."
sleep 2
sudo systemctl status chatbot-backend

echo "✅ Backend started successfully!"
echo "View logs with: sudo journalctl -u chatbot-backend -f"
