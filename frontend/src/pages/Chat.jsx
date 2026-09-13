import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Link } from "react-router-dom";

export default function Chat() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]); // {question, answer, sources, loading}
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(""); // "" = search all documents
  const { user, logout } = useAuth();

  async function loadHistory() {
    try {
      const res = await api.get("/query/history");
      setHistory(res.data);
    } catch (err) {
      console.error("Failed to load chat history", err);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function loadDocuments() {
    try {
      const res = await api.get("/documents/");
      setDocuments(res.data.filter((d) => d.status === "ready"));
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  }

  useEffect(() => {
    loadHistory();
    loadDocuments();
  }, []);

  function startNewChat() {
    setMessages([]);
  }

  function openHistoryEntry(entry) {
    // /query/history doesn't store sources, only question+answer — so past
    // entries render without citations. That's a real limitation, not a bug:
    // sources would need to be persisted in chat_history to show here too.
    setMessages([
      {
        id: entry.id,
        question: entry.question,
        answer: entry.answer,
        sources: [],
        loading: false,
      },
    ]);
  }

  async function handleAsk(e) {
    e.preventDefault();
    if (!question.trim()) return;

    const q = question;
    setQuestion("");
    const tempId = Date.now();
    setMessages((prev) => [...prev, { id: tempId, question: q, loading: true }]);

    try {
      const res = await api.post("/query", {
        question: q,
        document_id: selectedDocId || null,
      });
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? { ...m, loading: false, answer: res.data.answer, sources: res.data.sources }
            : m
        )
      );
      loadHistory(); // refresh sidebar so the new question appears
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === tempId
            ? {
                ...m,
                loading: false,
                answer: err.response?.data?.detail || "Something went wrong.",
                sources: [],
                isError: true,
              }
            : m
        )
      );
    }
  }

  return (
    <div className="h-screen bg-slate-50 flex flex-col">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <h1 className="font-bold text-slate-800">DocuMind AI</h1>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-slate-500">{user?.name} ({user?.role})</span>
          {user?.role === "admin" && (
            <Link to="/documents" className="text-blue-600 hover:underline">
              Manage documents
            </Link>
          )}
          <button onClick={logout} className="text-slate-500 hover:text-slate-800">
            Log out
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
          <div className="p-3 border-b border-slate-100">
            <button
              onClick={startNewChat}
              className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md py-2 text-sm font-medium"
            >
              + New question
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {historyLoading && (
              <p className="text-slate-400 text-sm p-3">Loading history...</p>
            )}
            {!historyLoading && history.length === 0 && (
              <p className="text-slate-400 text-sm p-3">No past questions yet.</p>
            )}
            {history.map((h) => (
              <button
                key={h.id}
                onClick={() => openHistoryEntry(h)}
                className="w-full text-left px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 border-b border-slate-50 truncate"
                title={h.question}
              >
                {h.question}
              </button>
            ))}
          </div>
        </aside>

        {/* Main chat area */}
        <div className="flex-1 flex flex-col">
          <main className="flex-1 overflow-y-auto px-6 py-6 space-y-6 max-w-3xl mx-auto w-full">
            {messages.length === 0 && (
              <p className="text-slate-400 text-center mt-20">
                Ask a question about any uploaded document.
              </p>
            )}

            {messages.map((m) => (
              <div key={m.id} className="space-y-2">
                <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-lg ml-auto">
                  {m.question}
                </div>

                <div
                  className={`rounded-lg px-4 py-3 max-w-xl ${
                    m.isError ? "bg-red-50 text-red-700" : "bg-white shadow-sm"
                  }`}
                >
                  {m.loading ? (
                    <span className="text-slate-400 italic">Thinking...</span>
                  ) : (
                    <>
                      <p className="text-slate-800">{m.answer}</p>
                      {m.sources && m.sources.length > 0 && (
                        <details className="mt-2 text-sm text-slate-500">
                          <summary className="cursor-pointer hover:text-slate-700">
                            {m.sources.length} source{m.sources.length > 1 ? "s" : ""}
                          </summary>
                          <ul className="mt-2 space-y-2">
                            {m.sources.map((s) => (
                              <li key={s.chunk_id} className="border-l-2 border-slate-200 pl-2">
                                <div className="font-medium text-slate-600">
                                  {s.filename} · score {s.score.toFixed(2)}
                                </div>
                                <div className="text-slate-400 line-clamp-2">{s.text}</div>
                              </li>
                            ))}
                          </ul>
                        </details>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </main>

          <form onSubmit={handleAsk} className="border-t border-slate-200 bg-white p-4">
            <div className="max-w-3xl mx-auto space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <label className="text-slate-500">Talking about:</label>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="border border-slate-300 rounded-md px-2 py-1 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All documents</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename}
                    </option>
                  ))}
                </select>
                {documents.length === 0 && (
                  <span className="text-slate-400">
                    No documents ready yet —{" "}
                    <Link to="/documents" className="text-blue-600 hover:underline">
                      upload one
                    </Link>
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask a question about your documents..."
                  className="flex-1 border border-slate-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  className="bg-blue-600 text-white rounded-lg px-5 py-2 font-medium hover:bg-blue-700"
                >
                  Ask
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}