// Tiny fetch wrapper. Talks to /api (proxied to Django in dev) and attaches the
// JWT access token. Unwraps the backend's {status, message, data} envelope.

const BASE = import.meta.env.VITE_API_URL || "";

export function getToken() {
  return localStorage.getItem("access");
}

export function setSession(session) {
  localStorage.setItem("access", session.access);
  localStorage.setItem("refresh", session.refresh || "");
  localStorage.setItem("role", session.role || "");
  localStorage.setItem("email", session.email || "");
  localStorage.setItem("tenant_id", session.tenant_id ?? "");
  localStorage.setItem("is_superuser", session.is_superuser ? "1" : "");
}

export function clearSession() {
  ["access", "refresh", "role", "email", "tenant_id", "is_superuser"].forEach(
    (k) => localStorage.removeItem(k)
  );
}

export function currentUser() {
  const access = getToken();
  if (!access) return null;
  return {
    role: localStorage.getItem("role"),
    email: localStorage.getItem("email"),
    tenant_id: localStorage.getItem("tenant_id"),
    is_superuser: localStorage.getItem("is_superuser") === "1",
  };
}

export async function api(path, { method = "GET", body, auth = true } = {}) {
  // FormData (file upload) must go as multipart: let the browser set the
  // Content-Type + boundary itself, and send the object as-is (no JSON).
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const headers = {};
  if (!isForm) headers["Content-Type"] = "application/json";
  if (auth && getToken()) headers.Authorization = `Bearer ${getToken()}`;
  const res = await fetch(`${BASE}/api${path}`, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });
  let payload = {};
  try {
    payload = await res.json();
  } catch (_) {
    /* empty body */
  }
  if (!res.ok) {
    const err = new Error(payload?.message || `Request failed (${res.status})`);
    err.status = res.status;
    err.payload = payload;
    throw err;
  }
  return payload;
}

export const ROLES = {
  ORG_ADMIN: "ORG_ADMIN",
  TEACHER: "TEACHER",
  MENTOR: "MENTOR",
  PARENT: "PARENT",
  STUDENT: "STUDENT",
  CANDIDATE: "CANDIDATE",
};

export const isLearner = (role) => role === "STUDENT" || role === "CANDIDATE";
export const isObserver = (role) =>
  ["TEACHER", "MENTOR", "ORG_ADMIN", "PARENT"].includes(role);
export const canUpload = (role) =>
  ["TEACHER", "MENTOR", "ORG_ADMIN"].includes(role);
// Only org-admins may create/manage users within their own tenant.
export const canManageUsers = (role) => role === "ORG_ADMIN";
// Platform superadmin: onboards organizations (tenants) only.
export const isSuperAdmin = (user) => !!(user && user.is_superuser);
