import { useEffect, useState } from "react";
import { getDocument, ApiError } from "../api/client";
import type { DocumentResponse } from "../types";

interface DocumentViewerProps {
  docId: number | null;
  onClose: () => void;
}

export function DocumentViewer({ docId, onClose }: DocumentViewerProps) {
  const [doc, setDoc] = useState<DocumentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (docId === null) return;
    setLoading(true);
    setError(null);
    getDocument(docId)
      .then(setDoc)
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(`Load failed: ${err.message}`);
        } else {
          setError("Load failed: unexpected error");
        }
      })
      .finally(() => setLoading(false));
  }, [docId]);

  if (docId === null) return null;

  return (
    <div className="viewer-overlay">
      <div className="viewer-content">
        <button onClick={onClose} className="btn-secondary btn-small">
          ← Back
        </button>
        {loading && <p className="state-text">Loading…</p>}
        {error && <p className="state-text error">{error}</p>}
        {doc && (
          <>
            <h2>{doc.filename}</h2>
            <div className="viewer-meta">
              <span>ID: {doc.id}</span>
              <span>{doc.content_length} tokens</span>
              <span>{doc.file_size} bytes</span>
              <span>{doc.mime_type || "text/plain"}</span>
            </div>
            <pre className="viewer-content-body">{doc.content}</pre>
          </>
        )}
      </div>
    </div>
  );
}