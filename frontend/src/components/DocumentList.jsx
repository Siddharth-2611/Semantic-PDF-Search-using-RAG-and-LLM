export default function DocumentList({ documents, activeId, onSelect, onDelete }) {
  if (documents.length === 0) {
    return <div className="empty-hint">No documents yet. Upload a PDF to get started.</div>;
  }

  return (
    <div className="doc-list">
      {/* "All documents" pseudo-item clears the active filter so chat searches everything */}
      <div
        className={`doc-item${activeId === null ? " active" : ""}`}
        onClick={() => onSelect(null)}
      >
        <span className="name">All documents</span>
        <span className="meta">Search across everything you've uploaded</span>
      </div>

      {documents.map((doc) => (
        <div
          key={doc.id}
          className={`doc-item${activeId === doc.id ? " active" : ""}`}
          onClick={() => onSelect(doc.id)}
        >
          <span className="name" title={doc.filename}>
            {doc.filename}
          </span>
          <span className="meta">
            <span className={`status-dot status-${doc.status}`} />
            {doc.status === "ready"
              ? `${doc.page_count} pages · ${doc.chunk_count} chunks`
              : doc.status}
          </span>
          <button
            className="remove"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(doc.id);
            }}
          >
            Remove
          </button>
        </div>
      ))}
    </div>
  );
}
