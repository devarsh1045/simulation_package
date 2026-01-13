from flask import Flask
from .routes.pages import bp_pages
from .routes.control import bp_control
from .routes.flows import bp_flows
from .routes.lanes import bp_lanes
from .routes.breakdowns import bp_breakdowns
from .routes.detectors import bp_detectors
from pathlib import Path
import scaling_config as scale
BASE_DIR = "/Users/devarshkunala/Documents/Thinkdigits/simulation_package1"

def create_app():
    app = Flask(
        __name__,
        template_folder="/Users/devarshkunala/Documents/Thinkdigits/simulation_package1/templates")

    app.register_blueprint(bp_pages)
    app.register_blueprint(bp_control)
    app.register_blueprint(bp_flows)
    app.register_blueprint(bp_lanes)
    app.register_blueprint(bp_breakdowns)
    app.register_blueprint(bp_detectors)

    return app