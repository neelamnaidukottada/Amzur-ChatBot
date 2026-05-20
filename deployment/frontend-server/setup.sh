#!/bin/bash
# Frontend Server Setup Script for Ubuntu

set -e

echo "=== Frontend Server Setup ==="

# Update system packages
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Node.js and npm
echo "Installing Node.js and npm..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Nginx
echo "Installing Nginx..."
sudo apt-get install -y nginx

# Create application directory
echo "Creating application directory..."
sudo mkdir -p /var/www/chatbot-frontend
sudo chown -R $USER:$USER /var/www/chatbot-frontend

# Configure Nginx
echo "Configuring Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/chatbot-frontend
sudo ln -sf /etc/nginx/sites-available/chatbot-frontend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "Testing Nginx configuration..."
sudo nginx -t

# Enable and start Nginx
echo "Starting Nginx..."
sudo systemctl enable nginx
sudo systemctl restart nginx

# Install SSL certificate (Optional - using Let's Encrypt)
echo ""
echo "For HTTPS setup with Let's Encrypt, run:"
echo "sudo apt-get install -y certbot python3-certbot-nginx"
echo "sudo certbot certonly --standalone -d your-domain.com"
echo "Then update nginx.conf with your certificate paths"
echo ""

echo "✅ Frontend server setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy your built frontend files to /var/www/chatbot-frontend/dist/"
echo "2. Update nginx.conf with your backend server IP (replace 'backend-server:8000')"
echo "3. Run: sudo systemctl restart nginx"
echo "4. Access your frontend at: http://$(hostname -I | awk '{print $1}')"
