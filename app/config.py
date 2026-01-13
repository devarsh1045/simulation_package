import os
import scaling_config as scale
class Config:
    SIM_GUI = os.getenv("SIM_GUI", "1") == "1"
    SIM_STEP = os.getenv("SIM_STEP", "0.2")
    SIM_LAT_RES = os.getenv("SIM_LAT_RES", "0.1")

    LANE_CONFIG = {"booth": 20, "main": 4, "bridge": 3}

    DETECTION_RADIUS = scale.DETECTION_RADIUS  # 200.0
    TRAVEL_TIME_INFLATION = scale.TRAVEL_TIME_INFLATION  # 15.0

    METRICS_EVERY_STEPS = 20
    REFRESH_TRAVELTIME_EVERY_STEPS = 50
