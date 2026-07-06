import { useEffect, useState } from "react";
import Login from "./components/Login.jsx";
import Upload from "./components/Upload.jsx";
import DocumentList from "./components/DocumentList.jsx";
import Chat from "./components/Chat.jsx";
import { deleteDocument, listDocuments, uploadDocument } from "./api.js";

const TOKEN_KEY = "docsift_token";
const EMAIL_KEY = "docsift_email";

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));
  const [email, setEmail] = useState(() => sessionStorage.getItem(EMAIL_KEY) || "");
  const [documents, setDocuments] = useState([]);
  const [activeDocument, setActiveDocument] = useState(null); // null = search all
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  useEffect(() => {
    if (token) refreshDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function refreshDocuments() {
    try {
      const docs = await listDocuments(token);
      setDocuments(docs);
    } catch (err) {
      if (err.message?.toLowerCase().includes("credentials")) handleLogout();
    }
  }

  function handleAuthenticated(newToken, newEmail) {
    sessionStorage.setItem(TOKEN_KEY, newToken);
    sessionStorage.setItem(EMAIL_KEY, newEmail);
    setToken(newToken);
    setEmail(newEmail);
  }

  function handleLogout() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(EMAIL_KEY);
    setToken(null);
    setDocuments([]);
    setActiveDocument(null);
  }

  async function handleUpload(file) {
    setUploading(true);
    setUploadError("");
    try {
      await uploadDocument(token, file);
      await refreshDocuments();
    } catch (err) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(documentId) {
    await deleteDocument(token, documentId);
    if (activeDocument === documentId) setActiveDocument(null);
    await refreshDocuments();
  }

  if (!token) {
    return <Login onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">
          <span className="brand-mark" />
          <h1>Docs Semantic Search</h1>
          <span className="tag">RAG Based</span>
        </div>
        <div className="user-chip">
          <span>{email}</span>
          <button className="link-btn" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>

      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-section">
            <h2>Upload</h2>
            <Upload onFileSelected={handleUpload} disabled={uploading} />
            {uploadError && <div className="auth-error" style={{ marginTop: 8 }}>{uploadError}</div>}
          </div>
          <div className="sidebar-section" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, borderBottom: "none" }}>
            <h2>Documents</h2>
            <DocumentList
              documents={documents}
              activeId={activeDocument}
              onSelect={setActiveDocument}
              onDelete={handleDelete}
            />
          </div>
        </aside>

        <Chat token={token} activeDocument={activeDocument} documents={documents} />
      </div>
    </div>
  );
}
