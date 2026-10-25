/**
 * route-planner.js
 * Location lookup, route fetching, map drawing and the route health readout.
 */

let map = null;
let drawnLayers = [];
let routeState = null;
let selectedRouteIndex = 0;
let selectedMode = "driving";

const CITY_CENTER = [29.3956, 71.6836];

const PAINT = "#F4B223";
const ALT_LINE = "#8B9199";
const STOP = "#C0342D";

function initMap() {
  if (map) return;
  map = L.map("map", { zoomControl: false }).setView(CITY_CENTER, 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);
  L.control.zoom({ position: "bottomright" }).addTo(map);
}

async function searchLocation(placeName) {
  const url = `${API_BASE_URL}/api/search-location?place=${encodeURIComponent(placeName)}`;
  const res = await fetch(url);
  const data = await res.json();
  return data.found ? [data.lat, data.lon] : null;
}

async function fetchRoutes(startCoords, endCoords, mode) {
  const url =
    `${API_BASE_URL}/api/routes?start_lat=${startCoords[0]}&start_lon=${startCoords[1]}` +
    `&end_lat=${endCoords[0]}&end_lon=${endCoords[1]}&mode=${mode}`;
  const res = await fetch(url);
  const data = await res.json();
  return data.routes;
}

function drawRoutesOnMap(routes, startCoords, endCoords) {
  drawnLayers.forEach((l) => map.removeLayer(l));
  drawnLayers = [];

  const pin = (colour) =>
    L.divIcon({
      className: "",
      html: `<div style="width:14px;height:14px;border-radius:50%;background:${colour};border:3px solid #23262D;box-shadow:0 0 0 2px ${colour}55;"></div>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });

  drawnLayers.push(L.marker(startCoords, { icon: pin(PAINT) }).addTo(map).bindTooltip("Start"));
  drawnLayers.push(L.marker(endCoords, { icon: pin(STOP) }).addTo(map).bindTooltip("Destination"));

  // Alternatives first, so the chosen route always sits on top.
  routes.forEach((route, i) => {
    if (i === selectedRouteIndex) return;
    route.segments.forEach((seg) => {
      const line = L.polyline(seg.coordinates, {
        color: ALT_LINE,
        weight: 3,
        opacity: 0.75,
      })
        .bindTooltip(seg.road_name)
        .on("click", () => selectRoute(i));
      line.addTo(map);
      drawnLayers.push(line);
    });
  });

  const chosen = routes[selectedRouteIndex];

  // Casing under the chosen route gives it the weight of a painted line.
  chosen.segments.forEach((seg) => {
    const casing = L.polyline(seg.coordinates, { color: "#23262D", weight: 9, opacity: 0.9 });
    casing.addTo(map);
    drawnLayers.push(casing);
  });
  chosen.segments.forEach((seg) => {
    const line = L.polyline(seg.coordinates, { color: PAINT, weight: 5, opacity: 1 }).bindTooltip(
      seg.road_name
    );
    line.addTo(map);
    drawnLayers.push(line);
  });

  const mid = chosen.coordinates[Math.floor(chosen.coordinates.length / 2)];
  const label = L.marker(mid, {
    icon: L.divIcon({
      className: "",
      html: `<div class="route-label">${chosen.distance_km} km · ${chosen.duration_min} min</div>`,
      iconSize: [0, 0],
    }),
  }).addTo(map);
  drawnLayers.push(label);

  map.fitBounds(L.latLngBounds(chosen.coordinates), { padding: [36, 36] });
}

function renderRouteList(routes) {
  const listEl = document.getElementById("route-list");
  const countEl = document.getElementById("route-count-label");
  countEl.textContent =
    routes.length === 1 ? "One route available" : `${routes.length} routes available`;
  listEl.innerHTML = "";

  const ordered = [...routes].sort((a, b) => a.duration_min - b.duration_min);

  ordered.forEach((route) => {
    const idx = routes.indexOf(route);
    const isSelected = idx === selectedRouteIndex;

    const card = document.createElement("div");
    card.className = `route-card ${isSelected ? "selected" : ""}`;
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline;">
        <span class="num" style="font-size:1.35rem;">${route.duration_min}<span style="font-size:.8rem;font-weight:500;margin-left:2px;">min</span></span>
        <span class="num" style="font-size:.9rem;color:rgb(var(--muted));">${route.distance_km} km</span>
      </div>
      <div style="margin-top:.35rem;font-size:.8rem;color:rgb(var(--muted));">
        ${isSelected ? "Showing on map" : "Tap to preview"}
      </div>
    `;
    card.addEventListener("click", () => selectRoute(idx));
    listEl.appendChild(card);
  });
}

function selectRoute(index) {
  selectedRouteIndex = index;
  const { routes, startCoords, endCoords } = routeState;
  drawRoutesOnMap(routes, startCoords, endCoords);
  renderRouteList(routes);
  loadRouteHealthScore(routes[index]);
}

async function loadRouteHealthScore(route) {
  const box = document.getElementById("route-health-box");
  const coords = route.coordinates;
  const mid = coords[Math.floor(coords.length / 2)];

  const res = await fetch(`${API_BASE_URL}/api/route-health-score?lat=${mid[0]}&lon=${mid[1]}`);
  const data = await res.json();

  if (!data.available) {
    box.style.display = "none";
    return;
  }

  const health = 100 - data.priority_score;
  const tone = health >= 70 ? "go" : health >= 40 ? "wait" : "stop";

  box.style.display = "";
  box.className = "sign rise";
  box.style.padding = "1.5rem";
  box.style.marginTop = "1.5rem";
  box.innerHTML = `
    <div style="display:flex;flex-wrap:wrap;gap:2rem;align-items:center;">
      <div style="text-align:center;min-width:120px;">
        <div class="num" style="font-size:3.4rem;line-height:1;color:rgb(var(--${tone}));">${health}</div>
        <div style="font-size:.8rem;color:rgb(var(--muted));margin-top:.2rem;">route health</div>
      </div>
      <div style="flex:1;min-width:220px;">
        <h3 style="font-size:1.25rem;margin-bottom:.5rem;">Conditions along this route</h3>
        <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.7rem;">
          <span class="chip chip-${
            data.traffic_level === "Low" ? "go" : data.traffic_level === "Medium" ? "wait" : "stop"
          }">${data.traffic_level} traffic</span>
          <span class="chip chip-${
            data.damage_level === "None" || data.damage_level === "Minor"
              ? "go"
              : data.damage_level === "Moderate"
              ? "wait"
              : "stop"
          }">${data.damage_level} road damage</span>
        </div>
        <p style="margin:0;font-size:.85rem;color:rgb(var(--muted));">
          Read from the nearest monitoring point: ${data.name}
        </p>
      </div>
    </div>
  `;
}

async function handleFindRoute() {
  const startPlace = document.getElementById("start-input").value.trim();
  const endPlace = document.getElementById("end-input").value.trim();
  const statusEl = document.getElementById("status-message");

  if (!startPlace || !endPlace) {
    statusEl.innerHTML = `<span style="color:rgb(var(--wait));">Enter both a starting point and a destination.</span>`;
    return;
  }

  statusEl.innerHTML = `<span style="color:rgb(var(--muted));">Looking up locations…</span>`;

  const startCoords = await searchLocation(startPlace);
  const endCoords = await searchLocation(endPlace);

  if (!startCoords) {
    statusEl.innerHTML = `<span style="color:rgb(var(--stop));">No match for “${startPlace}”. Try adding the city name.</span>`;
    return;
  }
  if (!endCoords) {
    statusEl.innerHTML = `<span style="color:rgb(var(--stop));">No match for “${endPlace}”. Try adding the city name.</span>`;
    return;
  }

  statusEl.innerHTML = `<span style="color:rgb(var(--muted));">Building routes…</span>`;

  const routes = await fetchRoutes(startCoords, endCoords, selectedMode);

  if (!routes || routes.length === 0) {
    statusEl.innerHTML = `<span style="color:rgb(var(--stop));">No road route connects these two points.</span>`;
    return;
  }

  statusEl.innerHTML = "";
  selectedRouteIndex = 0;
  routeState = { routes, startCoords, endCoords };

  const results = document.getElementById("results-section");
  results.style.display = "";
  results.classList.add("rise");

  setTimeout(() => {
    map.invalidateSize();
    drawRoutesOnMap(routes, startCoords, endCoords);
    renderRouteList(routes);
    loadRouteHealthScore(routes[0]);
  }, 80);
}

function setupModePills() {
  const pills = document.querySelectorAll(".mode-pill");
  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      pills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      selectedMode = pill.dataset.mode;
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  document.getElementById("find-route-btn").addEventListener("click", handleFindRoute);
  ["start-input", "end-input"].forEach((id) => {
    document.getElementById(id).addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleFindRoute();
    });
  });
  setupModePills();
});
