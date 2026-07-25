#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "====================================="
echo "Switching to Docker Environment Configuration"
echo "====================================="
echo

cd "$(dirname "$0")/../../frontend/contentgruen-frontend/src/environments"

# Reset to Docker configuration
cat > environment.ts << 'EOF'
export const environment = {
  production: false,
  baseUrl: '',
  clientId: 'contentgruen',
  mockAuth: true
};
EOF

echo -e "${GREEN}[OK]${NC} environment.ts has been reset to Docker configuration"
echo
echo "Configuration:"
echo "- baseUrl: '' (uses nginx proxy)"
echo "- mockAuth: true (dummy authentication)"
echo
echo "====================================="
echo "Switch complete!"
echo "====================================="
