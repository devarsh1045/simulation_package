from flask import Flask, render_template, jsonify, request
import subprocess
import threading
import time
import os
import sys
import random
import signal
import xml.etree.ElementTree as ET
import sumolib

# Add SUMO tools to path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

import traci

app = Flask(__name__)

# Global variables
simulation_thread = None
simulation_running = False
detector_wait_analyzer = None
# MAIN LANES on edge E3 (upstream of tolls)
simulation_data = {
    'revenue': {},
    'total_revenue': 0,
    'vehicle_counts': {},
    'queue_lengths': {},
    'occupancy': {},
    'broken_vehicles': {},
    'time': 0.0,

    # MAIN LANE metrics (for E3_0–E3_3 with detectors main_0..main_3)
    'mainlane_queue': {
        'main_0': 0,
        'main_1': 0,
        'main_2': 0,
        'main_3': 0
    },
    'mainlane_occupancy': {
        'main_0': 0.0,
        'main_1': 0.0,
        'main_2': 0.0,
        'main_3': 0.0
    },
    'mainlane_breakdown': {
        'main_0': False,
        'main_1': False,
        'main_2': False,
        'main_3': False
    },
    
    # BRIDGE LANE metrics (for E8_0-E8_2 ONLY - 3 LANES)
    'bridgelane_queue': {
        'bridge_0': 0,
        'bridge_1': 0,
        'bridge_2': 0
    },
    'bridgelane_occupancy': {
        'bridge_0': 0.0,
        'bridge_1': 0.0,
        'bridge_2': 0.0
    },
    'bridgelane_breakdown': {
        'bridge_0': False,
        'bridge_1': False,
        'bridge_2': False
    }
}

# Track broken down vehicles at toll booths (EXTENDED TO 20 BOOTHS)
breakdown_status = {
    'booth_0': False,
    'booth_1': False,
    'booth_2': False,
    'booth_3': False,
    'booth_4': False,
    'booth_5': False,
    'booth_6': False,
    'booth_7': False,
    'booth_8': False,
    'booth_9': False,
    'booth_10': False,
    'booth_11': False,
    'booth_12': False,
    'booth_13': False,
    'booth_14': False,
    'booth_15': False,
    'booth_16': False,
    'booth_17': False,
    'booth_18': False,
    'booth_19': False,
}
broken_vehicle_ids = {}

# Track lane closures  (booths + main lanes + bridge lanes) - 20 BOOTHS + 4 MAIN + 3 BRIDGE
lane_closure_status = {
    'booth_0': False,
    'booth_1': False,
    'booth_2': False,
    'booth_3': False,
    'booth_4': False,
    'booth_5': False,
    'booth_6': False,
    'booth_7': False,
    'booth_8': False,
    'booth_9': False,
    'booth_10': False,
    'booth_11': False,
    'booth_12': False,
    'booth_13': False,
    'booth_14': False,
    'booth_15': False,
    'booth_16': False,
    'booth_17': False,
    'booth_18': False,
    'booth_19': False,
    'main_0': False,
    'main_1': False,
    'main_2': False,
    'main_3': False,
    'bridge_0': False,
    'bridge_1': False,
    'bridge_2': False,
}
original_flow_rates = {}

# Flow rates (vehicles per hour) – EXTENDED TO 20 BOOTHS
flow_rates = {
    'booth_0': 50,
    'booth_1': 50,
    'booth_2': 50,
    'booth_3': 50,
    'booth_4': 50,
    'booth_5': 50,
    'booth_6': 50,
    'booth_7': 50,
    'booth_8': 50,
    'booth_9': 50,
    'booth_10': 50,
    'booth_11': 50,
    'booth_12': 50,
    'booth_13': 50,
    'booth_14': 50,
    'booth_15': 50,
    'booth_16': 50,
    'booth_17': 50,
    'booth_18': 50,
    'booth_19': 50,
}

main_lane_ids = {
    'main_0': 'E3_0',
    'main_1': 'E3_1',
    'main_2': 'E3_2',
    'main_3': 'E3_3',
}

# Bridge and additional lane IDs (ONLY E8 LANES - 3 BRIDGE LANES)
bridge_lane_ids = {
    'bridge_0': 'E8_0',
    'bridge_1': 'E8_1',
    'bridge_2': 'E8_2',
}

# Main lane breakdown flags
mainlane_breakdown_status = {
    'main_0': False,
    'main_1': False,
    'main_2': False,
    'main_3': False,
}
main_lane_broken_vehicle = {}

# Bridge lane breakdown flags (3 LANES ONLY)
bridge_breakdown_status = {
    'bridge_0': False,
    'bridge_1': False,
    'bridge_2': False,
}
bridge_lane_broken_vehicle = {}

# NEW: per-main-lane mode → 'cars', 'trucks', or 'both'
main_lane_modes = {
    'main_0': 'both',
    'main_1': 'both',
    'main_2': 'both',
    'main_3': 'both',
}

# Bridge lane modes (3 LANES ONLY)
bridge_lane_modes = {
    'bridge_0': 'both',
    'bridge_1': 'both',
    'bridge_2': 'both',
}

def update_route_file():
    """
    Generate routes with CUSTOM booth pairings
    Define exactly which Canada booth pairs with which US booth
    """
    
    # Vehicle type mapping
    vehicle_types = {
        'booth_0': 'car', 'booth_1': 'car', 'booth_2': 'car', 
        'booth_3': 'car', 'booth_4': 'truck', 'booth_5': 'truck',
        'booth_6': 'car', 'booth_7': 'car', 'booth_8': 'car', 
        'booth_9': 'car', 'booth_10': 'car', 'booth_11': 'car', 
        'booth_12': 'car', 'booth_13': 'car', 'booth_14': 'truck',
        'booth_15': 'truck', 'booth_16': 'truck', 'booth_17': 'truck',
        'booth_18': 'truck', 'booth_19': 'truck',
    }
    
    # ========================================================================
    # CUSTOM BOOTH PAIRING MAP
    # Define exactly which Canada → US booth combination for each flow
    # ========================================================================
    
    booth_pairing = {
        # Format: flow_booth_id: (canada_booth, us_booth)
        
        # Primary Canada flows (0-5)
        0: (0, 6),   
        1: (1, 7),   
        2: (2, 10),   
        3: (3, 11),   # f_booth_3: Canada bs_3 → US bs_9
        4: (4, 14),  # f_booth_4: Canada bs_4 → US bs_10
        5: (5, 17),  # f_booth_5: Canada bs_5 → US bs_11
        
        # Additional flows (6-19) - customize as needed
        6: (0, 6),   # f_booth_6: Canada bs_0 → US bs_12
        7: (0, 7),   # f_booth_7: Canada bs_1 → US bs_13
        8: (1, 8),   # f_booth_8: Canada bs_2 → US bs_14
        9: (1, 9),   # f_booth_9: Canada bs_3 → US bs_15
        10: (2, 10),  # f_booth_10: Canada bs_4 → US bs_16
        11: (2, 11),  # f_booth_11: Canada bs_5 → US bs_17
        12: (3, 12),  # f_booth_12: Canada bs_0 → US bs_18
        13: (3, 13),  # f_booth_13: Canada bs_1 → US bs_19
        14: (4, 14),   # f_booth_14: Canada bs_2 → US bs_6
        15: (4, 15),   # f_booth_15: Canada bs_3 → US bs_7
        16: (4, 16),   # f_booth_16: Canada bs_4 → US bs_8
        17: (5, 17),   # f_booth_17: Canada bs_5 → US bs_9
        18: (5, 18),  # f_booth_18: Canada bs_0 → US bs_10
        19: (5, 19),  # f_booth_19: Canada bs_1 → US bs_11
    }
    
    # ========================================================================
    # Calculate redistributed flows
    # ========================================================================
    
    redistributed_flows = {}
    
    for i in range(20):
        booth_key = f'booth_{i}'
        
        if not lane_closure_status.get(booth_key, False):
            redistributed_flows[booth_key] = flow_rates.get(booth_key, 100)
        else:
            redistributed_flows[booth_key] = 0
            closed_flow = flow_rates.get(booth_key, 100)
            adjacent_booths = find_adjacent_open_booths(i)
            
            if adjacent_booths:
                flow_per_adjacent = closed_flow // len(adjacent_booths)
                for adj_booth in adjacent_booths:
                    adj_key = f'booth_{adj_booth}'
                    redistributed_flows[adj_key] = redistributed_flows.get(adj_key, 100) + flow_per_adjacent
                print(f"[REDISTRIBUTE] booth_{i} closed: {closed_flow} veh/hr → {adjacent_booths}")
    
    # ========================================================================
    # Get open booths
    # ========================================================================
    
    open_canada_booths = [i for i in range(6) if not lane_closure_status.get(f'booth_{i}', False)]
    open_us_booths = [i for i in range(6, 20) if not lane_closure_status.get(f'booth_{i}', False)]
    
    if not open_canada_booths or not open_us_booths:
        print("[ERROR] Need at least one open booth in each section!")
        return ""
    
    # ========================================================================
    # Generate flows
    # ========================================================================
    
    flow_entries = []
    
    for i in range(20):
        booth_key = f'booth_{i}'
        flow_rate = redistributed_flows.get(booth_key, 0)
        
        if flow_rate == 0:
            continue
        
        # Get assigned booth pair
        canada_booth, us_booth = booth_pairing[i]
        
        # Adjust if assigned booths are closed
        if canada_booth not in open_canada_booths:
            canada_booth = min(open_canada_booths, key=lambda b: abs(b - canada_booth))
        
        if us_booth not in open_us_booths:
            us_booth = min(open_us_booths, key=lambda b: abs(b - us_booth))
        
        vtype = vehicle_types[booth_key]
        
        flow_entry = f'''    <flow id="f_booth_{i}" type="{vtype}" begin="0.1" departLane="best" departPos="0.00" from="E3" to="E0" end="3600.00" vehsPerHour="{flow_rate}">
        <stop busStop="bs_{canada_booth}" duration="2.00"/>
        <stop busStop="bs_{us_booth}" duration="2.00"/>
    </flow>
'''
        flow_entries.append(flow_entry)
        print(f"[FLOW] f_booth_{i}: Canada bs_{canada_booth} → US bs_{us_booth} ({flow_rate} veh/hr)")
    
    # ========================================================================
    # Generate XML
    # ========================================================================
    
    routes_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    <vType id="car" minGap="0.10" vClass="passenger" color="0,255,0" jmCrossingGap="0.10" jmIgnoreKeepClearTime="1.00" carFollowModel="IDM">
        <param key="has.rerouting.device" value="true"/>
        <param key="device.rerouting.period" value="10"/>
    </vType>
    <vType id="truck" minGap="0.15" vClass="truck" color="0,0,255" jmCrossingGap="0.30" jmIgnoreKeepClearTime="1.00" carFollowModel="IDM">
        <param key="has.rerouting.device" value="true"/>
        <param key="device.rerouting.period" value="10"/>
    </vType>
    
{''.join(flow_entries)}
</routes>
'''
    
    with open('bwb.rou.xml', 'w') as f:
        f.write(routes_xml)
    
    print(f"[ROUTES] Generated {len(flow_entries)} flows with custom booth pairings")
    
    return routes_xml

def find_adjacent_open_booths(booth_num):
    """Find adjacent open booths in the same section"""
    
    # Determine section
    if booth_num <= 5:
        # Canada section (booths 0-5)
        section_booths = list(range(6))
    else:
        # CBP section (booths 6-19)
        section_booths = list(range(6, 20))
    
    # Find adjacent booths (prefer immediate neighbors)
    adjacent = []
    
    # Check immediate neighbors first
    for offset in [1, -1, 2, -2, 3, -3]:
        neighbor = booth_num + offset
        if neighbor in section_booths:
            booth_key = f'booth_{neighbor}'
            if not lane_closure_status.get(booth_key, False):
                adjacent.append(neighbor)
                if len(adjacent) >= 2:  # Limit to 2 adjacent booths
                    break
    
    # If no immediate neighbors, use any open booth in section
    if not adjacent:
        for b in section_booths:
            booth_key = f'booth_{b}'
            if not lane_closure_status.get(booth_key, False) and b != booth_num:
                adjacent.append(b)
    
    return adjacent

def handle_toll_booth_closures(step_counter):
    """
    Handle dynamic toll booth closures with TWO-STOP system
    Each vehicle has: Stop 1 (Canada booth 0-5) + Stop 2 (US booth 6-19)
    """
    try:
        # ====================================================================
        # Helper Functions
        # ====================================================================
        
        def get_booth_lane(booth_num):
            """Get edge and lane for a booth number"""
            if booth_num <= 5:
                # Canada booths on E7
                return ('E7', booth_num)
            else:
                # US booths on E0
                return ('E0', booth_num - 6)
        
        def get_booth_from_stop_id(stop_id):
            """Extract booth number from bus stop ID"""
            if stop_id and stop_id.startswith('bs_'):
                try:
                    return int(stop_id.split('_')[1])
                except:
                    return None
            return None
        
        def find_nearest_open_booth_in_section(current_booth, section_booths):
            """Find nearest open booth within a specific section"""
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
        # Build Lists of Open/Closed Booths
        # ====================================================================
        
        open_canada = [i for i in range(6) if not lane_closure_status.get(f'booth_{i}', False)]
        open_us = [i for i in range(6, 20) if not lane_closure_status.get(f'booth_{i}', False)]
        closed_booths = [i for i in range(20) if lane_closure_status.get(f'booth_{i}', False)]
        
        # ====================================================================
        # Critical Check: Need at least one open booth in each section
        # ====================================================================
        
        if not open_canada or not open_us:
            print("[CRITICAL] Missing open booths - removing all vehicles")
            all_vehicles = traci.vehicle.getIDList()
            for vid in list(all_vehicles):
                try:
                    if vid in traci.vehicle.getIDList():
                        traci.vehicle.remove(vid)
                except:
                    pass
            return
        
        # ====================================================================
        # Periodic Status Logging
        # ====================================================================
        
        if step_counter % 100 == 0:
            print(f"\n[BOOTH STATUS] Step {step_counter}")
            print(f"  Open Canada (0-5): {open_canada}")
            print(f"  Open US (6-19): {open_us}")
            print(f"  Closed: {closed_booths}")
        
        # ====================================================================
        # Process All Vehicles
        # ====================================================================
        
        all_vehicles = traci.vehicle.getIDList()
        
        rerouted_canada = 0
        rerouted_us = 0
        removed_count = 0
        
        for vid in list(all_vehicles):
            try:
                # Check vehicle still exists
                if vid not in traci.vehicle.getIDList():
                    continue
                
                # Get vehicle's stops
                stops = traci.vehicle.getStops(vid)
                
                if not stops:
                    continue
                
                # ============================================================
                # TWO-STOP SYSTEM: Check both stops
                # ============================================================
                
                needs_reroute = False
                new_canada_booth = None
                new_us_booth = None
                
                # ------ CHECK STOP 0 (Canada Booth) ------
                if len(stops) >= 1:
                    stop_0 = stops[0]
                    stop_0_id = stop_0.stoppingPlaceID if hasattr(stop_0, 'stoppingPlaceID') else None
                    canada_booth = get_booth_from_stop_id(stop_0_id)
                    
                    if canada_booth is not None and canada_booth in closed_booths:
                        # Canada booth is closed, find alternative
                        new_canada_booth = find_nearest_open_booth_in_section(canada_booth, open_canada)
                        
                        if new_canada_booth is not None:
                            needs_reroute = True
                            print(f"[PLAN REROUTE CANADA] {vid}: booth_{canada_booth} → booth_{new_canada_booth}")
                        else:
                            # No alternative Canada booth
                            print(f"[REMOVE] {vid} - no alternative Canada booth for booth_{canada_booth}")
                            if vid in traci.vehicle.getIDList():
                                traci.vehicle.remove(vid)
                                removed_count += 1
                            continue
                
                # ------ CHECK STOP 1 (US Booth) ------
                if len(stops) >= 2:
                    stop_1 = stops[1]
                    stop_1_id = stop_1.stoppingPlaceID if hasattr(stop_1, 'stoppingPlaceID') else None
                    us_booth = get_booth_from_stop_id(stop_1_id)
                    
                    if us_booth is not None and us_booth in closed_booths:
                        # US booth is closed, find alternative
                        new_us_booth = find_nearest_open_booth_in_section(us_booth, open_us)
                        
                        if new_us_booth is not None:
                            needs_reroute = True
                            print(f"[PLAN REROUTE US] {vid}: booth_{us_booth} → booth_{new_us_booth}")
                        else:
                            # No alternative US booth
                            print(f"[REMOVE] {vid} - no alternative US booth for booth_{us_booth}")
                            if vid in traci.vehicle.getIDList():
                                traci.vehicle.remove(vid)
                                removed_count += 1
                            continue
                
                # ============================================================
                # Execute Rerouting if Needed
                # ============================================================
                
                if needs_reroute:
                    try:
                        # Clear all existing stops
                        traci.vehicle.setStops(vid, [])
                        
                        # Add new Canada stop (use existing if not changed)
                        final_canada = new_canada_booth if new_canada_booth is not None else canada_booth
                        canada_edge, canada_lane = get_booth_lane(final_canada)
                        
                        traci.vehicle.setStop(
                            vid,
                            edgeID=canada_edge,
                            pos=40.0,
                            laneIndex=canada_lane,
                            duration=2.0,
                            flags=traci.constants.STOP_BUS_STOP,
                            startPos=0.0,
                            until=-1,
                            stopID=f"bs_{final_canada}"
                        )
                        
                        if new_canada_booth is not None:
                            rerouted_canada += 1
                        
                        # Add new US stop (use existing if not changed)
                        final_us = new_us_booth if new_us_booth is not None else us_booth
                        us_edge, us_lane = get_booth_lane(final_us)
                        
                        traci.vehicle.setStop(
                            vid,
                            edgeID=us_edge,
                            pos=40.0,
                            laneIndex=us_lane,
                            duration=2.0,
                            flags=traci.constants.STOP_BUS_STOP,
                            startPos=0.0,
                            until=-1,
                            stopID=f"bs_{final_us}"
                        )
                        
                        if new_us_booth is not None:
                            rerouted_us += 1
                        
                        print(f"[REROUTE SUCCESS] {vid}: Canada→{final_canada}, US→{final_us}")
                        
                    except Exception as e:
                        # Rerouting failed, remove vehicle
                        print(f"[REROUTE FAILED] {vid}: {type(e).__name__}: {e}")
                        try:
                            if vid in traci.vehicle.getIDList():
                                traci.vehicle.remove(vid)
                                removed_count += 1
                        except:
                            pass
            
            except Exception as e:
                # Handle individual vehicle errors
                print(f"[ERROR] Processing {vid}: {e}")
        
        # ====================================================================
        # Remove Stuck Vehicles on Closed Lanes
        # ====================================================================
        
        for booth_num in closed_booths:
            edge, lane_idx = get_booth_lane(booth_num)
            lane_id = f"{edge}_{lane_idx}"
            
            try:
                vehicles_on_lane = traci.lane.getLastStepVehicleIDs(lane_id)
                
                for vid in vehicles_on_lane:
                    try:
                        if vid in traci.vehicle.getIDList():
                            speed = traci.vehicle.getSpeed(vid)
                            if speed < 1.0:  # Vehicle is stuck/slow
                                traci.vehicle.remove(vid)
                                removed_count += 1
                                print(f"[REMOVE STUCK] {vid} on closed lane {lane_id}")
                    except:
                        pass
            except:
                pass
        
        # ====================================================================
        # Summary Logging
        # ====================================================================
        
        if step_counter % 100 == 0 and (rerouted_canada > 0 or rerouted_us > 0 or removed_count > 0):
            print(f"\n[CLOSURE SUMMARY] Step {step_counter}")
            print(f"  Canada reroutes: {rerouted_canada}")
            print(f"  US reroutes: {rerouted_us}")
            print(f"  Vehicles removed: {removed_count}")
        
    except Exception as e:
        print(f"[TOLL CLOSURE] Critical Error: {e}")
        import traceback
        traceback.print_exc()

class DetectorWaitTimeAnalyzer:
    """
    Wait time analysis using detector-based measurement
    Tracks vehicles crossing entry/exit detectors for Canada and US zones
    """
    
    def __init__(self):
        # Vehicle tracking dictionaries
        self.canada_tracking = {}  # {vehicle_id: entry_time}
        self.us_tracking = {}      # {vehicle_id: entry_time}
        
        # Completed vehicle data
        self.canada_completed = []  # List of travel times
        self.us_completed = []      # List of travel times
        
        # Statistics
        self.stats = {
            'canada': {
                'avg_wait_time': 0,
                'min_wait_time': 0,
                'max_wait_time': 0,
                'median_wait_time': 0,
                'vehicles_completed': 0,
                'vehicles_in_zone': 0
            },
            'us': {
                'avg_wait_time': 0,
                'min_wait_time': 0,
                'max_wait_time': 0,
                'median_wait_time': 0,
                'vehicles_completed': 0,
                'vehicles_in_zone': 0
            }
        }
        
        # Detector IDs
        self.canada_entry_detectors = [f'entry_canada_{i}' for i in range(6)]
        self.canada_exit_detectors = [f'exit_canada_{i}' for i in range(6)]
        self.us_entry_detectors = [f'entry_us_{i}' for i in range(14)]
        self.us_exit_detectors = [f'exit_us_{i}' for i in range(14)]
    
    def check_detectors(self, sim_time):
        """
        Check all detectors and update vehicle tracking
        Call this every simulation step
        """
        try:
            # ===== CANADA ZONE TRACKING =====
            
            # Check Canada entry detectors (E4)
            for detector_id in self.canada_entry_detectors:
                try:
                    vehicles = traci.inductionloop.getLastStepVehicleIDs(detector_id)
                    for vid in vehicles:
                        if vid not in self.canada_tracking:
                            # Vehicle just entered Canada zone
                            self.canada_tracking[vid] = sim_time
                except:
                    pass
            
            # Check Canada exit detectors (E7)
            for detector_id in self.canada_exit_detectors:
                try:
                    vehicles = traci.inductionloop.getLastStepVehicleIDs(detector_id)
                    for vid in vehicles:
                        if vid in self.canada_tracking:
                            # Vehicle just exited Canada zone
                            entry_time = self.canada_tracking[vid]
                            wait_time = sim_time - entry_time
                            self.canada_completed.append(wait_time)
                            del self.canada_tracking[vid]
                except:
                    pass
            
            # ===== US ZONE TRACKING =====
            
            # Check US entry detectors (E0 at 7m)
            for detector_id in self.us_entry_detectors:
                try:
                    vehicles = traci.inductionloop.getLastStepVehicleIDs(detector_id)
                    for vid in vehicles:
                        if vid not in self.us_tracking:
                            # Vehicle just entered US zone
                            self.us_tracking[vid] = sim_time
                except:
                    pass
            
            # Check US exit detectors (E0 at 48m)
            for detector_id in self.us_exit_detectors:
                try:
                    vehicles = traci.inductionloop.getLastStepVehicleIDs(detector_id)
                    for vid in vehicles:
                        if vid in self.us_tracking:
                            # Vehicle just exited US zone
                            entry_time = self.us_tracking[vid]
                            wait_time = sim_time - entry_time
                            self.us_completed.append(wait_time)
                            del self.us_tracking[vid]
                except:
                    pass
        
        except Exception as e:
            print(f"[DETECTOR ANALYZER] Error checking detectors: {e}")
    
    def calculate_statistics(self):
        """Calculate current statistics for both zones"""
        try:
            # ===== CANADA STATISTICS =====
            if self.canada_completed:
                self.stats['canada']['avg_wait_time'] = sum(self.canada_completed) / len(self.canada_completed)
                self.stats['canada']['min_wait_time'] = min(self.canada_completed)
                self.stats['canada']['max_wait_time'] = max(self.canada_completed)
                sorted_canada = sorted(self.canada_completed)
                self.stats['canada']['median_wait_time'] = sorted_canada[len(sorted_canada) // 2]
                self.stats['canada']['vehicles_completed'] = len(self.canada_completed)
            else:
                self.stats['canada']['avg_wait_time'] = 0
                self.stats['canada']['min_wait_time'] = 0
                self.stats['canada']['max_wait_time'] = 0
                self.stats['canada']['median_wait_time'] = 0
                self.stats['canada']['vehicles_completed'] = 0
            
            self.stats['canada']['vehicles_in_zone'] = len(self.canada_tracking)
            
            # ===== US STATISTICS =====
            if self.us_completed:
                self.stats['us']['avg_wait_time'] = sum(self.us_completed) / len(self.us_completed)
                self.stats['us']['min_wait_time'] = min(self.us_completed)
                self.stats['us']['max_wait_time'] = max(self.us_completed)
                sorted_us = sorted(self.us_completed)
                self.stats['us']['median_wait_time'] = sorted_us[len(sorted_us) // 2]
                self.stats['us']['vehicles_completed'] = len(self.us_completed)
            else:
                self.stats['us']['avg_wait_time'] = 0
                self.stats['us']['min_wait_time'] = 0
                self.stats['us']['max_wait_time'] = 0
                self.stats['us']['median_wait_time'] = 0
                self.stats['us']['vehicles_completed'] = 0
            
            self.stats['us']['vehicles_in_zone'] = len(self.us_tracking)
        
        except Exception as e:
            print(f"[DETECTOR ANALYZER] Error calculating stats: {e}")
    
    def get_statistics(self):
        """Get current statistics"""
        self.calculate_statistics()
        return self.stats
    
    def export_to_csv(self, filename='detector_wait_times.csv'):
        """Export wait time data to CSV"""
        import csv
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['zone', 'wait_time_seconds'])
            
            for wait_time in self.canada_completed:
                writer.writerow(['canada', wait_time])
            
            for wait_time in self.us_completed:
                writer.writerow(['us', wait_time])
        
        print(f"[DETECTOR ANALYZER] Exported to {filename}")
    
    def get_summary(self):
        """Get summary report"""
        self.calculate_statistics()
        
        return {
            'canada': {
                'avg_wait_time': round(self.stats['canada']['avg_wait_time'], 2),
                'min_wait_time': round(self.stats['canada']['min_wait_time'], 2),
                'max_wait_time': round(self.stats['canada']['max_wait_time'], 2),
                'median_wait_time': round(self.stats['canada']['median_wait_time'], 2),
                'vehicles_completed': self.stats['canada']['vehicles_completed'],
                'vehicles_in_zone': self.stats['canada']['vehicles_in_zone']
            },
            'us': {
                'avg_wait_time': round(self.stats['us']['avg_wait_time'], 2),
                'min_wait_time': round(self.stats['us']['min_wait_time'], 2),
                'max_wait_time': round(self.stats['us']['max_wait_time'], 2),
                'median_wait_time': round(self.stats['us']['median_wait_time'], 2),
                'vehicles_completed': self.stats['us']['vehicles_completed'],
                'vehicles_in_zone': self.stats['us']['vehicles_in_zone']
            },
            'total': {
                'avg_wait_time': round(
                    (self.stats['canada']['avg_wait_time'] + self.stats['us']['avg_wait_time']) / 2 
                    if (self.stats['canada']['vehicles_completed'] > 0 and self.stats['us']['vehicles_completed'] > 0) 
                    else 0, 2
                ),
                'total_vehicles_completed': self.stats['canada']['vehicles_completed'] + self.stats['us']['vehicles_completed']
            }
        }

def run_simulation():
    global simulation_running
    global simulation_data
    global breakdown_status, broken_vehicle_ids
    global lane_closure_status, original_flow_rates
    global mainlane_breakdown_status
    global main_lane_ids, main_lane_broken_vehicle
    global main_lane_modes
    global bridge_breakdown_status, bridge_lane_ids, bridge_lane_broken_vehicle, bridge_lane_modes
    global detector_wait_analyzer

    # ----------------------
    # PREP BEFORE SIM START
    # ----------------------
    update_route_file()  # update flows
    detector_wait_analyzer = DetectorWaitTimeAnalyzer()  # ← ADD THIS LINE
    print("[DETECTOR ANALYZER] Detector-based tracking initialized")  # ← ADD THIS LINE


    # SUMO start config
    sumo_config = [
        "sumo-gui",
        "-c", "bwb.sumocfg",
        "--step-length", "0.05",
        "--delay", "100",
        "--lateral-resolution", "0.1",
    ]

    # dict to hold broken vehicles on main lanes
    main_lane_broken_vehicle = {}

    try:
        # ----------------------
        # START SUMO
        # ----------------------
        traci.start(sumo_config)
        print("SUMO started successfully.")
        print("DEBUG: Lanes inside SUMO:")
        for lane in traci.lane.getIDList():
            print("  ", lane)

        # Track unique vehicles per booth - EXTENDED TO 20 BOOTHS
        booth_vehicles = {}
        for i in range(20):  # CHANGED FROM 21 to 20
            booth_vehicles[f"e2_booth_{i}"] = set()

        step_counter = 0

        # ----------------------
        # SIMULATION LOOP
        # ----------------------
        while simulation_running and traci.simulation.getMinExpectedNumber() > 0:

            traci.simulationStep()
            
            # =========================
            step_counter += 1
            handle_toll_booth_closures(step_counter)

             # ===== CHECK DETECTORS FOR WAIT TIME ANALYSIS =====
            sim_time = traci.simulation.getTime()  # ← ADD THIS LINE
            detector_wait_analyzer.check_detectors(sim_time)  # ← ADD THIS LINE
       

            
                                    
            
            # ==================================================================
            # 2️⃣  MAIN LANE CLOSURES (E3_0–E3_3)
            # ==================================================================
            for lane_key, lane_id in main_lane_ids.items():

                if lane_closure_status.get(lane_key, False):

                    # remove vehicles currently in the lane
                    try:
                        vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
                        for v in vehicles:
                            traci.vehicle.remove(v)
                        traci.lane.setAllowed(lane_id, [])
                        print(f"[MAIN CLOSE] vehicles removed from {lane_id}")
                    except Exception:
                        pass

                    # fully close class
                    try:
                        traci.lane.setAllowed(lane_id, [])
                    except Exception:
                        print(f"[CLOSE MAIN] Could not set allowed = [] on lane{lane_id}")
                        pass

                else:
                    # Lane is open: enforce current mode (cars/trucks/both)
                    try:
                        mode = main_lane_modes.get(lane_key, 'both')
                        if mode == 'cars':
                            traci.lane.setAllowed(lane_id, ["passenger"])
                        elif mode == 'trucks':
                            traci.lane.setAllowed(lane_id, ["truck"])
                        else:  # both
                            traci.lane.setAllowed(lane_id, ["passenger", "truck"])
                    except Exception:
                        pass

            for lane_key, lane_id in main_lane_ids.items():
                mode = main_lane_modes[lane_key]

                if lane_closure_status.get(lane_key, False):
                    traci.lane.setAllowed(lane_id, [])
                    # remove vehicles etc
                    continue

                # Only restrict E3_* lanes
                if mode == "cars":
                    traci.lane.setAllowed(lane_id, ["passenger"])
                elif mode == "trucks":
                    traci.lane.setAllowed(lane_id, ["truck"])
                else:
                    traci.lane.setAllowed(lane_id, ["passenger", "truck"])

            # ==================================================================
            # 2B️⃣  BRIDGE LANE CLOSURES (E0_0-E0_2, E8_0-E8_2)
            # ==================================================================
            for lane_key, lane_id in bridge_lane_ids.items():

                if lane_closure_status.get(lane_key, False):
                    # remove vehicles currently in the lane
                    try:
                        vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
                        for v in vehicles:
                            traci.vehicle.remove(v)
                        traci.lane.setAllowed(lane_id, [])
                        print(f"[BRIDGE CLOSE] vehicles removed from {lane_id}")
                    except Exception:
                        pass

                    # fully close class
                    try:
                        traci.lane.setAllowed(lane_id, [])
                    except Exception:
                        print(f"[CLOSE BRIDGE] Could not set allowed = [] on lane {lane_id}")
                        pass

                else:
                    # Lane is open: enforce current mode (cars/trucks/both)
                    try:
                        mode = bridge_lane_modes.get(lane_key, 'both')
                        if mode == 'cars':
                            traci.lane.setAllowed(lane_id, ["passenger"])
                        elif mode == 'trucks':
                            traci.lane.setAllowed(lane_id, ["truck"])
                        else:  # both
                            traci.lane.setAllowed(lane_id, ["passenger", "truck"])
                    except Exception:
                        pass

            for lane_key, lane_id in bridge_lane_ids.items():
                mode = bridge_lane_modes[lane_key]

                if lane_closure_status.get(lane_key, False):
                    traci.lane.setAllowed(lane_id, [])
                    continue

                # Restrict bridge lanes based on mode
                if mode == "cars":
                    traci.lane.setAllowed(lane_id, ["passenger"])
                elif mode == "trucks":
                    traci.lane.setAllowed(lane_id, ["truck"])
                else:
                    traci.lane.setAllowed(lane_id, ["passenger", "truck"])


            # ==================================================================
            # 3️⃣ HANDLE TOLL-BOOTH BREAKDOWNS (EXTENDED TO BOOTHS 0-19)
            # ==================================================================
            for booth_num in range(20):  # CHANGED FROM 21 to 20
                booth_key = f"booth_{booth_num}"
                
                # Determine correct lane ID based on booth number
                # Booths 0-5 use E7_0 to E7_5
                # Booths 6-19 use E0_0 to E0_13
                if booth_num <= 5:
                    lane_id = f"E7_{booth_num}"
                else:
                    lane_id = f"E0_{booth_num - 6}"  # booth_6 -> E0_0, booth_7 -> E0_1, etc.

                # skip if lane closed
                if lane_closure_status.get(booth_key, False):
                    if booth_key in broken_vehicle_ids:
                        del broken_vehicle_ids[booth_key]
                    continue

                # trigger breakdown
                if breakdown_status[booth_key]:
                    if booth_key not in broken_vehicle_ids:
                        try:
                            vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
                            if vehicles:
                                v = vehicles[0]
                                traci.vehicle.setColor(v, (255, 0, 0, 255))
                                traci.vehicle.setSpeed(v, 0)
                                broken_vehicle_ids[booth_key] = v
                                print(f"[BREAKDOWN BOOTH] {v} stopped on {lane_id}")
                        except:
                            pass
                    else:
                        # keep stopped
                        v = broken_vehicle_ids[booth_key]
                        if v in traci.vehicle.getIDList():
                            traci.vehicle.setSpeed(v, 0)

                else:
                    # clear breakdown
                    if booth_key in broken_vehicle_ids:
                        v = broken_vehicle_ids[booth_key]
                        try:
                            if v in traci.vehicle.getIDList():
                                traci.vehicle.setColor(v, (255, 255, 0, 255))
                                traci.vehicle.setSpeed(v, -1)
                        except:
                            pass

                        del broken_vehicle_ids[booth_key]

            # ==================================================================
            # 4️⃣ MAIN LANE BREAKDOWNS (E3_0..E3_3)
            # ==================================================================
            for lane_key, lane_id in main_lane_ids.items():
                if mainlane_breakdown_status.get(lane_key, False):
                    # If no broken vehicle yet, pick one
                    if lane_key not in main_lane_broken_vehicle:
                        try:
                            vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
                            if vehicles:
                                v_id = vehicles[0]
                                traci.vehicle.setColor(v_id, (255, 0, 0, 255))
                                traci.vehicle.setSpeed(v_id, 0)
                                main_lane_broken_vehicle[lane_key] = v_id
                                print(f"[MAIN BREAKDOWN] Vehicle {v_id} broken on {lane_id}")
                        except Exception as e:
                            print(f"[MAIN BREAKDOWN] Error on {lane_id}: {e}")
                    else:
                        # Keep it stopped
                        v_id = main_lane_broken_vehicle[lane_key]
                        if v_id in traci.vehicle.getIDList():
                            try:
                                traci.vehicle.setSpeed(v_id, 0)
                            except Exception:
                                pass
                else:
                    # Clear breakdown if exists
                    if lane_key in main_lane_broken_vehicle:
                        v_id = main_lane_broken_vehicle[lane_key]
                        try:
                            if v_id in traci.vehicle.getIDList():
                                traci.vehicle.setColor(v_id, (255, 255, 0, 255))
                                traci.vehicle.setSpeed(v_id, -1)
                        except Exception:
                            pass
                        del main_lane_broken_vehicle[lane_key]

            # ==================================================================
            # 4B️⃣ BRIDGE LANE BREAKDOWNS (E0_0-E0_2, E8_0-E8_2)
            # ==================================================================
            for lane_key, lane_id in bridge_lane_ids.items():
                if bridge_breakdown_status.get(lane_key, False):
                    # If no broken vehicle yet, pick one
                    if lane_key not in bridge_lane_broken_vehicle:
                        try:
                            vehicles = traci.lane.getLastStepVehicleIDs(lane_id)
                            if vehicles:
                                v_id = vehicles[0]
                                traci.vehicle.setColor(v_id, (255, 0, 0, 255))
                                traci.vehicle.setSpeed(v_id, 0)
                                bridge_lane_broken_vehicle[lane_key] = v_id
                                print(f"[BRIDGE BREAKDOWN] Vehicle {v_id} broken on {lane_id}")
                        except Exception as e:
                            print(f"[BRIDGE BREAKDOWN] Error on {lane_id}: {e}")
                    else:
                        # Keep it stopped
                        v_id = bridge_lane_broken_vehicle[lane_key]
                        if v_id in traci.vehicle.getIDList():
                            try:
                                traci.vehicle.setSpeed(v_id, 0)
                            except Exception:
                                pass
                else:
                    # Clear breakdown if exists
                    if lane_key in bridge_lane_broken_vehicle:
                        v_id = bridge_lane_broken_vehicle[lane_key]
                        try:
                            if v_id in traci.vehicle.getIDList():
                                traci.vehicle.setColor(v_id, (255, 255, 0, 255))
                                traci.vehicle.setSpeed(v_id, -1)
                        except Exception:
                            pass
                        del bridge_lane_broken_vehicle[lane_key]

            # ==================================================================
            # 5️⃣ UPDATE DASHBOARD METRICS EVERY 20 STEPS
            # ==================================================================
            if step_counter % 20 == 0:

                sim_time = traci.simulation.getTime()
                simulation_data["time"] = round(sim_time, 1)
                detector_wait_analyzer.calculate_statistics() 

                # Toll Booth Metrics - EXTENDED TO 21 BOOTHS
                for booth_id in booth_vehicles:
                    if booth_id in traci.lanearea.getIDList():
                        ids = traci.lanearea.getLastStepVehicleIDs(booth_id)
                        booth_vehicles[booth_id].update(ids)
                        queue = traci.lanearea.getLastStepHaltingNumber(booth_id)
                        occ = traci.lanearea.getLastStepOccupancy(booth_id)

                        num = booth_id.split("_")[-1]
                        key = f"booth_{num}"

                        simulation_data["revenue"][key] = len(booth_vehicles[booth_id]) * 20
                        simulation_data["vehicle_counts"][key] = len(booth_vehicles[booth_id])
                        simulation_data["queue_lengths"][key] = queue
                        simulation_data["occupancy"][key] = round(occ * 100, 1)
                        simulation_data["broken_vehicles"][key] = key in broken_vehicle_ids

                simulation_data["total_revenue"] = sum(
                    len(v) * 20 for v in booth_vehicles.values()
                )
                simulation_data["total_queue"] = sum(
                    simulation_data["queue_lengths"].get(f"booth_{i}", 0) for i in range(20)  # CHANGED FROM 21 to 20
                )

                # ------- MAIN LANE METRICS -------
                lanearea_ids = set(traci.lanearea.getIDList())
                for lane_key, lane_id in main_lane_ids.items():

                    det_id = lane_key  # detector name in bwb.add.xml

                    if det_id in traci.lanearea.getIDList():
                        q = traci.lanearea.getLastStepHaltingNumber(det_id)
                        occ = traci.lanearea.getLastStepOccupancy(det_id)
                        simulation_data['mainlane_queue'][lane_key] = q
                        simulation_data['mainlane_occupancy'][lane_key] = round(occ * 100.0, 1)
                    else:
                        simulation_data['mainlane_queue'][lane_key] = 0
                        simulation_data['mainlane_occupancy'][lane_key] = 0.0

                    simulation_data["mainlane_breakdown"][lane_key] = bool(
                        mainlane_breakdown_status[lane_key]
                    )

                # ------- BRIDGE LANE METRICS -------
                for lane_key, lane_id in bridge_lane_ids.items():

                    det_id = lane_key  # detector name in bwb.add.xml

                    if det_id in traci.lanearea.getIDList():
                        q = traci.lanearea.getLastStepHaltingNumber(det_id)
                        occ = traci.lanearea.getLastStepOccupancy(det_id)
                        simulation_data['bridgelane_queue'][lane_key] = q
                        simulation_data['bridgelane_occupancy'][lane_key] = round(occ * 100.0, 1)
                    else:
                        simulation_data['bridgelane_queue'][lane_key] = 0
                        simulation_data['bridgelane_occupancy'][lane_key] = 0.0

                    simulation_data["bridgelane_breakdown"][lane_key] = bool(
                        bridge_breakdown_status[lane_key]
                    )

    except Exception as e:
        print("Simulation error:", e)

    finally:
        simulation_running = False
        try:
            traci.close()
        except:
            pass

        print("Simulation stopped cleanly.")



#=========================================================
# FLASK ROUTES
#=========================================================
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_simulation():
    """Start the SUMO simulation"""
    global simulation_thread, simulation_running, simulation_data, lane_closure_status, original_flow_rates
    global breakdown_status, broken_vehicle_ids
    global mainlane_breakdown_status, main_lane_broken_vehicle, main_lane_modes
    global bridge_breakdown_status, bridge_lane_broken_vehicle, bridge_lane_modes

    if not simulation_running:
        # Reset simulation data and breakdown status
        simulation_data = {
            'revenue': {},
            'total_revenue': 0,
            'vehicle_counts': {},
            'queue_lengths': {},
            'occupancy': {},
            'broken_vehicles': {},
            'time': 0.0,
            'mainlane_queue': {
                'main_0': 0,
                'main_1': 0,
                'main_2': 0,
                'main_3': 0
            },
            'mainlane_occupancy': {
                'main_0': 0.0,
                'main_1': 0.0,
                'main_2': 0.0,
                'main_3': 0.0
            },
            'mainlane_breakdown': {
                'main_0': False,
                'main_1': False,
                'main_2': False,
                'main_3': False
            },
            'bridgelane_queue': {
                'bridge_0': 0,
                'bridge_1': 0,
                'bridge_2': 0
            },
            'bridgelane_occupancy': {
                'bridge_0': 0.0,
                'bridge_1': 0.0,
                'bridge_2': 0.0
            },
            'bridgelane_breakdown': {
                'bridge_0': False,
                'bridge_1': False,
                'bridge_2': False
            }
        }
        # Reset breakdown status
        for booth in breakdown_status:
            breakdown_status[booth] = False
        broken_vehicle_ids.clear()

        # Reset lane closure status
        for booth in lane_closure_status:
            lane_closure_status[booth] = False
        original_flow_rates.clear()

        # Reset main lane breakdown
        for lane in mainlane_breakdown_status:
            mainlane_breakdown_status[lane] = False
        main_lane_broken_vehicle = {}

        # Reset bridge lane breakdown
        for lane in bridge_breakdown_status:
            bridge_breakdown_status[lane] = False
        bridge_lane_broken_vehicle = {}

        # Reset all lane closures (booths + main lanes + bridge lanes)
        for key in lane_closure_status:
            lane_closure_status[key] = False
        original_flow_rates.clear()
        
        # Reset main lane modes to 'both'
        for lane in main_lane_modes:
            main_lane_modes[lane] = 'both'
            
        # Reset bridge lane modes to 'both'
        for lane in bridge_lane_modes:
            bridge_lane_modes[lane] = 'both'

        
        simulation_running = True
        simulation_thread = threading.Thread(target=run_simulation)
        simulation_thread.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already running'})

@app.route('/stop', methods=['POST'])
def stop_simulation():
    """Stop the SUMO simulation"""
    global simulation_running
    
    simulation_running = False
    time.sleep(1)  # Give time for the simulation to stop
    
    # Kill any remaining SUMO processes
    try:
        subprocess.run(['pkill', '-f', 'sumo-gui'], capture_output=True)
    except:
        pass
    
    return jsonify({'status': 'stopped'})

@app.route('/status', methods=['GET'])
def get_status():
    """Get current simulation status"""
    global simulation_running, simulation_data, breakdown_status, lane_closure_status, mainlane_breakdown_status
    global main_lane_modes, bridge_breakdown_status, bridge_lane_modes
    global detector_wait_analyzer 

    # Get detector wait time stats if available
    detector_stats = None  
    if detector_wait_analyzer is not None:  
        detector_stats = detector_wait_analyzer.get_summary() 

    return jsonify({
        'running': simulation_running,
        'data': simulation_data,
        'flow_rates': flow_rates,
        'breakdown_status': breakdown_status,
        'lane_closure_status': lane_closure_status,
        'mainlane_breakdown_status': mainlane_breakdown_status,
        'main_lane_modes' : main_lane_modes,
        'bridge_breakdown_status': bridge_breakdown_status,
        'bridge_lane_modes': bridge_lane_modes,
        'detector_wait_stats': detector_stats 
    })

@app.route('/update_flow', methods=['POST'])
def update_flow():
    """Update flow rates for toll booths"""
    global flow_rates, simulation_running
    
    if simulation_running:
        return jsonify({'status': 'error', 'message': 'Stop simulation before updating flow rates'}), 400
    
    data = request.json
    booth = data.get('booth')
    rate = data.get('rate')
    
    if booth in flow_rates:
        try:
            flow_rates[booth] = int(rate)
            update_route_file()
            return jsonify({'status': 'success', 'flow_rates': flow_rates})
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid rate value'}), 400
    
    return jsonify({'status': 'error', 'message': 'Invalid booth'}), 400

@app.route('/reset_flows', methods=['POST'])
def reset_flows():
    """Reset flow rates to defaults"""
    global flow_rates

    # Reset all 20 booths to 100
    for i in range(20):  # CHANGED FROM 21 to 20
        flow_rates[f'booth_{i}'] = 100
    
    update_route_file()
    return jsonify({'status': 'success', 'flow_rates': flow_rates})

@app.route('/trigger_breakdown', methods=['POST'])
def trigger_breakdown():
    """Trigger a vehicle breakdown on a specific lane"""
    global breakdown_status, simulation_running
    
    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400
    
    data = request.json
    booth = data.get('booth')
    
    if booth in breakdown_status:
        breakdown_status[booth] = True
        return jsonify({'status': 'success', 'message': f'Breakdown triggered for {booth}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid booth'}), 400

@app.route('/clear_breakdown', methods=['POST'])
def clear_breakdown():
    """Clear a vehicle breakdown on a specific lane"""
    global breakdown_status, simulation_running
    
    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400
    
    data = request.json
    booth = data.get('booth')
    
    if booth in breakdown_status:
        breakdown_status[booth] = False
        # The actual vehicle removal will be handled in the simulation loop
        return jsonify({'status': 'success', 'message': f'Breakdown cleared for {booth}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid booth'}), 400

@app.route('/clear_all_breakdowns', methods=['POST'])
def clear_all_breakdowns():
    """Clear all vehicle breakdowns"""
    global breakdown_status, mainlane_breakdown_status, bridge_breakdown_status

    for booth in breakdown_status:
        breakdown_status[booth] = False
    for k in mainlane_breakdown_status:
        mainlane_breakdown_status[k] = False
    for k in bridge_breakdown_status:
        bridge_breakdown_status[k] = False

    # The actual vehicle removal will be handled in the simulation loop
    return jsonify({'status': 'success', 'message': 'All breakdowns cleared'})

@app.route('/close_lane', methods=['POST'])
def close_lane():
    """Close a specific toll booth lane"""
    global lane_closure_status, breakdown_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400

    data = request.json
    booth = data.get('booth')

    if booth in lane_closure_status:
        # Mark lane as closed
        lane_closure_status[booth] = True

        # Clear any breakdown on this lane
        if booth in breakdown_status:
            breakdown_status[booth] = False

        # The TraCI logic (handle_toll_booth_closures) will handle rerouting automatically
        print(f"[FRONTEND] Booth {booth} closed - vehicles will reroute")
        return jsonify({'status': 'success', 'message': f'Booth {booth} closed'})

    return jsonify({'status': 'error', 'message': 'Invalid booth'}), 400

@app.route('/open_lane', methods=['POST'])
def open_lane():
    """Open a previously closed toll booth lane"""
    global lane_closure_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400

    data = request.json
    booth = data.get('booth')

    if booth in lane_closure_status:
        # Mark lane as open
        lane_closure_status[booth] = False

        print(f"[FRONTEND] Booth {booth} opened")
        return jsonify({'status': 'success', 'message': f'Booth {booth} opened'})

    return jsonify({'status': 'error', 'message': 'Invalid booth'}), 400
@app.route('/close_main_lane', methods=['POST'])
def close_main_lane():
    global lane_closure_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400
    data = request.json
    lane = data.get('lane')

    if lane in main_lane_ids and lane in lane_closure_status:
        lane_closure_status[lane] = True
        print(f"[CLOSE MAIN] {lane} closed")
        return jsonify({'status': 'success', 'message': f'{lane} closed'})

    return jsonify({'status': 'error', 'message': 'Invalid main lane'}), 400

@app.route('/open_main_lane', methods=['POST'])
def open_main_lane():
    global lane_closure_status, simulation_running
    if not simulation_running:
        return({'status': 'errror', 'message' : 'Simulation is not running'}),400
    data = request.json
    lane = data.get('lane')

    if lane in lane_closure_status:
        lane_closure_status[lane] = False
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error'}), 400

@app.route('/break_main_lane', methods=['POST'])
def break_main_lane():
    global mainlane_breakdown_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400

    data = request.json
    lane = data.get('lane')   # 'main_0', 'main_1', etc.

    if lane in mainlane_breakdown_status:
        mainlane_breakdown_status[lane] = True
        print(f"Main lane breakdown triggered on {lane}")
        return jsonify({'status': 'success', 'message': f'Breakdown triggered for {lane}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid main lane'}), 400


@app.route('/fix_main_lane', methods=['POST'])
def fix_main_lane():
    global mainlane_breakdown_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400

    data = request.json
    lane = data.get('lane')

    if lane in mainlane_breakdown_status:
        mainlane_breakdown_status[lane] = False
        print(f"Main lane breakdown cleared on {lane}")
        return jsonify({'status': 'success', 'message': f'Breakdown cleared for {lane}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid main lane'}), 400


@app.route('/set_main_lane_mode', methods=['POST'])
def set_main_lane_mode():
    """
    Set vehicle type mode for a main lane:
    mode ∈ {'cars', 'trucks', 'both'}
    """
    global main_lane_modes, simulation_running

    data = request.json
    lane = data.get('lane')   # 'main_0', ...
    mode = data.get('mode')   # 'cars', 'trucks', 'both'

    if lane not in main_lane_ids:
        return jsonify({'status': 'error', 'message': 'Invalid main lane'}), 400
    if mode not in ('cars', 'trucks', 'both'):
        return jsonify({'status': 'error', 'message': 'Invalid mode'}), 400

    main_lane_modes[lane] = mode
    print(f"[MODE] {lane} set to {mode}")

    # You don't HAVE to apply immediately; the simulation loop will
    # pick it up next step via get_allowed_classes_for_mode.
    return jsonify({'status': 'success', 'lane': lane, 'mode': mode})

# =============================================================================
# BRIDGE LANE ROUTES (E0_0-E0_2, E8_0-E8_2)
# =============================================================================

@app.route('/close_bridge_lane', methods=['POST'])
def close_bridge_lane():
    global lane_closure_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400
    
    data = request.json
    lane = data.get('lane')

    if lane in bridge_lane_ids and lane in lane_closure_status:
        lane_closure_status[lane] = True
        print(f"[CLOSE BRIDGE] {lane} closed")
        return jsonify({'status': 'success', 'message': f'{lane} closed'})

    return jsonify({'status': 'error', 'message': 'Invalid bridge lane'}), 400

@app.route('/open_bridge_lane', methods=['POST'])
def open_bridge_lane():
    global lane_closure_status, simulation_running
    
    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400
    
    data = request.json
    lane = data.get('lane')

    if lane in lane_closure_status:
        lane_closure_status[lane] = False
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error'}), 400

@app.route('/break_bridge_lane', methods=['POST'])
def break_bridge_lane():
    global bridge_breakdown_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400

    data = request.json
    lane = data.get('lane')   # 'bridge_0', 'bridge_1', etc.

    if lane in bridge_breakdown_status:
        bridge_breakdown_status[lane] = True
        print(f"Bridge lane breakdown triggered on {lane}")
        return jsonify({'status': 'success', 'message': f'Breakdown triggered for {lane}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid bridge lane'}), 400

@app.route('/fix_bridge_lane', methods=['POST'])
def fix_bridge_lane():
    global bridge_breakdown_status, simulation_running

    if not simulation_running:
        return jsonify({'status': 'error', 'message': 'Simulation not running'}), 400

    data = request.json
    lane = data.get('lane')

    if lane in bridge_breakdown_status:
        bridge_breakdown_status[lane] = False
        print(f"Bridge lane breakdown cleared on {lane}")
        return jsonify({'status': 'success', 'message': f'Breakdown cleared for {lane}'})
    
    return jsonify({'status': 'error', 'message': 'Invalid bridge lane'}), 400

@app.route('/set_bridge_lane_mode', methods=['POST'])
def set_bridge_lane_mode():
    """
    Set vehicle type mode for a bridge lane:
    mode ∈ {'cars', 'trucks', 'both'}
    """
    global bridge_lane_modes, simulation_running

    data = request.json
    lane = data.get('lane')   # 'bridge_0', ...
    mode = data.get('mode')   # 'cars', 'trucks', 'both'

    if lane not in bridge_lane_ids:
        return jsonify({'status': 'error', 'message': 'Invalid bridge lane'}), 400
    if mode not in ('cars', 'trucks', 'both'):
        return jsonify({'status': 'error', 'message': 'Invalid mode'}), 400

    bridge_lane_modes[lane] = mode
    print(f"[MODE] {lane} set to {mode}")

    return jsonify({'status': 'success', 'lane': lane, 'mode': mode})

@app.route('/clear_all_closures', methods=['POST'])
def clear_all_closures():
    """Open all closed lanes"""
    global lane_closure_status, flow_rates, original_flow_rates

    for booth in lane_closure_status:
        lane_closure_status[booth] = False
        if booth in original_flow_rates:
            flow_rates[booth] = original_flow_rates[booth]

    original_flow_rates.clear()

    return jsonify({'status': 'success', 'message': 'All lanes opened'})

# ============================================================================
# DETECTOR-BASED WAIT TIME ANALYSIS ENDPOINTS
# ============================================================================

@app.route('/detector_wait_time/stats', methods=['GET'])
def get_detector_wait_stats():
    """Get current detector-based wait time statistics"""
    global detector_wait_analyzer
    
    if detector_wait_analyzer is None:
        return jsonify({'status': 'error', 'message': 'Detector analyzer not initialized'}), 400
    
    stats = detector_wait_analyzer.get_statistics()
    
    return jsonify({
        'status': 'success',
        'statistics': stats
    })

@app.route('/detector_wait_time/summary', methods=['GET'])
def get_detector_wait_summary():
    """Get summary report of detector-based wait times"""
    global detector_wait_analyzer
    
    if detector_wait_analyzer is None:
        return jsonify({'status': 'error', 'message': 'Detector analyzer not initialized'}), 400
    
    summary = detector_wait_analyzer.get_summary()
    
    return jsonify({
        'status': 'success',
        'summary': summary
    })

@app.route('/detector_wait_time/export', methods=['POST'])
def export_detector_wait_data():
    """Export detector wait time data to CSV"""
    global detector_wait_analyzer
    
    if detector_wait_analyzer is None:
        return jsonify({'status': 'error', 'message': 'Detector analyzer not initialized'}), 400
    
    data = request.json
    filename = data.get('filename', 'detector_wait_times.csv')
    
    try:
        detector_wait_analyzer.export_to_csv(filename)
        return jsonify({
            'status': 'success',
            'message': f'Data exported to {filename}',
            'filename': filename
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)