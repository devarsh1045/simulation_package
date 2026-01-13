from pathlib import Path
from ..utils.sumo import project_path, BASE_DIR
import scaling_config as scale

def find_adjacent_open_booths(state, booth_num: int):
    # Determine section
    if booth_num <= 5:
        section_booths = list(range(6))
    else:
        section_booths = list(range(6, 20))

    adjacent = []
    for offset in [1, -1, 2, -2, 3, -3]:
        neighbor = booth_num + offset
        if neighbor in section_booths:
            if not state.lane_closure_status.get(f"booth_{neighbor}", False):
                adjacent.append(neighbor)
                if len(adjacent) >= 2:
                    break

    if not adjacent:
        for b in section_booths:
            if b != booth_num and not state.lane_closure_status.get(f"booth_{b}", False):
                adjacent.append(b)

    return adjacent

def update_route_file(state):
    """
    Generates bwb.rou.xml based on current flow_rates and closures.
    Uses 2-stop system: Canada (0-5) + US (6-19).
    """
    # Vehicle types mapping (same as your current)
    vehicle_types = {
        'booth_0': 'car', 'booth_1': 'car', 'booth_2': 'car',
        'booth_3': 'car', 'booth_4': 'truck', 'booth_5': 'truck',
        'booth_6': 'car', 'booth_7': 'car', 'booth_8': 'car',
        'booth_9': 'car', 'booth_10': 'car', 'booth_11': 'car',
        'booth_12': 'car', 'booth_13': 'car', 'booth_14': 'truck',
        'booth_15': 'truck', 'booth_16': 'truck', 'booth_17': 'truck',
        'booth_18': 'truck', 'booth_19': 'truck',
    }

    booth_pairing = {
        0: (0, 6), 1: (1, 7), 2: (2, 10), 3: (3, 11), 4: (4, 14), 5: (5, 17),
        6: (0, 6), 7: (0, 7), 8: (1, 8), 9: (1, 9), 10: (2, 10), 11: (2, 11),
        12: (3, 12), 13: (3, 13), 14: (4, 14), 15: (4, 15), 16: (4, 16),
        17: (5, 17), 18: (5, 18), 19: (5, 19),
    }

    redistributed_flows = {}
    for i in range(20):
        booth_key = f"booth_{i}"
        if not state.lane_closure_status.get(booth_key, False):
            redistributed_flows[booth_key] = state.flow_rates.get(booth_key, 100)
        else:
            redistributed_flows[booth_key] = 0
            closed_flow = state.flow_rates.get(booth_key, 100)
            adjacent = find_adjacent_open_booths(state, i)
            if adjacent:
                per = closed_flow // len(adjacent)
                for a in adjacent:
                    ak = f"booth_{a}"
                    redistributed_flows[ak] = redistributed_flows.get(ak, 100) + per

    open_canada = [i for i in range(6) if not state.lane_closure_status.get(f"booth_{i}", False)]
    open_us = [i for i in range(6, 20) if not state.lane_closure_status.get(f"booth_{i}", False)]
    if not open_canada or not open_us:
        print("[ERROR] Need at least one open booth in each section!")
        return ""

    flow_entries = []
    for i in range(20):
        booth_key = f"booth_{i}"
        flow_rate = redistributed_flows.get(booth_key, 0)
        if flow_rate == 0:
            continue

        c_booth, u_booth = booth_pairing[i]
        if c_booth not in open_canada:
            c_booth = min(open_canada, key=lambda b: abs(b - c_booth))
        if u_booth not in open_us:
            u_booth = min(open_us, key=lambda b: abs(b - u_booth))

        vtype = vehicle_types[booth_key]
        route_edges = "E3 E4 E7 E8 E0"
        flow_entries.append(
f'''     <flow id="f_booth_{i}" type="{vtype}" begin="0.1"
        departLane="best" departPos="0.00"
        end="3600.00" vehsPerHour="{flow_rate}">
        <route edges="{route_edges}"/>
        <stop busStop="bs_{c_booth}" duration="2.00"/>
        <stop busStop="bs_{u_booth}" duration="2.00"/>
    </flow>
'''
        )

    routes_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    <vType id="car" minGap="0.10" vClass="passenger" color="0,255,0" jmCrossingGap="0.10"
           jmIgnoreKeepClearTime="1.00" carFollowModel="IDM">
        <param key="has.rerouting.device" value="true"/>
        <param key="device.rerouting.period" value="10"/>
    </vType>
    <vType id="truck" minGap="0.15" vClass="truck" color="0,0,255" jmCrossingGap="0.30"
           jmIgnoreKeepClearTime="1.00" carFollowModel="IDM">
        <param key="has.rerouting.device" value="true"/>
        <param key="device.rerouting.period" value="10"/>
    </vType>

{''.join(flow_entries)}
</routes>
'''

    out_path = Path(BASE_DIR) / "bwb.rou.xml"
    out_path.write_text(routes_xml, encoding="utf-8")
    print(f"[ROUTES] Generated {len(flow_entries)} flows")
    return routes_xml
