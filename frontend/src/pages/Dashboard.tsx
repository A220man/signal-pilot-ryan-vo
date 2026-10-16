import { useEffect, useState } from "react";
import { DocumentUploader } from "../components/DocumentUploader";
import { SearchBar } from "../components/SearchBar";
import { SearchResults } from "../components/SearchResults";
import { DocumentViewer } from "../components/DocumentViewer";
import { checkHealth, searchDocuments } from "../api/client";
import type { DocumentResponse, HealthResponse, SearchResultItem } from "../types";

export function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading">("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<DocumentResponse | null>(null);
  const [viewerDocId, setViewerDocId] = useState<number | null>(null);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch((err) => setHealthError(`Health check failed: ${err.message}`));
  }, []);

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    setSearchError(null);
    setIsSearching(true);
    try {
      const resp = await searchDocuments(query);
      setSearchResults(resp.results);
      setSearchTotal(resp.total);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Search failed");
      setSearchResults([]);
      setSearchTotal(0);
    } finally {
      setIsSearching(false);
    }
  };

  const handleUpload = (doc: DocumentResponse) => {
    setUploadSuccess(doc);
    setUploadError(null);
    // Refresh health to update document count
    checkHealth().then(setHealth).catch(() => {});
  };

  const handleUploadError = (msg: string) => {
    setUploadError(msg);
    setUploadSuccess(null);
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Signal Pilot</h1>
        <p className="subtitle">Token-efficient BM25 search for AI agents</p>
      </header>

      {health && (
        <div className="health-banner">
          <span>Status: {health.status}</span>
          <span>Indexed: {health.document_count} documents</span>
          <span>Demo mode: {health.demo_mode ? "on" : "off"}</span>
        </div>
      )}
      {healthError && <p className="error">{healthError}</p>}

      <section className="upload-section">
        <DocumentUploader
          onUpload={handleUpload}
          onError={handleUploadError}
          onStatus={(s) => setUploadStatus(s)}
        />
        {uploadStatus === "uploading" && <p className="info">Indexing document…</p>}
        {uploadSuccess && (
          <p className="success">
            Indexed "{uploadSuccess.filename}" (ID: {uploadSuccess.id})
          </p>
        )}
        {uploadError && <p className="error">{uploadError}</p>}
      </section>

      <section className="search-section">
        <SearchBar onSearch={handleSearch} isLoading={isSearching} />
        <SearchResults
          results={searchResults}
          query={searchQuery}
          total={searchTotal}
          isLoading={isSearching}
          error={searchError}
          onSelect={setViewerDocId}
        />
      </section>

      <DocumentViewer docId={viewerDocId} onClose={() => setViewerDocId(null)} />
    </div>
  );
}