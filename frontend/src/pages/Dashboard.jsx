import { useEffect, useState } from "react";
import { api } from "../api";

// Observer (teacher/mentor/parent) dashboard: learners + drill-down report.
export default function Dashboard() {
  const [rows, setRows] = useState([]);
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("");

  async function load() {
    try {
      const res = await api("/reports/dashboard/");
      setRows(res.data || []);
    } catch (err) {
      setStatus(err.message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function openReport(id) {
    setStatus("");
    try {
      const res = await api(`/reports/learner/${id}/`);
      setReport(res.data);
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-xl font-semibold">Dashboard</h2>
      {status && <p className="text-sm text-red-600">{status}</p>}

      <div className="bg-white rounded-2xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="text-left px-4 py-2">Learner</th>
              <th className="text-left px-4 py-2">Attempts</th>
              <th className="text-left px-4 py-2">Avg</th>
              <th className="text-left px-4 py-2">Trend</th>
              <th className="text-left px-4 py-2">Weak topics</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.learner.id} className="border-t border-slate-100">
                <td className="px-4 py-2">
                  {r.learner.full_name || r.learner.email}
                </td>
                <td className="px-4 py-2">{r.graded_attempts}</td>
                <td className="px-4 py-2">{r.overall_avg ?? "—"}</td>
                <td className="px-4 py-2">{r.trend}</td>
                <td className="px-4 py-2">{r.weak_topic_count}</td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => openReport(r.learner.id)}
                    className="text-slate-900 underline"
                  >
                    View report
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan="6" className="px-4 py-6 text-center text-slate-500">
                  No learners to show.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {report && (
        <div className="bg-white rounded-2xl shadow p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">
              {report.learner.full_name || report.learner.email}
            </h3>
            <button
              onClick={() => setReport(null)}
              className="text-sm text-slate-400"
            >
              close
            </button>
          </div>
          <div className="text-sm text-slate-500">
            Overall {report.summary.overall_avg ?? "—"} · trend{" "}
            {report.summary.trend}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <TopicColumn title="Strong" color="green" topics={report.topics.strong} />
            <TopicColumn title="Weak" color="red" topics={report.topics.weak} />
            <UntestedColumn topics={report.topics.untested} />
          </div>
        </div>
      )}
    </div>
  );
}

function TopicColumn({ title, color, topics }) {
  const badge =
    color === "green" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";
  return (
    <div>
      <h4 className="font-medium mb-2">{title}</h4>
      <div className="space-y-1">
        {topics.map((t) => (
          <div key={t.topic} className="flex justify-between text-sm">
            <span>{t.topic}</span>
            <span className={`rounded-full px-2 ${badge}`}>{t.avg_score}</span>
          </div>
        ))}
        {topics.length === 0 && <p className="text-xs text-slate-400">none</p>}
      </div>
    </div>
  );
}

function UntestedColumn({ topics }) {
  return (
    <div>
      <h4 className="font-medium mb-2">Untested</h4>
      <div className="space-y-1">
        {topics.map((t) => (
          <div key={t} className="text-sm text-slate-500">
            {t}
          </div>
        ))}
        {topics.length === 0 && <p className="text-xs text-slate-400">none</p>}
      </div>
    </div>
  );
}
