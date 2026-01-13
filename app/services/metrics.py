def update_dashboard_metrics(state, traci, booth_vehicles):
    sim_time = traci.simulation.getTime()
    state.simulation_data["time"] = round(sim_time, 1)

    # Toll booth metrics
    for booth_id in booth_vehicles:
        if booth_id in traci.lanearea.getIDList():
            ids = traci.lanearea.getLastStepVehicleIDs(booth_id)
            booth_vehicles[booth_id].update(ids)

            queue = traci.lanearea.getLastStepHaltingNumber(booth_id)
            occ = traci.lanearea.getLastStepOccupancy(booth_id)

            num = booth_id.split("_")[-1]
            key = f"booth_{num}"

            state.simulation_data["revenue"][key] = len(booth_vehicles[booth_id]) * 20
            state.simulation_data["vehicle_counts"][key] = len(booth_vehicles[booth_id])
            state.simulation_data["queue_lengths"][key] = queue
            state.simulation_data["occupancy"][key] = round(occ * 100, 1)
            state.simulation_data["broken_vehicles"][key] = key in state.broken_vehicle_ids

    state.simulation_data["total_revenue"] = sum(len(v) * 20 for v in booth_vehicles.values())
    state.simulation_data["total_queue"] = sum(state.simulation_data["queue_lengths"].get(f"booth_{i}", 0) for i in range(20))

    # MAIN lane metrics
    for lane_key in state.main_lane_ids:
        det_id = lane_key
        if det_id in traci.lanearea.getIDList():
            q = traci.lanearea.getLastStepHaltingNumber(det_id)
            occ = traci.lanearea.getLastStepOccupancy(det_id)
            state.simulation_data["mainlane_queue"][lane_key] = q
            state.simulation_data["mainlane_occupancy"][lane_key] = round(occ * 100.0, 1)
        else:
            state.simulation_data["mainlane_queue"][lane_key] = 0
            state.simulation_data["mainlane_occupancy"][lane_key] = 0.0
        state.simulation_data["mainlane_breakdown"][lane_key] = bool(state.mainlane_breakdown_status.get(lane_key, False))

    # BRIDGE lane metrics
    for lane_key in state.bridge_lane_ids:
        det_id = lane_key
        if det_id in traci.lanearea.getIDList():
            q = traci.lanearea.getLastStepHaltingNumber(det_id)
            occ = traci.lanearea.getLastStepOccupancy(det_id)
            state.simulation_data["bridgelane_queue"][lane_key] = q
            state.simulation_data["bridgelane_occupancy"][lane_key] = round(occ * 100.0, 1)
        else:
            state.simulation_data["bridgelane_queue"][lane_key] = 0
            state.simulation_data["bridgelane_occupancy"][lane_key] = 0.0
        state.simulation_data["bridgelane_breakdown"][lane_key] = bool(state.bridge_breakdown_status.get(lane_key, False))
