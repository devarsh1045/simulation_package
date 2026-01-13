import threading
from dataclasses import dataclass, field
from .config import Config

@dataclass
class SimulationState:
    lock: threading.Lock = field(default_factory=threading.Lock)

    simulation_thread = None
    simulation_running: bool = False

    lane_config: dict = field(default_factory=lambda: Config.LANE_CONFIG.copy())

    # flows
    flow_rates: dict = field(default_factory=lambda: {f"booth_{i}": 50 for i in range(Config.LANE_CONFIG["booth"])})
    original_flow_rates: dict = field(default_factory=dict)

    # closures + breakdowns
    lane_closure_status: dict = field(default_factory=lambda: {
        f"{lane}_{i}": False
        for lane, count in Config.LANE_CONFIG.items()
        for i in range(count)
    })
    breakdown_status: dict = field(default_factory=lambda: {f"booth_{i}": False for i in range(Config.LANE_CONFIG["booth"])})
    broken_vehicle_ids: dict = field(default_factory=dict)

    # lane IDs
    main_lane_ids: dict = field(default_factory=lambda: {
        "main_0": "E3_0", "main_1": "E3_1", "main_2": "E3_2", "main_3": "E3_3",
    })
    bridge_lane_ids: dict = field(default_factory=lambda: {
        "bridge_0": "E8_0", "bridge_1": "E8_1", "bridge_2": "E8_2",
    })

    # lane modes
    main_lane_modes: dict = field(default_factory=lambda: {f"main_{i}": "both" for i in range(Config.LANE_CONFIG["main"])})
    bridge_lane_modes: dict = field(default_factory=lambda: {f"bridge_{i}": "both" for i in range(Config.LANE_CONFIG["bridge"])})

    # main/bridge breakdown toggles
    mainlane_breakdown_status: dict = field(default_factory=lambda: {f"main_{i}": False for i in range(Config.LANE_CONFIG["main"])})
    bridge_breakdown_status: dict = field(default_factory=lambda: {f"bridge_{i}": False for i in range(Config.LANE_CONFIG["bridge"])})

    # tracking breakdown effects
    breakdown_tracking: dict = field(default_factory=lambda: {
        **{f"main_{i}": {"active": False, "vehicle_id": None, "position": 0, "lane_id": None, "edge_id": None, "affected_count": 0}
           for i in range(Config.LANE_CONFIG["main"])},
        **{f"bridge_{i}": {"active": False, "vehicle_id": None, "position": 0, "lane_id": None, "edge_id": None, "affected_count": 0}
           for i in range(Config.LANE_CONFIG["bridge"])},
    })
    breakdown_refresh_counter: int = 0

    detector_wait_analyzer = None

    simulation_data: dict = field(default_factory=dict)

    def reset_simulation_data(self):
        self.simulation_data = {
            "revenue": {},
            "total_revenue": 0,
            "vehicle_counts": {},
            "queue_lengths": {},
            "occupancy": {},
            "broken_vehicles": {},
            "time": 0.0,

            "mainlane_queue": {f"main_{i}": 0 for i in range(Config.LANE_CONFIG["main"])},
            "mainlane_occupancy": {f"main_{i}": 0.0 for i in range(Config.LANE_CONFIG["main"])},
            "mainlane_breakdown": {f"main_{i}": False for i in range(Config.LANE_CONFIG["main"])},

            "bridgelane_queue": {f"bridge_{i}": 0 for i in range(Config.LANE_CONFIG["bridge"])},
            "bridgelane_occupancy": {f"bridge_{i}": 0.0 for i in range(Config.LANE_CONFIG["bridge"])},
            "bridgelane_breakdown": {f"bridge_{i}": False for i in range(Config.LANE_CONFIG["bridge"])},
        }

    def reset_all(self):
        self.simulation_running = False

        self.reset_simulation_data()

        for k in self.breakdown_status:
            self.breakdown_status[k] = False
        self.broken_vehicle_ids.clear()

        for k in self.lane_closure_status:
            self.lane_closure_status[k] = False
        self.original_flow_rates.clear()

        for k in self.mainlane_breakdown_status:
            self.mainlane_breakdown_status[k] = False
        for k in self.bridge_breakdown_status:
            self.bridge_breakdown_status[k] = False

        for k in self.main_lane_modes:
            self.main_lane_modes[k] = "both"
        for k in self.bridge_lane_modes:
            self.bridge_lane_modes[k] = "both"

        # reset breakdown tracking
        for lane_key in self.breakdown_tracking:
            self.breakdown_tracking[lane_key] = {
                "active": False, "vehicle_id": None, "position": 0,
                "lane_id": None, "edge_id": None, "affected_count": 0
            }
        self.breakdown_refresh_counter = 0

STATE = SimulationState()
STATE.reset_simulation_data()
