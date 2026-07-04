import { useEffect, useState } from "react";
import { api } from "../api";

// Learner's own marks sheet: each material is a paper scored out of 50.
export default function StudentDashboard() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("");

  async function load() {
    try {
      const res = await api("/reports/my-papers/");
      setData(res.data);
    } catch (err) {
      setStatus(err.message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  if (status) return <p className="text-sm text-red-600">{status}</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;

  const { summary, papers } = data;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-xl font-semibold">My marks</h2>

      <div className="bg-white rounded-2xl shadow p-6 flex items-center justify-between">
        <div>
          <div className="text-sm text-slate-500">Total across all papers</div>
          <div className="text-3xl font-bold">
            {summary.total_marks}
            <span className="text-lg font-normal text-slate-400">
              {" "}
              / {summary.total_possible}
            </span>
          </div>
        </div>
        <div className="text-sm text-slate-500">
          {summary.papers} paper{summary.papers === 1 ? "" : "s"}
        </div>
      </div>

      <div>
        <h3 className="font-medium mb-2">Your papers</h3>
        <div className="space-y-2">
          {papers.map((p) => (
            <div
              key={p.material_id}
              className="bg-white rounded-xl shadow px-4 py-3 flex items-center justify-between"
            >
              <div>
                <div className="font-medium">
                  {p.subject_or_role} — {p.topic}
                </div>
                <div className="text-xs text-slate-500">
                  {p.mode} · {p.answered}/{p.total_questions} answered
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">
                  {p.marks}
                  <span className="text-sm font-normal text-slate-400">
                    {" "}
                    / {p.total_marks}
                  </span>
                </div>
                <div className="text-xs text-slate-400">avg {p.avg_score}%</div>
              </div>
            </div>
          ))}
          {papers.length === 0 && (
            <p className="text-sm text-slate-500">
              No graded papers yet — answer some questions in Practice.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
