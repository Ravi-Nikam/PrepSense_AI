import { useEffect, useState } from "react";
import { api, ROLES } from "../api";

// Org-admin only: create + manage users within the admin's own tenant.
// Backed by /api/users/ (POST create, GET list, DELETE = deactivate).
const ROLE_OPTIONS = [
  ROLES.TEACHER,
  ROLES.MENTOR,
  ROLES.PARENT,
  ROLES.STUDENT,
  ROLES.CANDIDATE,
  ROLES.ORG_ADMIN,
];

const EMPTY = { email: "", full_name: "", role: ROLES.STUDENT, password: "" };

export default function Users() {
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState("");
  const [users, setUsers] = useState([]);

  async function load() {
    try {
      const res = await api("/users/");
      setUsers(res.results || res.data || []);
    } catch (err) {
      setStatus(err.message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function create(e) {
    e.preventDefault();
    setStatus("Creating…");
    try {
      await api("/users/", { method: "POST", body: form });
      setStatus("User created.");
      setForm(EMPTY);
      load();
    } catch (err) {
      // Surface field errors (e.g. duplicate email / weak password) if present.
      const detail = err.payload && typeof err.payload === "object"
        ? Object.values(err.payload).flat().join(" ")
        : "";
      setStatus(detail ? `${err.message}: ${detail}` : err.message);
    }
  }

  async function resetPassword(id, email) {
    const pw = prompt(`New password for ${email}:`);
    if (!pw) return;
    try {
      await api(`/users/${id}/password/`, {
        method: "POST",
        body: { password: pw },
      });
      setStatus(`Password updated for ${email}.`);
    } catch (err) {
      setStatus(err.message);
    }
  }

  async function deactivate(id) {
    if (!confirm("Deactivate this user?")) return;
    try {
      await api(`/users/${id}/`, { method: "DELETE" });
      load();
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-xl font-semibold">Users</h2>

      <form onSubmit={create} className="bg-white rounded-2xl shadow p-6 space-y-3">
        <div className="flex gap-3">
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            type="email"
            required
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            placeholder="Email"
          />
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            placeholder="Full name"
          />
        </div>
        <div className="flex gap-3">
          <select
            value={form.role}
            onChange={(e) => set("role", e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            {ROLE_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            type="password"
            required
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            placeholder="Password"
          />
        </div>
        <button className="rounded-lg bg-slate-900 text-white px-4 py-2">
          Create user
        </button>
        {status && <p className="text-sm text-slate-500">{status}</p>}
      </form>

      <div>
        <h3 className="font-medium mb-2">Your users</h3>
        <div className="bg-white rounded-2xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2">Name</th>
                <th className="text-left px-4 py-2">Email</th>
                <th className="text-left px-4 py-2">Role</th>
                <th className="text-left px-4 py-2">Active</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="px-4 py-2">{u.full_name || "—"}</td>
                  <td className="px-4 py-2">{u.email}</td>
                  <td className="px-4 py-2">{u.role_display || u.role}</td>
                  <td className="px-4 py-2">{u.is_active ? "Yes" : "No"}</td>
                  <td className="px-4 py-2 text-right space-x-3">
                    <button
                      onClick={() => resetPassword(u.id, u.email)}
                      className="text-slate-900 underline"
                    >
                      Reset password
                    </button>
                    {u.is_active && (
                      <button
                        onClick={() => deactivate(u.id)}
                        className="text-red-600 underline"
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan="5" className="px-4 py-6 text-center text-slate-500">
                    No users yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
