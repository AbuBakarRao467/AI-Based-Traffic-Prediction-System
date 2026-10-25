"""
demo_checkpoints.py
Fixed monitoring points — jaise real CCTV cameras hote, unki simulated
images. System automatically inhe process karta hai, koi manual
upload involved nahi hai real user flow mein.

NOTE: Ye prototype approach hai. Real deployment mein ye live camera
feeds se replace hoga — architecture wahi rahega, sirf data source badlega.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_DATA_DIR = os.path.join(BASE_DIR, "..", "demo_data")

import math

# ===== APNI CITY KE 5 CHECKPOINTS — COORDINATES GOOGLE MAPS SE NIKALEIN =====
DEMO_CHECKPOINTS = [
    {
        "id": "checkpoint_1",
        "name": "Farid Gate Chowk",
        "lat": 29.4048,
        "lon": 71.6820,
        # "traffic_image": "demo_data/traffic 1.jpg",
        # "damage_image": "demo_data/damage 1.jpg",
        "traffic_image": os.path.join(DEMO_DATA_DIR, "traffic 1.jpg"),
"damage_image": os.path.join(DEMO_DATA_DIR, "damage 1.jpg"),
    },
    {
        "id": "checkpoint_2",
        "name": "Islamia University Road",
        "lat": 29.3831,
        "lon": 71.7325,
        # "traffic_image": "demo_data/traffic 2.jpg",
        # "damage_image": "demo_data/damage 2.jpg",
        "traffic_image": os.path.join(DEMO_DATA_DIR, "traffic 2.jpg"),
"damage_image": os.path.join(DEMO_DATA_DIR, "damage 2.jpg"),
    },
    {
        "id": "checkpoint_3",
        "name": "Railway Station Chowk",
        "lat": 29.3956,
        "lon": 71.6836,
        # "traffic_image": "demo_data/traffic 3.jpg",
        # "damage_image": "demo_data/damage 4.jpg",
        "traffic_image": os.path.join(DEMO_DATA_DIR, "traffic 3.jpg"),
"damage_image": os.path.join(DEMO_DATA_DIR, "damage 4.jpg"),
    },
    {
        "id": "checkpoint_4",
        "name": "Model Town Road",
        "lat": 29.3700,
        "lon": 71.7100,
        # "traffic_image": "demo_data/traffic 4.jpg",
        # "damage_image": "demo_data/damage 5.jpg",
        "traffic_image": os.path.join(DEMO_DATA_DIR, "traffic 4.jpg"),
"damage_image": os.path.join(DEMO_DATA_DIR, "damage 5.jpg"),
    },
    {
        "id": "checkpoint_5",
        "name": "Bahawalpur Airport Road",
        "lat": 29.3480,
        "lon": 71.7169,
        # "traffic_image": "demo_data/traffic 5.jpg",
        # "damage_image": "demo_data/damage 6.jpg",
        "traffic_image": os.path.join(DEMO_DATA_DIR, "traffic 5.jpg"),
"damage_image": os.path.join(DEMO_DATA_DIR, "damage 6 .jpg"),
    },
]
# ==============================================================================


def find_nearest_checkpoint(lat, lon, checkpoints=None):
    """
    Diye gaye coordinate se sabse nazdeek checkpoint dhoondta hai.
    """
    if checkpoints is None:
        checkpoints = DEMO_CHECKPOINTS

    nearest = None
    min_dist = float("inf")

    for cp in checkpoints:
        dist = math.sqrt((lat - cp["lat"]) ** 2 + (lon - cp["lon"]) ** 2)
        if dist < min_dist:
            min_dist = dist
            nearest = cp

    return nearest


def calculate_priority_score(traffic_level, damage_level):
    """
    Traffic aur damage ke hisaab se ek 0-100 priority score deta hai.
    Higher score = zyada urgent repair/attention chahiye.
    """
    traffic_weight = {"Low": 1, "Medium": 2, "High": 3}
    damage_weight = {"None": 0, "Minor": 1, "Moderate": 2, "Severe": 3}

    t_score = traffic_weight.get(traffic_level, 2)
    d_score = damage_weight.get(damage_level, 1)

    raw_score = t_score + d_score  # max possible = 6
    normalized_score = round((raw_score / 6) * 100)

    if normalized_score >= 70:
        priority_label = "Urgent"
    elif normalized_score >= 40:
        priority_label = "Monitor"
    else:
        priority_label = "Low Priority"

    return normalized_score, priority_label            