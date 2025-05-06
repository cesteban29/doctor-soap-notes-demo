#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up SOAP Note Generator Demo...${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create and activate virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Create .vscode directory if it doesn't exist
mkdir -p .vscode

# Create/update VS Code settings
echo -e "${BLUE}Configuring VS Code settings...${NC}"
cat > .vscode/settings.json << EOL
{
    "python.defaultInterpreterPath": "\${workspaceFolder}/.venv/bin/python3",
    "python.analysis.extraPaths": ["\${workspaceFolder}/.venv/lib/python3.13/site-packages"],
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.rulers": [88],
    "files.trimTrailingWhitespace": true
}
EOL

# Run the ETL pipeline
echo -e "${BLUE}Running ETL pipeline...${NC}"
echo -e "${GREEN}Step 1: Building dataset...${NC}"
python3 etl/build.py

echo -e "${GREEN}Step 2: Filtering complete dataset...${NC}"
python3 etl/filter_complete.py

echo -e "${GREEN}Step 3: Inserting dataset into Braintrust...${NC}"
python3 braintrust/insert_soap_dataset.py

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${BLUE}To activate the virtual environment in the future, run:${NC}"
echo "source .venv/bin/activate"