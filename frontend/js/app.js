/**
 * app.js
 * Shared configuration and helpers used by every page.
 */

const API_BASE_URL = "http://localhost:8000";

/** Posts an image file to a detection endpoint and returns the parsed result. */
async function callDetectionAPI(endpoint, imageFile) {
  const formData = new FormData();
  formData.append("file", imageFile);

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) throw new Error("API request failed");
  return await response.json();
}

/** Turns a base64 string from the API into something an <img> can display. */
function base64ToImageSrc(base64String) {
  return `data:image/jpeg;base64,${base64String}`;
}

/**
 * Counts a number up from zero. Used once per page, on the figure that
 * matters most, so the motion points at the result rather than decorating.
 */
function countUp(el, target, duration = 900) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.textContent = target;
    return;
  }
  const start = performance.now();
  function tick(now) {
    const p = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(target * eased);
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/**
 * If someone is already signed in as authority, the nav link takes them
 * straight to the dashboard instead of back to the sign-in form.
 */
function updateAuthorityNavLink() {
  const link = document.getElementById("authority-nav-link");
  if (!link) return;

  const authData = localStorage.getItem("auth_user");
  if (!authData) return;

  try {
    const user = JSON.parse(authData);
    if (user.role === "admin") {
      link.href = "authority.html";
      link.textContent = "Authority dashboard";
    }
  } catch (e) {
    /* stored value unreadable — leave the sign-in link as it is */
  }
}

/** Loads sample images from the backend so the demo folder stays the source of truth. */
async function loadSampleImages(containerId, keyword, onPick) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/samples`);
    const data = await res.json();
    const matches = data.samples.filter((n) => n.toLowerCase().includes(keyword));

    matches.forEach((filename) => {
      const img = document.createElement("img");
      img.src = `${API_BASE_URL}/api/samples/${encodeURIComponent(filename)}`;
      img.className = "thumb";
      img.alt = filename;
      img.addEventListener("click", async () => {
        const response = await fetch(img.src, { cache: "no-store" });
        const blob = await response.blob();
        onPick(new File([blob], filename, { type: blob.type }));
      });
      container.appendChild(img);
    });
  } catch (err) {
    console.error("Sample images unavailable:", err);
  }
}

document.addEventListener("DOMContentLoaded", updateAuthorityNavLink);
