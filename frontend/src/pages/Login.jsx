import { useState } from "react";
import { api, setSession } from "../api";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("teacher@springfield.demo");
  const [password, setPassword] = useState("Prep@1234");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await api("/auth/login/", {
        method: "POST",
        auth: false,
        body: { email, password },
      });
      setSession(res.data);
      onLogin();
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm bg-white rounded-2xl shadow p-8 space-y-4"
      >
        <div>
          <h1 className="text-2xl font-bold">PrepCheck</h1>
          <p className="text-sm text-slate-500">Exam & interview preparation</p>
        </div>
        {error && (
          <div className="text-sm bg-red-50 text-red-700 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
        <label className="block text-sm">
          <span className="text-slate-600">Email</span>
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-600">Password</span>
          <input
            type="password"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button
          disabled={busy}
          className="w-full rounded-lg bg-slate-900 text-white py-2 font-medium hover:bg-slate-700 disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-xs text-slate-400">
          Demo users (password <code>Prep@1234</code>): teacher@springfield.demo,
          homer@springfield.demo, mentor@acme.demo, dana@acme.demo
        </p>
      </form>
    </div>
  );
}
