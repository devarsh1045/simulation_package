def apply_lane_modes_and_closures(state, traci):
    # MAIN lanes
    for lane_key, lane_id in state.main_lane_ids.items():
        if state.lane_closure_status.get(lane_key, False):
            try:
                for v in traci.lane.getLastStepVehicleIDs(lane_id):
                    traci.vehicle.remove(v)
            except:
                pass
            try:
                traci.lane.setAllowed(lane_id, [])
            except:
                pass
            continue

        mode = state.main_lane_modes.get(lane_key, "both")
        try:
            if mode == "cars":
                traci.lane.setAllowed(lane_id, ["passenger"])
            elif mode == "trucks":
                traci.lane.setAllowed(lane_id, ["truck"])
            else:
                traci.lane.setAllowed(lane_id, ["passenger", "truck"])
        except:
            pass

    # BRIDGE lanes
    for lane_key, lane_id in state.bridge_lane_ids.items():
        if state.lane_closure_status.get(lane_key, False):
            try:
                for v in traci.lane.getLastStepVehicleIDs(lane_id):
                    traci.vehicle.remove(v)
            except:
                pass
            try:
                traci.lane.setAllowed(lane_id, [])
            except:
                pass
            continue

        mode = state.bridge_lane_modes.get(lane_key, "both")
        try:
            if mode == "cars":
                traci.lane.setAllowed(lane_id, ["passenger"])
            elif mode == "trucks":
                traci.lane.setAllowed(lane_id, ["truck"])
            else:
                traci.lane.setAllowed(lane_id, ["passenger", "truck"])
        except:
            pass
