#!/bin/bash

# SUMO Environment Documentation Script
# This script documents your complete SUMO simulation environment

echo "🔍 Gathering environment information..."
echo ""

# Create a timestamp
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# ============================================
# 1. Create SYSTEM_INFO.md
# ============================================
cat > SYSTEM_INFO.md << EOF
# SUMO Simulation Environment Documentation

**Generated:** $TIMESTAMP

## System Information

EOF

# macOS Version
echo "### Operating System" >> SYSTEM_INFO.md
echo "\`\`\`" >> SYSTEM_INFO.md
sw_vers >> SYSTEM_INFO.md
echo "\`\`\`" >> SYSTEM_INFO.md
echo "" >> SYSTEM_INFO.md

# Python Version
echo "### Python Version" >> SYSTEM_INFO.md
echo "\`\`\`" >> SYSTEM_INFO.md
python3 --version >> SYSTEM_INFO.md
which python3 >> SYSTEM_INFO.md
echo "\`\`\`" >> SYSTEM_INFO.md
echo "" >> SYSTEM_INFO.md

# SUMO Version
echo "### SUMO Version" >> SYSTEM_INFO.md
echo "\`\`\`" >> SYSTEM_INFO.md
if command -v sumo &> /dev/null; then
    sumo --version 2>&1 | head -5 >> SYSTEM_INFO.md
else
    echo "SUMO not found in PATH" >> SYSTEM_INFO.md
fi
echo "\`\`\`" >> SYSTEM_INFO.md
echo "" >> SYSTEM_INFO.md

# SUMO Installation Path
echo "### SUMO Installation" >> SYSTEM_INFO.md
echo "\`\`\`" >> SYSTEM_INFO.md
if command -v sumo &> /dev/null; then
    echo "SUMO Path: $(which sumo)" >> SYSTEM_INFO.md
    echo "SUMO_HOME: $SUMO_HOME" >> SYSTEM_INFO.md
else
    echo "SUMO not found" >> SYSTEM_INFO.md
fi
echo "\`\`\`" >> SYSTEM_INFO.md
echo "" >> SYSTEM_INFO.md

echo "✅ Created SYSTEM_INFO.md"

# ============================================
# 2. Create .python-version
# ============================================
python3 --version | awk '{print $2}' > .python-version
echo "✅ Created .python-version ($(cat .python-version))"

# ============================================
# 3. Generate requirements.txt
# ============================================
echo ""
echo "📦 Generating requirements.txt..."

# Check if pipreqs is installed
if ! command -v pipreqs &> /dev/null; then
    echo "⚠️  pipreqs not found. Installing..."
    pip3 install pipreqs
fi

# Generate requirements using pipreqs (scans actual imports)
if [ -f "requirements.txt" ]; then
    echo "⚠️  requirements.txt already exists. Creating backup..."
    mv requirements.txt requirements.txt.backup
fi

pipreqs . --force 2>/dev/null || pip3 freeze > requirements.txt

# Add Python version comment at the top
PYTHON_VERSION=$(python3 --version)
sed -i.bak "1i\\
# $PYTHON_VERSION\\
# Generated: $TIMESTAMP\\
" requirements.txt && rm requirements.txt.bak

echo "✅ Created requirements.txt"

# ============================================
# 4. Create README_SETUP.md
# ============================================
cat > README_SETUP.md << 'EOF'
# SUMO Simulation Setup Guide

## Prerequisites

- macOS (version specified in SYSTEM_INFO.md)
- Python (version specified in .python-version)
- SUMO (version specified in SYSTEM_INFO.md)

## Installation Steps

### 1. Install Python

```bash
# Using Homebrew
brew install python@3.x  # Replace x with version from .python-version

# Or using pyenv (recommended)
brew install pyenv
pyenv install $(cat .python-version)
pyenv local $(cat .python-version)
```

### 2. Install SUMO

```bash
# Using Homebrew
brew install sumo

# Set SUMO_HOME environment variable
echo 'export SUMO_HOME="/opt/homebrew/opt/sumo/share/sumo"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
python -c "import traci, sumolib; print('✓ SUMO Python libraries installed')"
```

## Running the Simulation

```bash
# Activate virtual environment
source venv/bin/activate

# Run your simulation
python your_simulation_script.py

# Or run SUMO GUI
sumo-gui -c your_config.sumocfg
```

## Troubleshooting

### SUMO Not Found
```bash
# Check if SUMO is installed
which sumo

# Check SUMO_HOME
echo $SUMO_HOME

# Set SUMO_HOME if needed
export SUMO_HOME="/opt/homebrew/opt/sumo/share/sumo"
```

### Python Import Errors
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Version Conflicts
Check SYSTEM_INFO.md for the exact versions used in the original setup.

## Updating Dependencies

```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Regenerate requirements.txt
pip freeze > requirements.txt
```

## Project Structure

```
your-project/
├── SYSTEM_INFO.md          # Complete system information
├── README_SETUP.md         # This file - setup instructions
├── .python-version         # Python version
├── requirements.txt        # Python dependencies
├── venv/                   # Virtual environment (not in git)
└── your simulation files...
```

## Additional Notes

- See SYSTEM_INFO.md for complete environment details
- Always activate the virtual environment before running simulations
- Keep requirements.txt updated when adding new dependencies
EOF

echo "✅ Created README_SETUP.md"

# ============================================
# 5. Create .gitignore if it doesn't exist
# ============================================
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
venv/
env/
ENV/

# SUMO
*.log
*.xml.gz
tripinfo.xml
summary.xml

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Backups
*.backup
*.bak
EOF
    echo "✅ Created .gitignore"
else
    echo "ℹ️  .gitignore already exists (skipped)"
fi

# ============================================
# Summary
# ============================================
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  📋 Documentation Complete!                ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "Created files:"
echo "  ✓ SYSTEM_INFO.md      - Complete system & version info"
echo "  ✓ README_SETUP.md     - Setup instructions"
echo "  ✓ .python-version     - Python version specification"
echo "  ✓ requirements.txt    - Python dependencies"
echo "  ✓ .gitignore         - Git ignore rules"
echo ""
echo "Next steps:"
echo "  1. Review SYSTEM_INFO.md to verify all information"
echo "  2. Read README_SETUP.md for setup instructions"
echo "  3. Commit these files to your repository"
echo ""
echo "To recreate this environment on another machine:"
echo "  → Follow the steps in README_SETUP.md"
echo ""