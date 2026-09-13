import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Documents() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const { user } = useAuth();

  async function loadDocuments() {
    try {
      const res = await api.get("/documents/");
      setDocuments(res.data);
    } catch (err) {
      setError("Could not load documents.");
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      await api.post("/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      await loadDocuments();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this document?")) return;
    try {
      await api.delete(`/documents/${id}`);
      await loadDocuments();
    } catch (err) {
      setError("Delete failed.");
    }
  }

  const statusColor = {
    ready: "bg-green-100 text-green-700",
    processing: "bg-yellow-100 text-yellow-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <h1 className="font-bold text-slate-800">Documents</h1>
        <Link to="/chat" className="text-blue-600 hover:underline text-sm">
          Back to chat
        </Link>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        {user?.role === "admin" && (
          <div className="mb-6">
            <label className="inline-block bg-blue-600 text-white rounded-lg px-4 py-2 font-medium cursor-pointer hover:bg-blue-700">
              {uploading ? "Uploading..." : "Upload PDF"}
              <input
                type="file"
                accept="application/pdf"
                onChange={handleUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>
            {uploading && (
              <p className="text-sm text-slate-500 mt-2">
                First upload may take a minute (downloading the embedding model)...
              </p>
            )}
          </div>
        )}

        {error && <div className="bg-red-50 text-red-600 text-sm rounded-md p-2 mb-4">{error}</div>}

        <div className="bg-white rounded-lg shadow-sm divide-y divide-slate-100">
          {documents.length === 0 && (
            <p className="p-4 text-slate-400">No documents uploaded yet.</p>
          )}
          {documents.map((doc) => (
            <div key={doc.id} className="p-4 flex items-center justify-between">
              <div>
                <div className="font-medium text-slate-800">{doc.filename}</div>
                <div className="text-sm text-slate-400">
                  {doc.page_count} pages · {doc.char_count} chars
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs px-2 py-1 rounded-full ${statusColor[doc.status] || ""}`}>
                  {doc.status}
                </span>
                {user?.role === "admin" && (
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="text-red-500 text-sm hover:underline"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}