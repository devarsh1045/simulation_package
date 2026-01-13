import os
import sys
import subprocess
import sumolib
from ..config import Config
from ..utils.sumo import sumo_binary, project_path
from .route_builder import update_route_file
from .detector_analyzer import DetectorWaitTimeAnalyzer
from .toll_closures import handle_toll_booth_closures
from .lane_controls import apply_lane_modes_and_closures
from .breakdowns import (
    create_permanent_breakdown, clear_breakdown,
    set_adapted_travel_time_for_edge, reset_adapted_travel_time_for_edge,
    force_vehicle_reroute, get_vehicles_behind_position
)
from .metrics import update_dashboard_metrics

def _ensure_sumo_tools():
    if "SUMO_HOME" not in os.environ:
        raise RuntimeError("Please declare environment variable 'SUMO_HOME'")
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    if tools not in sys.path:
        sys.path.append(tools)

def _booth_lane_id(booth_num: int) -> str:
    # Booths 0-5 -> E7_0..E7_5
    if booth_num <= 5:
        return f"E7_{booth_num}"
    # Booths 6-19 -> E0_0..E0_13
    return f"E0_{booth_num - 6}"

def run_simulation(state):
    """
    Background simulation thread.
    """
    _ensure_sumo_tools()
    import traci  
    # must be after SUMO tools path

    # update routes at start
    update_route_file(state)

    # init detector analyzer
    state.detector_wait_analyzer = DetectorWaitTimeAnalyzer(traci)
    state.lane_closure_status = {
    f"booth_{i}": False for i in range(20)
    }


    gui = Config.SIM_GUI
    sumo_cmd = sumo_binary(gui=gui)
    sumo_config = [
        sumo_cmd,
        "-c", project_path("bwb.sumocfg"),
        "--step-length", str(Config.SIM_STEP),
        "--lateral-resolution", str(Config.SIM_LAT_RES),
    ]

    # Track unique vehicles per booth via lanearea detectors e2_booth_0..19
    booth_vehicles = {f"e2_booth_{i}": set() for i in range(Config.LANE_CONFIG["booth"])}

    step_counter = 0

    try:
        traci.start(sumo_config)
        print("[SIM] SUMO started.")
        print("E7 lanes:", [l for l in traci.lane.getIDList() if l.startswith("E7_")])
        print("E0 lanes:", [l for l in traci.lane.getIDList() if l.startswith("E0_")])
        print("All lanes:", traci.lane.getIDList())
        net = sumolib.net.readNet(project_path("bwb_fixed.net.xml"))
        for a, b in [("E3", "E7"), ("E7", "E0"), ("E3", "E0")]:
            try:
                path, cost = net.getShortestPath(net.getEdge(a), net.getEdge(b))
                print(a, "->", b, ":", [e.getID() for e in path])
            except Exception as e:
                print("No path", a, "->", b, e)

        while state.simulation_running and traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            step_counter += 1

            # closures reroute
            handle_toll_booth_closures(step_counter, state.lane_closure_status) 

            # detector updates
            sim_time = traci.simulation.getTime()
            state.detector_wait_analyzer.check_detectors(sim_time)

            # lane modes + closures
            apply_lane_modes_and_closures(state, traci)

            # booth breakdowns
            for booth_num in range(20):
                booth_key = f"booth_{booth_num}"
                lane_id = _booth_lane_id(booth_num)

                # skip if lane closed
                if state.lane_closure_status.get(booth_key, False):
                    state.broken_vehicle_ids.pop(booth_key, None)
                    continue

                if state.breakdown_status.get(booth_key, False):
                    if booth_key not in state.broken_vehicle_ids:
                        try:
                            vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
                            if vehicles:
                                v = vehicles[0]
                                traci.vehicle.setColor(v, (255, 0, 0, 255))
                                traci.vehicle.setSpeed(v, 0)
                                state.broken_vehicle_ids[booth_key] = v
                        except:
                            pass
                    else:
                        v = state.broken_vehicle_ids[booth_key]
                        if v in traci.vehicle.getIDList():
                            try:
                                traci.vehicle.setSpeed(v, 0)
                            except:
                                pass
                else:
                    if booth_key in state.broken_vehicle_ids:
                        v = state.broken_vehicle_ids[booth_key]
                        try:
                            if v in traci.vehicle.getIDList():
                                traci.vehicle.setColor(v, (255, 255, 0, 255))
                                traci.vehicle.setSpeed(v, -1)
                        except:
                            pass
                        del state.broken_vehicle_ids[booth_key]

            # main/bridge breakdown rerouting
            for lane_key, lane_id in {**state.main_lane_ids, **state.bridge_lane_ids}.items():
                is_main = lane_key.startswith("main_")
                active_flag = state.mainlane_breakdown_status if is_main else state.bridge_breakdown_status

                if active_flag.get(lane_key, False):
                    if not state.breakdown_tracking[lane_key]["active"]:
                        try:
                            vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
                            if vehicles:
                                v_id = vehicles[0]
                                if create_permanent_breakdown(traci, v_id, lane_id):
                                    state.breakdown_tracking[lane_key]["active"] = True
                                    state.breakdown_tracking[lane_key]["vehicle_id"] = v_id
                                    state.breakdown_tracking[lane_key]["position"] = traci.vehicle.getLanePosition(v_id)
                                    state.breakdown_tracking[lane_key]["lane_id"] = lane_id
                                    state.breakdown_tracking[lane_key]["edge_id"] = traci.vehicle.getRoadID(v_id)
                                    state.breakdown_tracking[lane_key]["affected_count"] = 0
                                    set_adapted_travel_time_for_edge(traci, state.breakdown_tracking[lane_key]["edge_id"], Config.TRAVEL_TIME_INFLATION)
                        except:
                            pass
                    else:
                        v_id = state.breakdown_tracking[lane_key]["vehicle_id"]
                        if v_id not in traci.vehicle.getIDList():
                            state.breakdown_tracking[lane_key]["active"] = False
                            active_flag[lane_key] = False
                            continue
                        try:
                            pos = state.breakdown_tracking[lane_key]["position"]
                            affected = get_vehicles_behind_position(traci, lane_id, pos, Config.DETECTION_RADIUS)
                            state.breakdown_tracking[lane_key]["affected_count"] = len(affected)
                            for av in affected:
                                if av != v_id:
                                    force_vehicle_reroute(traci, av)
                        except:
                            pass
                else:
                    if state.breakdown_tracking[lane_key]["active"]:
                        v_id = state.breakdown_tracking[lane_key]["vehicle_id"]
                        edge_id = state.breakdown_tracking[lane_key]["edge_id"]
                        try:
                            if v_id and v_id in traci.vehicle.getIDList():
                                clear_breakdown(traci, v_id)
                        except:
                            pass
                        try:
                            if edge_id:
                                reset_adapted_travel_time_for_edge(traci, edge_id)
                        except:
                            pass
                        state.breakdown_tracking[lane_key]["active"] = False
                        state.breakdown_tracking[lane_key]["vehicle_id"] = None
                        state.breakdown_tracking[lane_key]["affected_count"] = 0

            # refresh adapted travel times periodically
            state.breakdown_refresh_counter += 1
            if state.breakdown_refresh_counter >= Config.REFRESH_TRAVELTIME_EVERY_STEPS:
                state.breakdown_refresh_counter = 0
                for lane_key, tracking in state.breakdown_tracking.items():
                    if tracking["active"] and tracking["edge_id"]:
                        set_adapted_travel_time_for_edge(traci, tracking["edge_id"], Config.TRAVEL_TIME_INFLATION)

            # update metrics periodically
            if step_counter % Config.METRICS_EVERY_STEPS == 0:
                try:
                    state.detector_wait_analyzer.calculate_statistics()
                except:
                    pass
                update_dashboard_metrics(state, traci, booth_vehicles)

    except Exception as e:
        print("[SIM] Simulation error:", e)
    finally:
        state.simulation_running = False
        try:
            traci.close()
        except:
            pass
        print("[SIM] Simulation stopped cleanly.")
