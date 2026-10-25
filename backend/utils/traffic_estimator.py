"""
traffic_estimator.py

"""


def estimate_traffic(vehicle_count):
    
    if vehicle_count <= 5:
        return "Low", "🟢"
    elif vehicle_count <= 15:
        return "Medium", "🟡"
    else:
        return "High", "🔴"
