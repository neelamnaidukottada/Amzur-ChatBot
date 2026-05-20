#!/bin/bash
# Deployment Files Copy Script
# This script prepares the deployment folders with your project source

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."

echo "========================================="
echo "  Deployment Preparation Script"
echo "========================================="
echo ""

# Check if source directories exist
if [ ! -d "$PROJECT_ROOT/frontend" ]; then
    echo "❌ ERROR: Frontend directory not found at $PROJECT_ROOT/frontend"
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/backend" ]; then
    echo "❌ ERROR: Backend directory not found at $PROJECT_ROOT/backend"
    exit 1
fi

echo "Preparing deployment files..."
echo ""

# Copy frontend source
echo "📦 Copying frontend source..."
mkdir -p "$SCRIPT_DIR/frontend-server/app"
cp -r "$PROJECT_ROOT/frontend/"* "$SCRIPT_DIR/frontend-server/app/" 2>/dev/null || true
echo "✅ Frontend copied to deployment/frontend-server/app"

# Copy backend source
echo "📦 Copying backend source..."
mkdir -p "$SCRIPT_DIR/backend-server/app"
cp -r "$PROJECT_ROOT/backend/app"/* "$SCRIPT_DIR/backend-server/app/" 2>/dev/null || true
cp "$PROJECT_ROOT/backend/requirements.txt" "$SCRIPT_DIR/backend-server/" 2>/dev/null || true
echo "✅ Backend copied to deployment/backend-server/app"

# Copy mcp_server
echo "📦 Copying MCP server..."
mkdir -p "$SCRIPT_DIR/backend-server/mcp_server"
cp -r "$PROJECT_ROOT/mcp_server/"* "$SCRIPT_DIR/backend-server/mcp_server/" 2>/dev/null || true
echo "✅ MCP server copied"

echo ""
echo "========================================="
echo "  ✅ Deployment files ready!"
echo "========================================="
echo ""
echo "📁 Deployment structure:"
echo ""
echo "deployment/"
echo "├── DEPLOYMENT_GUIDE.md          # Read this first!"
echo "├── QUICK_START.md               # Fast 5-minute setup"
echo "├── README.md                    # Structure overview"
echo "├── DEPLOYMENT_CHECKLIST.md      # Use this to verify"
echo "├── ARCHITECTURE.md              # System design"
echo "│"
echo "├── frontend-server/             # ⬅️ Copy entire folder to Frontend Server"
echo "│   ├── setup.sh                 # Run: sudo ./setup.sh"
echo "│   ├── build.sh                 # Run: ./build.sh"
echo "│   ├── nginx.conf"
echo "│   ├── .env.example"
echo "│   ├── app/                     # ✅ Your frontend source"
echo "│   └── docker-compose.yml       # Optional: Docker setup"
echo "│"
echo "├── backend-server/              # ⬅️ Copy entire folder to Backend Server"
echo "│   ├── setup.sh                 # Run: sudo ./setup.sh"
echo "│   ├── start.sh                 # Run: ./start.sh"
echo "│   ├── stop.sh"
echo "│   ├── Dockerfile"
echo "│   ├── requirements.txt          # ✅ Your dependencies"
echo "│   ├── .env.example"
echo "│   ├── app/                     # ✅ Your backend source"
echo "│   ├── mcp_server/              # ✅ Your MCP server"
echo "│   └── docker-compose.yml       # Optional: Docker setup"
echo "│"
echo "└── shared-config/               # Reference guides"
echo "    ├── DATABASE_SETUP.md        # PostgreSQL setup"
echo "    ├── SSL_SETUP.md             # HTTPS setup"
echo "    └── TROUBLESHOOTING.md       # Common issues"
echo ""
echo "========================================="
echo "  🚀 Next Steps"
echo "========================================="
echo ""
echo "1. Read QUICK_START.md for 5-minute deployment"
echo "2. Or read DEPLOYMENT_GUIDE.md for detailed instructions"
echo ""
echo "3. Deploy Frontend Server:"
echo "   scp -r deployment/frontend-server/* user@frontend-ip:/tmp/deploy/"
echo "   ssh user@frontend-ip"
echo "   cd /tmp/deploy && sudo ./setup.sh && ./build.sh"
echo ""
echo "4. Deploy Backend Server:"
echo "   scp -r deployment/backend-server/* user@backend-ip:/tmp/deploy/"
echo "   ssh user@backend-ip"
echo "   cd /tmp/deploy && sudo ./setup.sh"
echo ""
echo "5. Use DEPLOYMENT_CHECKLIST.md to verify everything"
echo ""
echo "========================================="
echo ""
