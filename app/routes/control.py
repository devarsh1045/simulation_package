import os
import time
import subprocess
import threading
from flask import Blueprint, jsonify

from ..state import STATE
from ..services.simulation import run_simulation

bp_control = Blueprint("control", __name__)

@bp_control.route("/start", methods=["POST"])
def start_simulation():
    with STATE.lock:
        if STATE.simulation_running:
            return jsonify({"status": "already running"})

        # reset state and start
        STATE.reset_all()
        STATE.simulation_running = True

        STATE.simulation_thread = threading.Thread(target=run_simulation, args=(STATE,), daemon=True)
        STATE.simulation_thread.start()

    return jsonify({"status": "started"})

@bp_control.route("/stop", methods=["POST"])
def stop_simulation():
    with STATE.lock:
        STATE.simulation_running = False

    time.sleep(1)

    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/IM", "sumo-gui.exe"], capture_output=True)
            subprocess.run(["taskkill", "/F", "/IM", "sumo.exe"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "sumo-gui"], capture_output=True)
            subprocess.run(["pkill", "-f", "sumo"], capture_output=True)
    except:
        pass

    return jsonify({"status": "stopped"})

@bp_control.route("/status", methods=["GET"])
def status():
    detector_stats = None
    if STATE.detector_wait_analyzer is not None:
        try:
            detector_stats = STATE.detector_wait_analyzer.get_summary()
        except:
            detector_stats = None

    breakdown_stats = {}
    for lane_key, tracking in STATE.breakdown_tracking.items():
        if tracking.get("active"):
            breakdown_stats[lane_key] = {
                "vehicle_id": tracking.get("vehicle_id"),
                "affected_count": tracking.get("affected_count", 0),
            }

    return jsonify({
        "running": STATE.simulation_running,
        "data": STATE.simulation_data,
        "flow_rates": STATE.flow_rates,
        "breakdown_status": STATE.breakdown_status,
        "lane_closure_status": STATE.lane_closure_status,
        "mainlane_breakdown_status": STATE.mainlane_breakdown_status,
        "main_lane_modes": STATE.main_lane_modes,
        "bridge_breakdown_status": STATE.bridge_breakdown_status,
        "bridge_lane_modes": STATE.bridge_lane_modes,
        "detector_wait_stats": detector_stats,
        "breakdown_tracking": breakdown_stats,
    })
