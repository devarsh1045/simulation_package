# SUMO Simulation Setup Guide

## Prerequisites

- macOS (version specified in SYSTEM_INFO.md)
- Python (version specified in .python-version)
- SUMO (version specified in SYSTEM_INFO.md)

## Installation Steps

Create venv 
python3 -m venv .venv
Activate it
source .venv/bin/activate


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
