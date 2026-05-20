#!/bin/bash
# Backend Setup Script for Ubuntu

set -e

echo "=== Backend Server Setup ==="

# Update system packages
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and pip
echo "Installing Python and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install PostgreSQL client (for database connections)
echo "Installing PostgreSQL client..."
sudo apt-get install -y postgresql-client libpq-dev

# Create application directory
echo "Creating application directory..."
sudo mkdir -p /var/www/chatbot-backend
sudo chown -R $USER:$USER /var/www/chatbot-backend

# Create virtual environment
echo "Setting up Python virtual environment..."
cd /var/www/chatbot-backend
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Create systemd service file
echo "Setting up systemd service..."
sudo tee /etc/systemd/system/chatbot-backend.service > /dev/null <<EOF
[Unit]
Description=Amzur Chatbot Backend Service
After=network.target

[Service]
Type=notify
User=$USER
WorkingDirectory=/var/www/chatbot-backend
Environment="PATH=/var/www/chatbot-backend/venv/bin"
ExecStart=/var/www/chatbot-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable chatbot-backend

echo "✅ Backend server setup complete!"
echo ""
echo "Next steps:"
echo "1. Update /var/www/chatbot-backend/.env with your configuration:"
echo "   - DATABASE_URL (PostgreSQL connection string)"
echo "   - LITELLM_API_KEY (Amzur LiteLLM proxy key)"
echo "   - GOOGLE_GEMINI_API_KEY (Google API key)"
echo "   - SECRET_KEY (Change to a secure random key)"
echo ""
echo "2. Copy backend files to /var/www/chatbot-backend/"
echo "3. Run: sudo systemctl start chatbot-backend"
echo "4. Check status: sudo systemctl status chatbot-backend"
echo "5. View logs: sudo journalctl -u chatbot-backend -f"
