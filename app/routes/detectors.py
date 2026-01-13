from flask import Blueprint, jsonify

from ..state import STATE

bp_detectors = Blueprint("detectors", __name__)

@bp_detectors.route("/detector_wait_time/stats", methods=["GET"])
def get_detector_wait_stats():
    if STATE.detector_wait_analyzer is None:
        return jsonify({"status": "error", "message": "Detector analyzer not initialized"}), 400
    return jsonify({"status": "success", "statistics": STATE.detector_wait_analyzer.get_statistics()})

@bp_detectors.route("/detector_wait_time/summary", methods=["GET"])
def get_detector_wait_summary():
    if STATE.detector_wait_analyzer is None:
        return jsonify({"status": "error", "message": "Detector analyzer not initialized"}), 400
    return jsonify({"status": "success", "summary": STATE.detector_wait_analyzer.get_summary()})
