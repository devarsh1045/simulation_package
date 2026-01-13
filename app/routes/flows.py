from flask import Blueprint, jsonify, request
from ..state import STATE
from ..services.route_builder import update_route_file

bp_flows = Blueprint("flows", __name__)

@bp_flows.route("/update_flow", methods=["POST"])
def update_flow():
    if STATE.simulation_running:
        return jsonify({"status": "error", "message": "Stop simulation before updating flow rates"}), 400

    data = request.json or {}
    booth = data.get("booth")
    rate = data.get("rate")

    if booth in STATE.flow_rates:
        try:
            STATE.flow_rates[booth] = int(rate)
            update_route_file(STATE)
            return jsonify({"status": "success", "flow_rates": STATE.flow_rates})
        except:
            return jsonify({"status": "error", "message": "Invalid rate value"}), 400

    return jsonify({"status": "error", "message": "Invalid booth"}), 400

@bp_flows.route("/reset_flows", methods=["POST"])
def reset_flows():
    for i in range(20):
        STATE.flow_rates[f"booth_{i}"] = 100
    update_route_file(STATE)
    return jsonify({"status": "success", "flow_rates": STATE.flow_rates})
