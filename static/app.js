const API = "/api";

function getToken() {
    return localStorage.getItem("token");
}

function getUser() {
    const u = localStorage.getItem("user");
    return u ? JSON.parse(u) : null;
}

function setAuth(data) {
    localStorage.setItem("token", data.access_token);
}

function clearAuth() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
}

function logout() {
    clearAuth();
    window.location.href = "/";
}

async function api(path, options = {}) {
    const token = getToken();
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API}${path}`, { ...options, headers });
    if (res.status === 401) { logout(); return null; }
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
}

function showToast(msg, type = "success") {
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

function formatDate(d) {
    if (!d) return "-";
    return new Date(d).toLocaleDateString("en-US", {
        month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit"
    });
}

function statusBadge(s) {
    return `<span class="badge badge-${s}">${s.replace("_", " ")}</span>`;
}

function priorityBadge(p) {
    return `<span class="badge badge-${p}">${p}</span>`;
}
