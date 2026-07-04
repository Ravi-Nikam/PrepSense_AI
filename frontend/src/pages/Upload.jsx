import { useEffect, useState } from "react";
import { api } from "../api";

// Teacher/mentor: upload source material and trigger grounded question generation.
export default function Upload() {
  const [mode, setMode] = useState("INTERVIEW");
  const [subject, setSubject] = useState("Backend Engineer");
  const [topic, setTopic] = useState("System Design");
  const [text, setText] = useState(
    "The backend engineer designs scalable services: API design, caching, rate limiting."
  );
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [materials, setMaterials] = useState([]);
  // Which material's questions are expanded, and the fetched questions for it.
  const [openId, setOpenId] = useState(null);
  const [questions, setQuestions] = useState([]);
  // Inline editing of a single question.
  const [editId, setEditId] = useState(null);
  const [editText, setEditText] = useState("");
  const [editRef, setEditRef] = useState("");

  async function load() {
    try {
      const res = await api("/materials/");
      setMaterials(res.results || res.data || []);
    } catch (err) {
      setStatus(err.message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function create(e) {
    e.preventDefault();
    if (mode === "EXAM" && !file) {
      setStatus("Exam mode requires a PDF file.");
      return;
    }
    setStatus("Uploading…");
    try {
      // A PDF is sent as multipart/form-data; otherwise a plain JSON body.
      let body;
      if (file) {
        body = new FormData();
        body.append("mode", mode);
        body.append("subject_or_role", subject);
        body.append("topic", topic);
        body.append("file", file);
        if (text) body.append("source_text", text);
      } else {
        body = { mode, subject_or_role: subject, topic, source_text: text };
      }
      await api("/materials/", { method: "POST", body });
      setStatus("Uploaded. Ingestion queued.");
      setFile(null);
      load();
    } catch (err) {
      setStatus(err.message);
    }
  }

  async function generate(id) {
    setStatus("Generating a 100-question paper… (this can take a minute)");
    try {
      const res = await api(`/materials/${id}/generate/`, {
        method: "POST",
        body: { count: 100 },
      });
      const created = res.data?.created;
      setStatus(
        created != null
          ? `Paper ready: ${created} question(s) generated.`
          : "Question generation done."
      );
      // Show the freshly generated questions (works immediately with eager tasks).
      viewQuestions(id, true);
    } catch (err) {
      setStatus(`${err.message}` + (err.status === 429 ? " (daily LLM cap reached)" : ""));
    }
  }

  async function viewQuestions(id, force = false) {
    // Toggle closed if already open (unless we just generated).
    if (openId === id && !force) {
      setOpenId(null);
      return;
    }
    setStatus("");
    setEditId(null);
    try {
      const res = await api(`/questions/?source_material=${id}&page_size=100`);
      setQuestions(res.results || res.data || []);
      setOpenId(id);
    } catch (err) {
      setStatus(err.message);
    }
  }

  function startEdit(q) {
    setEditId(q.id);
    setEditText(q.question_text);
    setEditRef(q.reference_answer || "");
  }

  async function saveEdit(q) {
    try {
      const res = await api(`/questions/${q.id}/`, {
        method: "PATCH",
        body: { question_text: editText, reference_answer: editRef },
      });
      // Swap the edited question in place with the server's response.
      setQuestions((qs) => qs.map((x) => (x.id === q.id ? res.data : x)));
      setEditId(null);
      setStatus("Question updated.");
    } catch (err) {
      setStatus(err.message);
    }
  }

  async function deleteQuestion(q) {
    if (!confirm("Delete this question?")) return;
    try {
      await api(`/questions/${q.id}/`, { method: "DELETE" });
      setQuestions((qs) => qs.filter((x) => x.id !== q.id));
      setStatus("Question deleted.");
    } catch (err) {
      setStatus(err.message);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-xl font-semibold">Upload material</h2>

      <form onSubmit={create} className="bg-white rounded-2xl shadow p-6 space-y-3">
        <div className="flex gap-3">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            <option value="INTERVIEW">Interview (job description)</option>
            <option value="EXAM">Exam (chapter text)</option>
          </select>
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder={mode === "EXAM" ? "Subject" : "Role"}
          />
          <input
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Topic"
          />
        </div>
        <textarea
          className="w-full rounded-lg border border-slate-300 px-3 py-2 h-32"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            mode === "EXAM" ? "Paste chapter text…" : "Paste job description / role skills…"
          }
        />
        <div className="space-y-1">
          <label className="block text-sm font-medium text-slate-700">
            {mode === "EXAM" ? "PDF chapter (required)" : "PDF (optional)"}
          </label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-slate-700 hover:file:bg-slate-200"
          />
          {file && (
            <p className="text-xs text-slate-500">
              Selected: {file.name} ({Math.round(file.size / 1024)} KB)
            </p>
          )}
        </div>
        <button className="rounded-lg bg-slate-900 text-white px-4 py-2">
          Upload &amp; ingest
        </button>
        {status && <p className="text-sm text-slate-500">{status}</p>}
      </form>

      <div>
        <h3 className="font-medium mb-2">Your materials</h3>
        <div className="space-y-2">
          {materials.map((m) => (
            <div key={m.id} className="bg-white rounded-xl shadow">
              <div className="px-4 py-3 flex items-center justify-between">
                <div>
                  <div className="font-medium">
                    {m.subject_or_role} — {m.topic || "general"}
                  </div>
                  <div className="text-xs text-slate-500">
                    {m.mode} · status: {m.ingestion_status}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => viewQuestions(m.id)}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                  >
                    {openId === m.id ? "Hide questions" : "View questions"}
                  </button>
                  <button
                    onClick={() => generate(m.id)}
                    disabled={m.ingestion_status !== "READY"}
                    className="rounded-lg bg-slate-900 text-white px-3 py-1.5 text-sm disabled:opacity-40"
                  >
                    Generate paper (100 Q)
                  </button>
                </div>
              </div>

              {openId === m.id && (
                <div className="border-t border-slate-100 px-4 py-3 space-y-3">
                  {questions.length === 0 && (
                    <p className="text-sm text-slate-500">
                      No questions yet — click “Generate questions”.
                    </p>
                  )}
                  {questions.map((q, i) => (
                    <div key={q.id} className="text-sm">
                      <div className="flex gap-2 items-start">
                        <span className="text-slate-400">{i + 1}.</span>
                        <div className="flex-1">
                          {editId === q.id ? (
                            <div className="space-y-2">
                              <textarea
                                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                placeholder="Question"
                              />
                              <textarea
                                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                                value={editRef}
                                onChange={(e) => setEditRef(e.target.value)}
                                placeholder="Reference answer"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={() => saveEdit(q)}
                                  className="rounded-lg bg-slate-900 text-white px-3 py-1 text-xs"
                                >
                                  Save
                                </button>
                                <button
                                  onClick={() => setEditId(null)}
                                  className="rounded-lg border border-slate-300 px-3 py-1 text-xs"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <p className="font-medium text-slate-800">
                                {q.question_text}
                              </p>
                              {q.reference_answer && (
                                <p className="mt-1 text-slate-500">
                                  <span className="font-medium text-slate-600">
                                    Reference:
                                  </span>{" "}
                                  {q.reference_answer}
                                </p>
                              )}
                              <div className="mt-1 flex gap-2 items-center text-xs">
                                <span className="rounded-full bg-slate-100 px-2 py-0.5">
                                  {q.topic_or_category}
                                </span>
                                {q.difficulty && (
                                  <span className="rounded-full bg-amber-100 text-amber-800 px-2 py-0.5">
                                    {q.difficulty}
                                  </span>
                                )}
                                {q.category && (
                                  <span className="rounded-full bg-indigo-100 text-indigo-800 px-2 py-0.5">
                                    {q.category}
                                  </span>
                                )}
                                <button
                                  onClick={() => startEdit(q)}
                                  className="text-slate-600 underline ml-auto"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => deleteQuestion(q)}
                                  className="text-red-600 underline"
                                >
                                  Delete
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {materials.length === 0 && (
            <p className="text-sm text-slate-500">No materials yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
