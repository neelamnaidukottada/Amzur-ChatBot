#!/bin/bash
# Backend Stop Script

echo "=== Stopping Chatbot Backend ==="
sudo systemctl stop chatbot-backend

echo "Checking service status..."
sleep 1
sudo systemctl status chatbot-backend

echo "✅ Backend stopped!"
