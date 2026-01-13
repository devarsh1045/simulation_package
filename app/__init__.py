from flask import Flask
from .routes.pages import bp_pages
from .routes.control import bp_control
from .routes.flows import bp_flows
from .routes.lanes import bp_lanes
from .routes.breakdowns import bp_breakdowns
from .routes.detectors import bp_detectors
from pathlib import Path
import os
import sys

# ============================================================================
# DYNAMIC PATH CONFIGURATION - Works on any system
# ============================================================================

# Get the absolute path to THIS file (__init__.py inside app/)
CURRENT_FILE = Path(__file__).resolve()

# Go up one level to get the app/ directory
APP_DIR = CURRENT_FILE.parent

# Go up one more level to get the project root (simulation_package1/)
BASE_DIR = APP_DIR.parent

# Templates folder (simulation_package1/templates/)
TEMPLATES_DIR = BASE_DIR / "templates"

# Static folder (simulation_package1/static/) - if you have one
STATIC_DIR = BASE_DIR / "static"

# Print paths for debugging (optional - remove in production)
print(f"[PATH CONFIG]")
print(f"  Base Directory: {BASE_DIR}")
print(f"  Templates Directory: {TEMPLATES_DIR}")
print(f"  App Directory: {APP_DIR}")

# Add BASE_DIR to Python path so imports work
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ============================================================================
# IMPORT SCALING CONFIG
# ============================================================================

try:
    import scaling_config as scale
    print(f"[SCALING] Configuration loaded successfully")
except ImportError as e:
    print(f"[WARNING] Could not import scaling_config: {e}")
    scale = None

# ============================================================================
# CREATE APP FACTORY
# ============================================================================

def create_app():
    """Create and configure the Flask application"""
    
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),  # Convert Path to string
        static_folder=str(STATIC_DIR) if STATIC_DIR.exists() else None
    )
    
    # Set configuration
    app.config['BASE_DIR'] = str(BASE_DIR)
    app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
    
    # Register blueprints
    app.register_blueprint(bp_pages)
    app.register_blueprint(bp_control)
    app.register_blueprint(bp_flows)
    app.register_blueprint(bp_lanes)
    app.register_blueprint(bp_breakdowns)
    app.register_blueprint(bp_detectors)
    
    print(f"[FLASK] Application initialized successfully")
    
    return app