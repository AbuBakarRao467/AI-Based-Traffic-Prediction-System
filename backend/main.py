"""
main.py
FastAPI backend — saare AI models aur route-calculation logic ko
REST API endpoints ke through frontend (HTML/JS) ke liye expose karta hai.
"""

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
import cv2
import base64
import sys
import os
import hashlib
from utils.demo_checkpoints import DEMO_CHECKPOINTS, find_nearest_checkpoint, calculate_priority_score
import json
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.responses import FileResponse


# USERS_FILE = os.path.join(os.path.dirname(__file__), "users_db.json")


# def load_users():
#     """JSON file se users load karta hai. Agar file na ho, default admin bana deta hai."""
#     if os.path.exists(USERS_FILE):
#         with open(USERS_FILE, "r") as f:
#             return json.load(f)

#     # Pehli baar chalne pr, ek default admin account bana dena
#     default_users = {
#         "admin": {
#             "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
#             "role": "admin",
#             "name": "Admin User",
#         }
#     }
#     save_users(default_users)
#     return default_users


# def save_users(users_dict):
#     """Users ko JSON file mein permanently save karta hai."""
#     with open(USERS_FILE, "w") as f:
#         json.dump(users_dict, f, indent=2)


# USERS_DB = load_users()

import database as db

db.init_db()
db.seed_checkpoints_if_empty(DEMO_CHECKPOINTS)

sys.path.append(os.path.dirname(__file__))
from utils.model_loader import (
    load_vehicle_detection_model, detect_vehicles,
    load_road_damage_model, detect_road_damage
)
from utils.traffic_estimator import estimate_traffic
from utils.damage_estimator import estimate_severity
from utils.map_helper import search_location, get_routes

app = FastAPI(title="AI Traffic System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo/sample images ka folder
DEMO_DATA_DIR = Path(__file__).resolve().parent / "demo_data"


@app.get("/api/samples")
def get_sample_images():
    """Demo folder ki sample images ki list return karta hai."""
    if not DEMO_DATA_DIR.exists():
        return {"samples": []}

    samples = [
        file.name
        for file in DEMO_DATA_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    return {"samples": sorted(samples)}


@app.get("/api/samples/{filename:path}")
def get_sample_image(filename: str):
    """Sample image ko frontend ko serve karta hai."""

    try:
        file_path = (DEMO_DATA_DIR / filename).resolve()
        demo_dir = DEMO_DATA_DIR.resolve()

        # Security: demo folder se bahar ki file access na ho
        file_path.relative_to(demo_dir)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid file path"
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Sample image not found: {filename}"
        )

    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid image type"
        )

    return FileResponse(file_path)



def image_to_base64(image_array):
    """Numpy image ko base64 string mein convert karta hai (JSON mein bhejne ke liye)."""
    _, buffer = cv2.imencode('.jpg', cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR))
    return base64.b64encode(buffer).decode('utf-8')


@app.get("/")
def root():
    return {"message": "AI Traffic System API is running"}


@app.post("/api/vehicle-detection")
async def vehicle_detection_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    model = load_vehicle_detection_model()
    count, annotated_image = detect_vehicles(image, model)
    
    return JSONResponse({
        "vehicle_count": count,
        "annotated_image": image_to_base64(annotated_image),
    })


@app.post("/api/traffic-estimation")
async def traffic_estimation_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    model = load_vehicle_detection_model()
    count, annotated_image = detect_vehicles(image, model)
    level, emoji = estimate_traffic(count)
    db.log_detection("traffic_estimation", {"vehicle_count": count, "traffic_level": level})
    return JSONResponse({
        "vehicle_count": count,
        "traffic_level": level,
        "traffic_emoji": emoji,
        "annotated_image": image_to_base64(annotated_image),
    })


@app.post("/api/road-damage-detection")
async def road_damage_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    model = load_road_damage_model()
    count, annotated_image, detected_classes = detect_road_damage(image, model)
    severity, emoji = estimate_severity(count)
    db.log_detection("road_damage", {"damage_count": count, "severity_level": severity})
    return JSONResponse({
        "damage_count": count,
        "severity_level": severity,
        "severity_emoji": emoji,
        "detected_classes": list(set(detected_classes)),
        "annotated_image": image_to_base64(annotated_image),
    })


@app.get("/api/search-location")
def search_location_endpoint(place: str):
    coords = search_location(place)
    if coords:
        return {"found": True, "lat": coords[0], "lon": coords[1]}
    return {"found": False}


# @app.get("/api/routes")
# def routes_endpoint(start_lat: float, start_lon: float, end_lat: float, end_lon: float, mode: str = "driving"):
#     routes = get_routes((start_lat, start_lon), (end_lat, end_lon), mode=mode, alternatives=3)
#     return {"routes": routes} 

@app.get("/api/routes")
def routes_endpoint(start_lat: float, start_lon: float, end_lat: float, end_lon: float, mode: str = "driving"):
    routes = get_routes((start_lat, start_lon), (end_lat, end_lon), mode=mode, alternatives=3)
    if routes:
        db.log_route_search("", "", (start_lat, start_lon), (end_lat, end_lon), mode, routes[0])
    return {"routes": routes}





from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


# @app.post("/api/login")
# def login_endpoint(request: LoginRequest):
#     user = USERS_DB.get(request.username)

#     if not user:
#         return JSONResponse(status_code=401, content={"success": False, "message": "Invalid username"})

#     password_hash = hashlib.sha256(request.password.encode()).hexdigest()
#     if password_hash != user["password_hash"]:
#         return JSONResponse(status_code=401, content={"success": False, "message": "Invalid password"})

#     return {
#         "success": True,
#         "username": request.username,
#         "name": user["name"],
#         "role": user["role"],
#     }

@app.post("/api/login")
def login_endpoint(request: LoginRequest):
    user = db.get_user(request.username)

    if not user:
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid username"})

    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if password_hash != user["password_hash"]:
        return JSONResponse(status_code=401, content={"success": False, "message": "Invalid password"})

    return {
        "success": True,
        "username": request.username,
        "name": user["name"],
        "role": user["role"],
    }



AUTHORITY_ACCESS_CODE = "IUB-TRAFFIC-2026"  # Sirf verified authority members ko diya jata


class SignupRequest(BaseModel):
    username: str
    password: str
    name: str
    access_code: str


# @app.post("/api/signup")
# def signup_endpoint(request: SignupRequest):
#     if request.access_code != AUTHORITY_ACCESS_CODE:
#         return JSONResponse(
#             status_code=403,
#             content={"success": False, "message": "Invalid Authority Access Code. Please contact your department administrator."}
#         )

#     if request.username in USERS_DB:
#         return JSONResponse(
#             status_code=400,
#             content={"success": False, "message": "This username is already registered."}
#         )

#     if len(request.password) < 6:
#         return JSONResponse(
#             status_code=400,
#             content={"success": False, "message": "Password must be at least 6 characters long."}
#         )

#     USERS_DB[request.username] = {
#         "password_hash": hashlib.sha256(request.password.encode()).hexdigest(),
#         "role": "admin",
#         "name": request.name,
#     }
#     save_users(USERS_DB)

#     return {"success": True, "message": f"Welcome, {request.name}. Your Authority account has been created successfully."}

@app.post("/api/signup")
def signup_endpoint(request: SignupRequest):
    if request.access_code != AUTHORITY_ACCESS_CODE:
        return JSONResponse(status_code=403, content={"success": False, "message": "Invalid Authority Access Code. Please contact your department administrator."})

    if db.get_user(request.username):
        return JSONResponse(status_code=400, content={"success": False, "message": "This username is already registered."})

    if len(request.password) < 6:
        return JSONResponse(status_code=400, content={"success": False, "message": "Password must be at least 6 characters long."})

    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    db.create_user(request.username, password_hash, request.name, role="admin")

    return {"success": True, "message": f"Welcome, {request.name}. Your Authority account has been created successfully."}

def process_checkpoint(checkpoint):
    """
    Ek checkpoint ki traffic aur damage images ko process karta hai,
    aur uska poora status + priority score return karta hai.
    """
    vehicle_model = load_vehicle_detection_model()
    damage_model = load_road_damage_model()

    # Traffic image process karna
    traffic_img = cv2.imread(checkpoint["traffic_image"])
    traffic_img = cv2.cvtColor(traffic_img, cv2.COLOR_BGR2RGB)
    vehicle_count, _ = detect_vehicles(traffic_img, vehicle_model)
    traffic_level, traffic_emoji = estimate_traffic(vehicle_count)

    # Damage image process karna
    damage_img = cv2.imread(checkpoint["damage_image"])
    damage_img = cv2.cvtColor(damage_img, cv2.COLOR_BGR2RGB)
    damage_count, _, _ = detect_road_damage(damage_img, damage_model)
    damage_level, damage_emoji = estimate_severity(damage_count)

    # Priority score calculate karna
    priority_score, priority_label = calculate_priority_score(traffic_level, damage_level)

    return {
        "id": checkpoint["id"],
        "name": checkpoint["name"],
        "lat": checkpoint["lat"],
        "lon": checkpoint["lon"],
        "vehicle_count": vehicle_count,
        "traffic_level": traffic_level,
        "traffic_emoji": traffic_emoji,
        "damage_count": damage_count,
        "damage_level": damage_level,
        "damage_emoji": damage_emoji,
        "priority_score": priority_score,
        "priority_label": priority_label,
    }


# @app.get("/api/authority/priority-report")
# def get_priority_report():
#     """
#     Authority Dashboard ke liye — saare checkpoints ko process karke,
#     priority score ke hisaab se sorted list deta hai (highest priority pehle).
#     """
#     results = [process_checkpoint(cp) for cp in DEMO_CHECKPOINTS]
#     results.sort(key=lambda x: x["priority_score"], reverse=True)
#     return {"checkpoints": results}


# @app.get("/api/route-health-score")
# def get_route_health_score(lat: float, lon: float):
#     """
#     User Route Planner ke liye — route ke ek point (jaise route ka
#     midpoint) ke nazdeek checkpoint dhoond kar uska health score deta hai.
#     """
#     nearest = find_nearest_checkpoint(lat, lon)
#     if not nearest:
#         return {"available": False}

#     result = process_checkpoint(nearest)
#     result["available"] = True
#     return result


@app.get("/api/authority/priority-report")
def get_priority_report():
    checkpoints = db.get_all_checkpoints()
    results = [process_checkpoint(cp) for cp in checkpoints]
    results.sort(key=lambda x: x["priority_score"], reverse=True)
    return {"checkpoints": results}


@app.get("/api/route-health-score")
def get_route_health_score(lat: float, lon: float):
    checkpoints = db.get_all_checkpoints()
    nearest = find_nearest_checkpoint(lat, lon, checkpoints)
    if not nearest:
        return {"available": False}
    result = process_checkpoint(nearest)
    result["available"] = True
    return result

# import os

# SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "demo_data") 


# SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "demo_data")


# @app.get("/api/samples")
# def get_samples():
#     """demo_data folder mein jo bhi images hain, unki list deta hai."""
#     try:
#         if not os.path.exists(SAMPLES_DIR):
#             return {"samples": []}
#         files = [f for f in os.listdir(SAMPLES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
#         return {"samples": sorted(files)}
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})


# @app.get("/api/samples/{filename:path}")
# def get_sample_image(filename: str):
#     """Ek specific sample image ki actual file serve karta hai."""
#     try:
#         filepath = os.path.normpath(os.path.join(SAMPLES_DIR, filename))
#         if not os.path.exists(filepath):
#             return JSONResponse(status_code=404, content={"error": f"File not found: {filename}"})
#         return FileResponse(filepath)
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})