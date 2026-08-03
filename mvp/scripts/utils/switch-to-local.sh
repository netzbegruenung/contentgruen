#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "====================================="
echo "Switching to Local Environment Configuration"
echo "====================================="
echo

cd "$(dirname "$0")/../../frontend/contentgruen-frontend/src/environments"

# Switch to local configuration
cat > environment.ts << 'EOF'
export const environment = {
  production: false,
  baseUrl: 'http://localhost:5054',
  clientId: 'contentgruen',
  mockAuth: true
};
EOF

echo -e "${GREEN}[OK]${NC} environment.ts has been set to local configuration"
echo
echo "Configuration:"
echo "- baseUrl: 'http://localhost:5054' (direct BFF connection)"
echo "- mockAuth: true (dummy authentication)"
echo
echo "====================================="
echo "Switch complete!"
echo "====================================="
