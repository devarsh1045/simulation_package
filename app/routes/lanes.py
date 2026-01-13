from flask import Blueprint, jsonify, request
from ..state import STATE

bp_lanes = Blueprint("lanes", __name__)

@bp_lanes.route("/close_lane", methods=["POST"])
def close_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    booth = data.get("booth")
    if booth in STATE.lane_closure_status:
        STATE.lane_closure_status[booth] = True
        if booth in STATE.breakdown_status:
            STATE.breakdown_status[booth] = False
        return jsonify({"status": "success", "message": f"{booth} closed"})
    return jsonify({"status": "error", "message": "Invalid booth"}), 400

@bp_lanes.route("/open_lane", methods=["POST"])
def open_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    booth = data.get("booth")
    if booth in STATE.lane_closure_status:
        STATE.lane_closure_status[booth] = False
        return jsonify({"status": "success", "message": f"{booth} opened"})
    return jsonify({"status": "error", "message": "Invalid booth"}), 400

@bp_lanes.route("/close_main_lane", methods=["POST"])
def close_main_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.main_lane_ids and lane in STATE.lane_closure_status:
        STATE.lane_closure_status[lane] = True
        return jsonify({"status": "success", "message": f"{lane} closed"})
    return jsonify({"status": "error", "message": "Invalid main lane"}), 400

@bp_lanes.route("/open_main_lane", methods=["POST"])
def open_main_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.lane_closure_status:
        STATE.lane_closure_status[lane] = False
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@bp_lanes.route("/set_main_lane_mode", methods=["POST"])
def set_main_lane_mode():
    data = request.json or {}
    lane = data.get("lane")
    mode = data.get("mode")
    if lane not in STATE.main_lane_ids:
        return jsonify({"status": "error", "message": "Invalid main lane"}), 400
    if mode not in ("cars", "trucks", "both"):
        return jsonify({"status": "error", "message": "Invalid mode"}), 400
    STATE.main_lane_modes[lane] = mode
    return jsonify({"status": "success", "lane": lane, "mode": mode})

@bp_lanes.route("/close_bridge_lane", methods=["POST"])
def close_bridge_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.bridge_lane_ids and lane in STATE.lane_closure_status:
        STATE.lane_closure_status[lane] = True
        return jsonify({"status": "success", "message": f"{lane} closed"})
    return jsonify({"status": "error", "message": "Invalid bridge lane"}), 400

@bp_lanes.route("/open_bridge_lane", methods=["POST"])
def open_bridge_lane():
    if not STATE.simulation_running:
        return jsonify({"status": "error", "message": "Simulation not running"}), 400
    data = request.json or {}
    lane = data.get("lane")
    if lane in STATE.lane_closure_status:
        STATE.lane_closure_status[lane] = False
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@bp_lanes.route("/set_bridge_lane_mode", methods=["POST"])
def set_bridge_lane_mode():
    data = request.json or {}
    lane = data.get("lane")
    mode = data.get("mode")
    if lane not in STATE.bridge_lane_ids:
        return jsonify({"status": "error", "message": "Invalid bridge lane"}), 400
    if mode not in ("cars", "trucks", "both"):
        return jsonify({"status": "error", "message": "Invalid mode"}), 400
    STATE.bridge_lane_modes[lane] = mode
    return jsonify({"status": "success", "lane": lane, "mode": mode})

@bp_lanes.route("/clear_all_closures", methods=["POST"])
def clear_all_closures():
    for k in STATE.lane_closure_status:
        STATE.lane_closure_status[k] = False
        if k in STATE.original_flow_rates:
            STATE.flow_rates[k] = STATE.original_flow_rates[k]
    STATE.original_flow_rates.clear()
    return jsonify({"status": "success", "message": "All lanes opened"})
