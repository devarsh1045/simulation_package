# Step 1: Add modules to provide access to specific libraries and functions
import os # Module provides functions to handle file paths, directories, environment variables
import sys # Module provides access to Python-specific system parameters and functions

# Step 2: Establish path to SUMO (SUMO_HOME)
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Step 3: Add Traci module to provide access to specific libraries and functions
import traci # Static network information (such as reading and analyzing network files)

# Step 4: Define Sumo configuration (headless mode for testing)
Sumo_config = [
    'sumo',  # Using sumo instead of sumo-gui for headless mode
    '-c', 'bwb.sumocfg',
    '--step-length', '0.05',
    '--lateral-resolution', '0.1',
    '--duration-log.statistics', 'true',
    '--end', '100'  # Run for 100 seconds only for testing
]

# Step 5: Open connection between SUMO and Traci
traci.start(Sumo_config)

# Step 6: Define Variables
vehicle_speed = 0
total_speed = 0

# Dictionary to track unique vehicles per booth
booth_vehicles = {
    'e2_booth_0': set(),
    'e2_booth_1': set(),
    'e2_booth_2': set(),
    'e2_booth_3': set(),
    'e2_booth_4': set(),
    'e2_booth_5': set()
}

# Step 7: Define Functions

# Step 8: Take simulation steps until there are no more vehicles in the network
step_counter = 0
while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep() # Move simulation forward 1 step
    step_counter += 1
    
    # Only print every 20 steps (1 second of simulation time)
    if step_counter % 20 == 0:
        # Check each toll booth detector
        booth_status = []
        for booth_id in booth_vehicles.keys():
            if booth_id in traci.lanearea.getIDList():
                # Get vehicle IDs for this booth
                vehicle_ids = traci.lanearea.getLastStepVehicleIDs(booth_id)
                booth_vehicles[booth_id].update(vehicle_ids)
                
                # Get detector metrics
                vehicle_count = traci.lanearea.getLastStepVehicleNumber(booth_id)
                halting_number = traci.lanearea.getLastStepHaltingNumber(booth_id)
                
                # Collect booth information
                booth_num = booth_id.split('_')[-1]
                booth_revenue = len(booth_vehicles[booth_id]) * 20
                if booth_revenue > 0:
                    booth_status.append(f"B{booth_num}:${booth_revenue}")
        
        # Calculate and display total revenue across all booths
        total_unique_vehicles = sum(len(vehicles) for vehicles in booth_vehicles.values())
        if total_unique_vehicles > 0:
            sim_time = traci.simulation.getTime()
            print(f"Time={sim_time:.1f}s | {' '.join(booth_status)} | Total: ${total_unique_vehicles * 20}")

    if 't_0' in traci.vehicle.getIDList():
        vehicle_speed = traci.vehicle.getSpeed('t_0')
        total_speed = total_speed + vehicle_speed
    # step_count = step_count + 1

# Step 9: Close connection between SUMO and Traci
print("\nFinal Statistics:")
for booth_id in booth_vehicles.keys():
    booth_num = booth_id.split('_')[-1]
    vehicles = len(booth_vehicles[booth_id])
    if vehicles > 0:
        print(f"Booth {booth_num}: {vehicles} vehicles, Revenue: ${vehicles * 20}")

total_vehicles = sum(len(vehicles) for vehicles in booth_vehicles.values())
print(f"\nTotal Unique Vehicles: {total_vehicles}")
print(f"Total Revenue: ${total_vehicles * 20}")

traci.close()