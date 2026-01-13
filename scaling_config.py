

# ============================================================================
# NETWORK GEOMETRY (meters)
# ============================================================================

EDGE_LENGTHS = {
    'E3': 600.0,      # Main approach road
    'E4': 120.0,      # Canada toll plaza approach
    'E7': 60.0,       # Canada toll booth zone
    'E8': 1768.0,     # Peace Bridge span (ACTUAL)
    'E0': 180.0,      # US toll plaza
}

# ============================================================================
# TRAFFIC PARAMETERS
# ============================================================================

# Flow rates (vehicles per hour per booth)
CANADA_FLOW_PER_BOOTH = 50   # 50 veh/hour per Canada booth
US_FLOW_PER_BOOTH = 25       # 25 veh/hour per US booth

# Processing times (seconds)
CANADA_PROCESSING_TIME = 8.0   # 8 seconds average
US_PROCESSING_TIME = 12.0      # 12 seconds average

# Vehicle speeds (m/s)
CAR_MAX_SPEED = 22.22    # 80 km/h
TRUCK_MAX_SPEED = 19.44  # 70 km/h

# ============================================================================
# DETECTOR POSITIONS (meters)
# ============================================================================

DETECTOR_POSITIONS = {
    'canada_entry': 20.0,     # E4 at 20m
    'canada_exit': 54.0,      # E7 at 54m (90% of 60m)
    'us_entry': 15.0,         # E0 at 15m
    'us_exit': 162.0,         # E0 at 162m (90% of 180m)
}

# ============================================================================
# BREAKDOWN ANALYSIS
# ============================================================================

DETECTION_RADIUS = 200.0        # 200 meters
TRAVEL_TIME_INFLATION = 15.0    # 15x inflation

# ============================================================================
# SIMULATION CONFIG
# ============================================================================

STEP_LENGTH = 1.0               # 1 second per step
DELAY = 0                       # No delay (fast)
LATERAL_RESOLUTION = 0.5        # Moderate precision