import { useState } from "react";
import {
  canManageUsers,
  canUpload,
  clearSession,
  currentUser,
  isLearner,
  isSuperAdmin,
} from "./api";
import Login from "./pages/Login";
import Practice from "./pages/Practice";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import Users from "./pages/Users";
import Organizations from "./pages/Organizations";
import StudentDashboard from "./pages/StudentDashboard";

export default function App() {
  const [user, setUser] = useState(currentUser());
  // Default tab depends on role: learners practise; observers see the dashboard.
  const [tab, setTab] = useState(null);

  if (!user) {
    return <Login onLogin={() => setUser(currentUser())} />;
  }

  // Platform superadmin only manages organizations — nothing else.
  const superAdmin = isSuperAdmin(user);
  const learner = isLearner(user.role);
  const active = superAdmin
    ? "organizations"
    : tab || (learner ? "practice" : "dashboard");

  const tabs = superAdmin
    ? [["organizations", "Organizations"]]
    : learner
    ? [
        ["practice", "Practice"],
        ["mymarks", "My marks"],
      ]
    : [
        ["dashboard", "Dashboard"],
        ...(canUpload(user.role) ? [["upload", "Upload material"]] : []),
        ...(canManageUsers(user.role) ? [["users", "Users"]] : []),
      ];

  function logout() {
    clearSession();
    setUser(null);
    setTab(null);
  }

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-bold text-lg">PrepCheck</span>
            <nav className="flex gap-1">
              {tabs.map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  className={`px-3 py-1.5 rounded-lg text-sm ${
                    active === key
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-500">
              {user.email}{" "}
              <span className="rounded-full bg-slate-100 px-2 py-0.5">
                {user.role}
              </span>
            </span>
            <button onClick={logout} className="text-slate-400 hover:text-slate-700">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {active === "practice" && <Practice />}
        {active === "dashboard" && <Dashboard />}
        {active === "upload" && <Upload />}
        {active === "users" && <Users />}
        {active === "organizations" && <Organizations />}
        {active === "mymarks" && <StudentDashboard />}
      </main>
    </div>
  );
}
