"""
map_helper.py
Map banane, location search, aur route calculate karne ke functions.
"""

import folium
import requests
from geopy.geocoders import Nominatim
from typing import Dict, Tuple, Optional, List


def create_base_map(center_lat: float, center_lon: float, zoom: int = 13) -> folium.Map:
    """Base map banata hai given center point pr."""
    return folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")


def search_location(place_name: str) -> Optional[Tuple[float, float]]:
    """Location ka naam lekar (lat, lon) return karta hai."""
    geolocator = Nominatim(user_agent="ai_traffic_system")
    try:
        location = geolocator.geocode(place_name, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


BASE_URLS = {
    "driving": "https://routing.openstreetmap.de/routed-car/route/v1/driving",
    "walking": "https://routing.openstreetmap.de/routed-foot/route/v1/foot",
    "cycling": "https://routing.openstreetmap.de/routed-bike/route/v1/bike",
}


def get_routes(start_coords, end_coords, mode="driving", alternatives=3):
    """OSRM se multiple route options nikalta hai, har route ke segments (road-wise) ke saath."""
    lat1, lon1 = start_coords
    lat2, lon2 = end_coords

    base_url = BASE_URLS.get(mode, BASE_URLS["driving"])
    url = (
        f"{base_url}/{lon1},{lat1};{lon2},{lat2}"
        f"?alternatives=true&overview=full&geometries=geojson&steps=true"
    )

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok":
            return []

        routes = []
        for route in data["routes"][:alternatives]:
            coords = [(lat, lon) for lon, lat in route["geometry"]["coordinates"]]

            # Har step ko ek "segment" ki tarah nikalna — apni geometry aur road name ke saath
            segments = []
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    step_coords = [(lat, lon) for lon, lat in step["geometry"]["coordinates"]]
                    road_name = step.get("name") or "Unnamed road"
                    segments.append({
                        "coordinates": step_coords,
                        "road_name": road_name,
                    })

            routes.append({
                "coordinates": coords,
                "distance_km": round(route["distance"] / 1000, 2),
                "duration_min": round(route["duration"] / 60, 1),
                "segments": segments,
            })
        return routes
    except Exception as e:
        print(f"Routing error: {e}")
        return []


def format_step(step):
    """OSRM ke ek 'step' ko insaan-samajh-sake wali line mein badalta hai."""
    maneuver = step.get("maneuver", {})
    m_type = maneuver.get("type", "")
    modifier = maneuver.get("modifier", "")
    name = step.get("name") or "road"
    distance = step.get("distance", 0)

    if m_type == "depart":
        text = f"Start on {name}"
    elif m_type == "arrive":
        text = "Aap apni manzil pr pahunch gaye"
    elif m_type == "turn":
        text = f"{modifier.capitalize()} mudein — {name} pr"
    elif m_type == "continue":
        text = f"{name} pr seedha jaate rahein"
    elif m_type == "roundabout":
        text = f"Roundabout se {name} ki taraf jayein"
    else:
        text = f"{name} pr jaari rakhein"

    dist_text = f"{distance/1000:.1f} km" if distance >= 1000 else f"{int(distance)} m"
    return f"{text} ({dist_text})"


def format_step(step):
    """OSRM ke ek 'step' (raw data) ko insaan-samajh-sake wali line mein badalta hai."""
    maneuver = step.get("maneuver", {})
    m_type = maneuver.get("type", "")
    modifier = maneuver.get("modifier", "")
    name = step.get("name") or "road"
    distance = step.get("distance", 0)

    if m_type == "depart":
        text = f"Start on {name}"
    elif m_type == "arrive":
        text = "Aap apni manzil pr pahunch gaye"
    elif m_type == "turn":
        text = f"{modifier.capitalize()} mudein — {name} pr"
    elif m_type == "continue":
        text = f"{name} pr seedha jaate rahein"
    elif m_type == "roundabout":
        text = f"Roundabout se {name} ki taraf jayein"
    else:
        text = f"{name} pr jaari rakhein"

    dist_text = f"{distance/1000:.1f} km" if distance >= 1000 else f"{int(distance)} m"
    return f"{text} ({dist_text})"


def draw_routes_on_map(base_map, sorted_routes, start_coords, end_coords):
    """
    Har route ko segments mein draw karta hai. Alternatives patli (thin)
    lines mein hoti hain, best route moti (thick) — is se overlap ki
    jagah pr bhi dono ke colors visible rehte hain.
    """
    folium.Marker(start_coords, tooltip="Start", icon=folium.Icon(color="green", icon="play")).add_to(base_map)
    folium.Marker(end_coords, tooltip="Destination", icon=folium.Icon(color="red", icon="flag")).add_to(base_map)

    alt_colors = ["purple", "orange", "darkred", "cadetblue"]

    # Pehle best route draw karo (moti line, neeche layer mein)
    best_route = sorted_routes[0]
    for segment in best_route["segments"]:
        folium.PolyLine(
            segment["coordinates"],
            color="green",
            weight=6  ,
            opacity=1.0,
            tooltip =f"📍 {segment['road_name']} (Best Route)",
        ).add_to(base_map)

    # Ab alternatives draw karo (patli line, upar layer mein)
    for i, route in enumerate(sorted_routes):
        if i == 0:
            continue

        color = alt_colors[(i - 1) % len(alt_colors)]
        for segment in route["segments"]:
            folium.PolyLine(
                segment["coordinates"],
                color=color,
                weight=3,
                opacity=0.8,
                tooltip=f"📍 {segment['road_name']} (Alternative {i})",
            ).add_to(base_map)

    bounds = [start_coords, end_coords] + sorted_routes[0]["coordinates"]
    base_map.fit_bounds(bounds)

    return base_map