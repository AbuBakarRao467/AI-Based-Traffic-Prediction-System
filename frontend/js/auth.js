/**
 * auth.js
 * Session handling for the authority-only area.
 */

function getCurrentUser() {
  const raw = localStorage.getItem("auth_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

function logout() {
  localStorage.removeItem("auth_user");
  window.location.href = "login.html";
}

function renderUserChip(user) {
  const el = document.getElementById("user-info");
  if (!el || !user) return;
  el.innerHTML = `
    <span style="font-size:.9rem;color:rgb(var(--muted));">${user.name}</span>
    <button onclick="logout()" class="btn btn-ghost" style="padding:.35rem .8rem;font-size:.85rem;">
      Sign out
    </button>
  `;
}
