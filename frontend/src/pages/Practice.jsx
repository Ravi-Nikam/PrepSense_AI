import { useEffect, useRef, useState } from "react";
import { api } from "../api";

// Learner practice, two steps:
//   1) pick a PAPER (material) to attempt
//   2) answer the questions in that paper
export default function Practice() {
  const [list, setList] = useState([]);
  const [paperId, setPaperId] = useState(null); // selected paper (material) id
  const [active, setActive] = useState(null); // the question being answered
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const answerRef = useRef(null); // scroll the answer panel into view on pick

  async function loadList() {
    try {
      const res = await api("/practice/questions/");
      setList(res.data || []);
    } catch (err) {
      setStatus(err.message);
    }
  }
  useEffect(() => {
    loadList();
  }, []);

  // Group questions by paper (material).
  const papers = {};
  for (const q of list) {
    (papers[q.material_id] ||= {
      material_id: q.material_id,
      subject_or_role: q.subject_or_role,
      topic: q.topic,
      mode: q.mode,
      questions: [],
    }).questions.push(q);
  }
  const paperList = Object.values(papers);
  const paper = papers[paperId];

  function openPaper(id) {
    setPaperId(id);
    setActive(null);
    setAnswer("");
    setResult(null);
    setStatus("");
  }
  function pick(q) {
    setActive(q);
    setAnswer("");
    setResult(null);
    setStatus("");
    // Bring the answer box into view (matters on mobile / long lists).
    requestAnimationFrame(() =>
      answerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    );
  }

  async function submit() {
    if (!answer.trim() || !active) return;
    setBusy(true);
    setStatus("Submitting…");
    try {
      const res = await api("/attempts/", {
        method: "POST",
        body: { question: active.id, submitted_answer: answer },
      });
      const attemptId = res.data.id;
      setStatus("Grading…");
      let graded = null;
      for (let i = 0; i < 5 && !graded; i++) {
        await new Promise((r) => setTimeout(r, 600));
        const a = await api(`/attempts/${attemptId}/`);
        if (a.data.is_graded) graded = a.data;
      }
      setResult(graded || { pending: true });
      setStatus("");
      loadList();
    } catch (err) {
      setStatus(err.message);
    } finally {
      setBusy(false);
    }
  }

  // -------- Step 1: choose a paper --------
  if (!paper) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <h2 className="text-xl font-semibold">Choose a paper</h2>
        {status && <p className="text-sm text-red-600">{status}</p>}
        {paperList.length === 0 && (
          <p className="text-sm text-slate-500">No papers available yet.</p>
        )}
        {paperList.map((p) => {
          const done = p.questions.filter((q) => q.attempted).length;
          return (
            <div
              key={p.material_id}
              className="bg-white rounded-2xl shadow px-5 py-4 flex items-center justify-between"
            >
              <div>
                <div className="font-medium">
                  {p.subject_or_role} — {p.topic}
                </div>
                <div className="text-xs text-slate-500">
                  {p.mode} · {p.questions.length} questions · {done} answered
                </div>
              </div>
              <button
                onClick={() => openPaper(p.material_id)}
                className="rounded-lg bg-slate-900 text-white px-4 py-2 text-sm"
              >
                {done > 0 ? "Continue" : "Start"}
              </button>
            </div>
          );
        })}
      </div>
    );
  }

  // -------- Step 2: answer the chosen paper --------
  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <button
        onClick={() => setPaperId(null)}
        className="text-sm text-slate-500 hover:text-slate-800"
      >
        ← Back to papers
      </button>
      <h2 className="text-xl font-semibold">
        {paper.subject_or_role} — {paper.topic}
      </h2>

      <div className="grid md:grid-cols-2 gap-6 items-start">
        {/* Left: pick a question in this paper — scrolls within its own box */}
        <div className="bg-white rounded-2xl shadow p-4 space-y-1 md:max-h-[75vh] md:overflow-y-auto">
          {paper.questions.map((q, i) => (
            <button
              key={q.id}
              onClick={() => pick(q)}
              className={`w-full text-left rounded-lg px-3 py-2 text-sm flex gap-2 items-start ${
                active?.id === q.id ? "bg-slate-900 text-white" : "hover:bg-slate-100"
              }`}
            >
              <span
                className={active?.id === q.id ? "text-slate-300" : "text-slate-400"}
              >
                {q.attempted ? "✓" : i + 1}
              </span>
              <span className="flex-1 line-clamp-2">{q.question_text}</span>
            </button>
          ))}
        </div>

        {/* Right: answer — sticks in view while the question list scrolls */}
        <div ref={answerRef} className="md:sticky md:top-4 scroll-mt-4">
          {!active ? (
            <div className="bg-white rounded-2xl shadow p-6 text-slate-500 text-sm">
              Pick a question on the left to answer it.
            </div>
          ) : (
            <div className="bg-white rounded-2xl shadow p-6 space-y-4">
              <div className="flex gap-2 text-xs">
                <span className="rounded-full bg-slate-100 px-2 py-0.5">
                  {active.topic_or_category}
                </span>
                {active.difficulty && (
                  <span className="rounded-full bg-amber-100 text-amber-800 px-2 py-0.5">
                    {active.difficulty}
                  </span>
                )}
                {active.category && (
                  <span className="rounded-full bg-indigo-100 text-indigo-800 px-2 py-0.5">
                    {active.category}
                  </span>
                )}
                {active.attempted && !result && (
                  <span className="rounded-full bg-green-100 text-green-800 px-2 py-0.5">
                    already answered
                  </span>
                )}
              </div>
              <p className="text-lg">{active.question_text}</p>

              <textarea
                className="w-full rounded-lg border border-slate-300 px-3 py-2 h-32"
                placeholder="Type your answer…"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                disabled={busy || !!result}
              />

              {!result && (
                <button
                  onClick={submit}
                  disabled={busy || !answer.trim()}
                  className="rounded-lg bg-slate-900 text-white px-4 py-2 disabled:opacity-50"
                >
                  Submit answer
                </button>
              )}

              {result && !result.pending && (
                <div className="rounded-xl border border-slate-200 p-4 space-y-2">
                  <div className="text-2xl font-bold">
                    Score: {result.score}
                    <span className="text-base font-normal text-slate-400">/100</span>
                  </div>
                  <p className="text-slate-700">{result.feedback}</p>
                  <button
                    onClick={() => setActive(null)}
                    className="rounded-lg bg-slate-900 text-white px-4 py-2"
                  >
                    Pick another
                  </button>
                </div>
              )}
              {result?.pending && (
                <p className="text-sm text-slate-500">
                  Submitted — grading still in progress.
                </p>
              )}
              {status && <p className="text-sm text-slate-500">{status}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
