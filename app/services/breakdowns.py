def get_vehicles_behind_position(traci, lane_id, position, radius):
    try:
        affected = []
        for vid in traci.lane.getLastStepVehicleIDs(lane_id):
            try:
                v_pos = traci.vehicle.getLanePosition(vid)
                if traci.vehicle.getLaneID(vid) == lane_id and v_pos < position:
                    if (position - v_pos) <= radius:
                        affected.append(vid)
            except:
                continue
        return affected
    except:
        return []

def set_adapted_travel_time_for_edge(traci, edge_id, inflation_factor=10.0):
    try:
        edge_length = traci.edge.getLength(edge_id)
        lanes = traci.edge.getLaneNumber(edge_id)
        if lanes <= 0:
            return False
        lane_id = f"{edge_id}_0"
        speed_limit = traci.lane.getMaxSpeed(lane_id)
        normal = edge_length / speed_limit
        inflated = normal * inflation_factor
        for vid in traci.vehicle.getIDList():
            try:
                traci.vehicle.setAdaptedTraveltime(vid, edge_id, inflated)
            except:
                pass
        return True
    except:
        return False

def reset_adapted_travel_time_for_edge(traci, edge_id):
    try:
        for vid in traci.vehicle.getIDList():
            try:
                traci.vehicle.setAdaptedTraveltime(vid, edge_id, -1)
            except:
                pass
        return True
    except:
        return False

def force_vehicle_reroute(traci, vid):
    try:
        traci.vehicle.rerouteTraveltime(vid)
        return True
    except:
        return False

def create_permanent_breakdown(traci, vid, lane_id):
    try:
        position = traci.vehicle.getLanePosition(vid)
        edge_id = traci.vehicle.getRoadID(vid)
        traci.vehicle.setStop(
            vehID=vid, edgeID=edge_id, pos=position,
            laneIndex=traci.vehicle.getLaneIndex(vid),
            duration=99999, flags=0
        )
        traci.vehicle.setColor(vid, (255, 0, 0, 255))
        return True
    except:
        return False

def clear_breakdown(traci, vid):
    try:
        traci.vehicle.setStop(vehID=vid, edgeID="", pos=0, laneIndex=0, duration=0, flags=64)
        traci.vehicle.setColor(vid, (255, 255, 0, 255))
        traci.vehicle.setSpeed(vid, -1)
        return True
    except:
        return False
