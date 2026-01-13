class DetectorWaitTimeAnalyzer:
    """
    Detector-based wait time measurement.
    Vehicles tracked between entry detectors and exit detectors.
    """

    def __init__(self, traci):
        self.traci = traci

        self.canada_tracking = {}  # vid -> entry_time
        self.us_tracking = {}

        self.canada_completed = []
        self.us_completed = []

        self.stats = {
            "canada": {"avg_wait_time": 0, "min_wait_time": 0, "max_wait_time": 0, "median_wait_time": 0,
                       "vehicles_completed": 0, "vehicles_in_zone": 0},
            "us": {"avg_wait_time": 0, "min_wait_time": 0, "max_wait_time": 0, "median_wait_time": 0,
                   "vehicles_completed": 0, "vehicles_in_zone": 0},
        }

        self.canada_entry_detectors = [f"entry_canada_{i}" for i in range(6)]
        self.canada_exit_detectors = [f"exit_canada_{i}" for i in range(6)]
        self.us_entry_detectors = [f"entry_us_{i}" for i in range(14)]
        self.us_exit_detectors = [f"exit_us_{i}" for i in range(14)]

    def check_detectors(self, sim_time: float):
        traci = self.traci

        # Canada entry
        for det in self.canada_entry_detectors:
            try:
                for vid in traci.inductionloop.getLastStepVehicleIDs(det):
                    if vid not in self.canada_tracking:
                        self.canada_tracking[vid] = sim_time
            except:
                pass

        # Canada exit
        for det in self.canada_exit_detectors:
            try:
                for vid in traci.inductionloop.getLastStepVehicleIDs(det):
                    if vid in self.canada_tracking:
                        wt = sim_time - self.canada_tracking[vid]
                        self.canada_completed.append(wt)
                        del self.canada_tracking[vid]
            except:
                pass

        # US entry
        for det in self.us_entry_detectors:
            try:
                for vid in traci.inductionloop.getLastStepVehicleIDs(det):
                    if vid not in self.us_tracking:
                        self.us_tracking[vid] = sim_time
            except:
                pass

        # US exit
        for det in self.us_exit_detectors:
            try:
                for vid in traci.inductionloop.getLastStepVehicleIDs(det):
                    if vid in self.us_tracking:
                        wt = sim_time - self.us_tracking[vid]
                        self.us_completed.append(wt)
                        del self.us_tracking[vid]
            except:
                pass

    def _calc_one(self, arr):
        if not arr:
            return 0, 0, 0, 0, 0
        avg = sum(arr) / len(arr)
        mn = min(arr)
        mx = max(arr)
        s = sorted(arr)
        med = s[len(s) // 2]
        return avg, mn, mx, med, len(arr)

    def calculate_statistics(self):
        ca = self._calc_one(self.canada_completed)
        us = self._calc_one(self.us_completed)

        self.stats["canada"]["avg_wait_time"], self.stats["canada"]["min_wait_time"], \
        self.stats["canada"]["max_wait_time"], self.stats["canada"]["median_wait_time"], \
        self.stats["canada"]["vehicles_completed"] = ca
        self.stats["canada"]["vehicles_in_zone"] = len(self.canada_tracking)

        self.stats["us"]["avg_wait_time"], self.stats["us"]["min_wait_time"], \
        self.stats["us"]["max_wait_time"], self.stats["us"]["median_wait_time"], \
        self.stats["us"]["vehicles_completed"] = us
        self.stats["us"]["vehicles_in_zone"] = len(self.us_tracking)

    def get_statistics(self):
        self.calculate_statistics()
        return self.stats

    def get_summary(self):
        self.calculate_statistics()
        return {
            "canada": {
                "avg_wait_time": round(self.stats["canada"]["avg_wait_time"], 2),
                "min_wait_time": round(self.stats["canada"]["min_wait_time"], 2),
                "max_wait_time": round(self.stats["canada"]["max_wait_time"], 2),
                "median_wait_time": round(self.stats["canada"]["median_wait_time"], 2),
                "vehicles_completed": self.stats["canada"]["vehicles_completed"],
                "vehicles_in_zone": self.stats["canada"]["vehicles_in_zone"],
            },
            "us": {
                "avg_wait_time": round(self.stats["us"]["avg_wait_time"], 2),
                "min_wait_time": round(self.stats["us"]["min_wait_time"], 2),
                "max_wait_time": round(self.stats["us"]["max_wait_time"], 2),
                "median_wait_time": round(self.stats["us"]["median_wait_time"], 2),
                "vehicles_completed": self.stats["us"]["vehicles_completed"],
                "vehicles_in_zone": self.stats["us"]["vehicles_in_zone"],
            },
            "total": {
                "avg_wait_time": round(
                    (self.stats["canada"]["avg_wait_time"] + self.stats["us"]["avg_wait_time"]) / 2
                    if (self.stats["canada"]["vehicles_completed"] > 0 and self.stats["us"]["vehicles_completed"] > 0)
                    else 0,
                    2,
                ),
                "total_vehicles_completed": self.stats["canada"]["vehicles_completed"] + self.stats["us"]["vehicles_completed"],
            },
        }
