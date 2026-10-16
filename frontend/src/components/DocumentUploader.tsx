import { useState } from "react";
import { uploadDocument, ApiError } from "../api/client";
import type { DocumentResponse } from "../types";

interface DocumentUploaderProps {
  onUpload: (doc: DocumentResponse) => void;
  onError: (msg: string) => void;
  onStatus: (status: "idle" | "uploading") => void;
}

export function DocumentUploader({ onUpload, onError, onStatus }: DocumentUploaderProps) {
  const [filename, setFilename] = useState("");
  const [content, setContent] = useState("");
  const [mime, setMime] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!filename.trim() || !content.trim()) {
      onError("Filename and content are required.");
      return;
    }
    onStatus("uploading");
    try {
      const doc = await uploadDocument(filename.trim(), content, mime || undefined);
      onUpload(doc);
      setFilename("");
      setContent("");
      setMime("");
    } catch (err) {
      if (err instanceof ApiError) {
        onError(`Upload failed: ${err.message}`);
      } else {
        onError("Upload failed: unexpected error");
      }
    } finally {
      onStatus("idle");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <h2>Upload Document</h2>
      <div className="field">
        <label htmlFor="filename">Filename</label>
        <input
          id="filename"
          type="text"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          placeholder="e.g. notes.txt"
          maxLength={255}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="content">Content</label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste document text here..."
          rows={6}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="mime">MIME type (optional)</label>
        <input
          id="mime"
          type="text"
          value={mime}
          onChange={(e) => setMime(e.target.value)}
          placeholder="e.g. text/plain"
        />
      </div>
      <button type="submit" className="btn-primary">
        Index Document
      </button>
    </form>
  );
}