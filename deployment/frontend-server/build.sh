#!/bin/bash
# Frontend Build Script for Ubuntu Deployment

set -e

echo "=== Frontend Build Script ==="
echo "Building frontend for production..."

# Check if Node.js and npm are installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Navigate to frontend directory
cd "$(dirname "$0")/app"

# Install dependencies
echo "Installing dependencies..."
npm install

# Build the application
echo "Building application..."
npm run build

# The built files will be in dist/ directory
echo "✅ Build complete! Output in: dist/"
echo "Ready for deployment."
