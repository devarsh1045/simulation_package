# Toll booth closure handling logic
# This file implements the TWO-STOP toll booth system logic exactly as specified

import traci

# lane_closure_status is expected to be provided by the caller


def handle_toll_booth_closures(step_counter, lane_closure_status):
    """
    Handle dynamic toll booth closures with TWO-STOP system
    Each vehicle has:
      - Stop 1: Canada booth (0–5) on edge E7
      - Stop 2: US booth (6–19) on edge E0

    Logic matches the provided reference implementation
    without disturbing route definitions elsewhere.
    """
    try:
        # ====================================================================
        # Helper Functions
        # ====================================================================

        def get_booth_lane(booth_num):
            if booth_num <= 5:
                return 'E7', booth_num
            else:
                return 'E0', booth_num - 6

        def get_booth_from_stop_id(stop_id):
            if stop_id and stop_id.startswith('bs_'):
                try:
                    return int(stop_id.split('_')[1])
                except Exception:
                    return None
            return None

        def find_nearest_open_booth_in_section(current_booth, section_booths):
            if not section_booths:
                return None
            best_booth = None
            min_distance = float('inf')
            for booth in section_booths:
                distance = abs(booth - current_booth)
                if distance < min_distance:
                    min_distance = distance
                    best_booth = booth
            return best_booth

        # ====================================================================
        # Build Booth State
        # ====================================================================

        open_canada = [i for i in range(6)
                       if not lane_closure_status.get(f'booth_{i}', False)]
        open_us = [i for i in range(6, 20)
                   if not lane_closure_status.get(f'booth_{i}', False)]
        closed_booths = [i for i in range(20)
                         if lane_closure_status.get(f'booth_{i}', False)]

        # ====================================================================
        # Critical safety check
        # ====================================================================

        if not open_canada or not open_us:
            print('[CRITICAL] Missing open booths - removing all vehicles')
            for vid in list(traci.vehicle.getIDList()):
                try:
                    traci.vehicle.remove(vid)
                except Exception:
                    pass
            return

        # ====================================================================
        # Status logging
        # ====================================================================

        if step_counter % 100 == 0:
            print(f"\n[BOOTH STATUS] Step {step_counter}")
            print(f"  Open Canada (0-5): {open_canada}")
            print(f"  Open US (6-19): {open_us}")
            print(f"  Closed: {closed_booths}")

        # ====================================================================
        # Process vehicles
        # ====================================================================

        for vid in list(traci.vehicle.getIDList()):
            try:
                stops = traci.vehicle.getStops(vid)
                if not stops:
                    continue

                needs_reroute = False
                new_canada_booth = None
                new_us_booth = None
                canada_booth = None
                us_booth = None

                # Canada stop
                if len(stops) >= 1:
                    stop_id = getattr(stops[0], 'stoppingPlaceID', None)
                    canada_booth = get_booth_from_stop_id(stop_id)
                    if canada_booth in closed_booths:
                        new_canada_booth = find_nearest_open_booth_in_section(canada_booth, open_canada)
                        if new_canada_booth is not None:
                            needs_reroute = True
                        else:
                            traci.vehicle.remove(vid)
                            continue

                # US stop
                if len(stops) >= 2:
                    stop_id = getattr(stops[1], 'stoppingPlaceID', None)
                    us_booth = get_booth_from_stop_id(stop_id)
                    if us_booth in closed_booths:
                        new_us_booth = find_nearest_open_booth_in_section(us_booth, open_us)
                        if new_us_booth is not None:
                            needs_reroute = True
                        else:
                            traci.vehicle.remove(vid)
                            continue

                # Execute reroute
                if needs_reroute:
                    traci.vehicle.setStops(vid, [])

                    final_canada = new_canada_booth if new_canada_booth is not None else canada_booth
                    final_us = new_us_booth if new_us_booth is not None else us_booth

                    edge, lane = get_booth_lane(final_canada)
                    traci.vehicle.setStop(
                        vid, edge, pos=40.0, laneIndex=lane,
                        duration=2.0,
                        flags=traci.constants.STOP_BUS_STOP,
                        stopID=f'bs_{final_canada}'
                    )

                    edge, lane = get_booth_lane(final_us)
                    traci.vehicle.setStop(
                        vid, edge, pos=40.0, laneIndex=lane,
                        duration=2.0,
                        flags=traci.constants.STOP_BUS_STOP,
                        stopID=f'bs_{final_us}'
                    )

            except Exception as e:
                print(f"[ERROR] Vehicle {vid}: {e}")

        # ====================================================================
        # Remove stuck vehicles on closed lanes
        # ====================================================================

        for booth_num in closed_booths:
            edge, lane_idx = get_booth_lane(booth_num)
            lane_id = f"{edge}_{lane_idx}"
            try:
                for vid in traci.lane.getLastStepVehicleIDs(lane_id):
                    if traci.vehicle.getSpeed(vid) < 1.0:
                        traci.vehicle.remove(vid)
                        print(f"[REMOVE STUCK] {vid} on closed lane {lane_id}")
            except Exception:
                pass

    except Exception as e:
        print(f"[FATAL] Toll closure handler failed: {e}")
