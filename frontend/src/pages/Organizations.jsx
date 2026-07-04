import { useEffect, useState } from "react";
import { api } from "../api";

// Platform superadmin only: onboard organizations (tenants). Backed by
// /api/organizations/ (superuser-gated on the backend).
const TYPE_OPTIONS = [
  ["SCHOOL", "School (exam prep)"],
  ["COMPANY", "Company (interview prep)"],
  ["INSTITUTE", "Coaching institute"],
  ["INDIVIDUAL", "Individual self-serve"],
];

const EMPTY = {
  name: "",
  type: "SCHOOL",
  email: "",
  phone: "",
  city: "",
  admin_email: "",
  admin_full_name: "",
  admin_password: "",
};

export default function Organizations() {
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState("");
  const [orgs, setOrgs] = useState([]);

  async function load() {
    try {
      const res = await api("/organizations/");
      setOrgs(res.results || res.data || []);
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
      await api("/organizations/", { method: "POST", body: form });
      setStatus("Organization created.");
      setForm(EMPTY);
      load();
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-xl font-semibold">Organizations</h2>

      <form onSubmit={create} className="bg-white rounded-2xl shadow p-6 space-y-3">
        <div className="flex gap-3">
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            required
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Organization name"
          />
          <select
            value={form.type}
            onChange={(e) => set("type", e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            {TYPE_OPTIONS.map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-3">
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            type="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            placeholder="Contact email (optional)"
          />
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            value={form.phone}
            onChange={(e) => set("phone", e.target.value)}
            placeholder="Phone (optional)"
          />
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            value={form.city}
            onChange={(e) => set("city", e.target.value)}
            placeholder="City (optional)"
          />
        </div>

        <div className="pt-2 border-t border-slate-100">
          <p className="text-sm font-medium text-slate-700 mb-2">
            First admin for this organization
          </p>
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
              type="email"
              required
              value={form.admin_email}
              onChange={(e) => set("admin_email", e.target.value)}
              placeholder="Admin email"
            />
            <input
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
              value={form.admin_full_name}
              onChange={(e) => set("admin_full_name", e.target.value)}
              placeholder="Admin name (optional)"
            />
            <input
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
              type="password"
              required
              value={form.admin_password}
              onChange={(e) => set("admin_password", e.target.value)}
              placeholder="Admin password"
            />
          </div>
        </div>

        <button className="rounded-lg bg-slate-900 text-white px-4 py-2">
          Add organization
        </button>
        {status && <p className="text-sm text-slate-500">{status}</p>}
      </form>

      <div>
        <h3 className="font-medium mb-2">All organizations</h3>
        <div className="bg-white rounded-2xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                <th className="text-left px-4 py-2">Name</th>
                <th className="text-left px-4 py-2">Type</th>
                <th className="text-left px-4 py-2">Users</th>
                <th className="text-left px-4 py-2">Active</th>
              </tr>
            </thead>
            <tbody>
              {orgs.map((o) => (
                <tr key={o.id} className="border-t border-slate-100">
                  <td className="px-4 py-2">{o.name}</td>
                  <td className="px-4 py-2">{o.type_display || o.type}</td>
                  <td className="px-4 py-2">{o.user_count ?? "—"}</td>
                  <td className="px-4 py-2">{o.is_active ? "Yes" : "No"}</td>
                </tr>
              ))}
              {orgs.length === 0 && (
                <tr>
                  <td colSpan="4" className="px-4 py-6 text-center text-slate-500">
                    No organizations yet.
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
