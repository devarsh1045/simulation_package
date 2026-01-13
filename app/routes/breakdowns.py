from flask import Blueprint, jsonify, request
from ..state import STATE

bp_breakdowns = Blueprint("breakdowns", __name__)

@bp_breakdowns.route("/trigger_breakdown", methods=["POST"])
def trigger_breakdown():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    booth = data.get("booth")
    if booth in STATE.breakdown_status:
        STATE.breakdown_status[booth] = True
        return jsonify({"status": "success", "message": f"Breakdown triggered for {booth}"})
    return jsonify({"status": "error", "message": "Invalid booth"}), 400

@bp_breakdowns.route("/clear_breakdown", methods=["POST"])
def clear_breakdown():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    booth = data.get("booth")
    if booth in STATE.breakdown_status:
        STATE.breakdown_status[booth] = False
        return jsonify({"status": "success", "message": f"Breakdown cleared for {booth}"})
    return jsonify({"status": "error", "message": "Invalid booth"}), 400

@bp_breakdowns.route("/clear_all_breakdowns", methods=["POST"])
def clear_all_breakdowns():
    for k in STATE.breakdown_status:
        STATE.breakdown_status[k] = False
    for k in STATE.mainlane_breakdown_status:
        STATE.mainlane_breakdown_status[k] = False
    for k in STATE.bridge_breakdown_status:
        STATE.bridge_breakdown_status[k] = False
    return jsonify({"status": "success", "message": "All breakdowns cleared"})

@bp_breakdowns.route("/break_main_lane", methods=["POST"])
def break_main_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.mainlane_breakdown_status:
        STATE.mainlane_breakdown_status[lane] = True
        return jsonify({"status": "success", "message": f"Breakdown triggered for {lane}"})
    return jsonify({"status": "error", "message": "Invalid main lane"}), 400

@bp_breakdowns.route("/fix_main_lane", methods=["POST"])
def fix_main_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.mainlane_breakdown_status:
        STATE.mainlane_breakdown_status[lane] = False
        return jsonify({"status": "success", "message": f"Breakdown cleared for {lane}"})
    return jsonify({"status": "error", "message": "Invalid main lane"}), 400

@bp_breakdowns.route("/break_bridge_lane", methods=["POST"])
def break_bridge_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.bridge_breakdown_status:
        STATE.bridge_breakdown_status[lane] = True
        return jsonify({"status": "success", "message": f"Breakdown triggered for {lane}"})
    return jsonify({"status": "error", "message": "Invalid bridge lane"}), 400

@bp_breakdowns.route("/fix_bridge_lane", methods=["POST"])
def fix_bridge_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.bridge_breakdown_status:
        STATE.bridge_breakdown_status[lane] = False
        return jsonify({"status": "success", "message": f"Breakdown cleared for {lane}"})
    return jsonify({"status": "error", "message": "Invalid bridge lane"}), 400
