"""
model_loader.py (Backend Version)
Sab trained models yahan se load honge. Streamlit ke @st.cache_resource
ki jagah, ab simple Python-level caching use karenge (kyunki FastAPI
mein Streamlit ka decorator available nahi hai).
"""

from ultralytics import YOLO
import os

VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck (COCO classes)

# Simple caching — model ek baar load hoga, dobara dobara load nahi hoga
_vehicle_model = None
_road_damage_model = None


def load_vehicle_detection_model():
    global _vehicle_model
    if _vehicle_model is None:
        local_path = os.path.join(os.path.dirname(__file__), "..", "models", "vehicle_detection", "yolov8n.pt")
        if os.path.exists(local_path):
            _vehicle_model = YOLO(local_path)
        else:
            _vehicle_model = YOLO("yolov8n.pt")
    return _vehicle_model


def load_road_damage_model():
    global _road_damage_model
    if _road_damage_model is None:
        local_path = os.path.join(os.path.dirname(__file__), "..", "models", "road_damage", "road_damage_best.pt")
        _road_damage_model = YOLO(local_path)
    return _road_damage_model


def detect_vehicles(image, model):
    results = model(image, verbose=False)
    count = 0
    for box in results[0].boxes:
        class_id = int(box.cls[0])
        if class_id in VEHICLE_CLASSES:
            count += 1
    annotated_image = results[0].plot()
    return count, annotated_image


def detect_road_damage(image, model):
    results = model(image, verbose=False)
    damage_count = len(results[0].boxes)
    annotated_image = results[0].plot()
    detected_classes = [model.names[int(box.cls[0])] for box in results[0].boxes]
    return damage_count, annotated_image, detected_classes