import type { SearchResultItem } from "../types";

interface SearchResultsProps {
  results: SearchResultItem[];
  query: string;
  total: number;
  isLoading: boolean;
  error: string | null;
  onSelect: (docId: number) => void;
}

export function SearchResults({
  results,
  query,
  total,
  isLoading,
  error,
  onSelect,
}: SearchResultsProps) {
  if (isLoading) {
    return (
      <div className="state-container">
        <p className="state-text">Searching…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-container error">
        <p className="state-text">{error}</p>
      </div>
    );
  }

  if (!query) {
    return (
      <div className="state-container">
        <p className="state-text">Enter a search query to begin.</p>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="state-container">
        <p className="state-text">No results found for "{query}".</p>
      </div>
    );
  }

  return (
    <div className="results-list">
      <p className="results-count">
        {total} result{total !== 1 ? "s" : ""} for "{query}"
      </p>
      {results.map((item) => (
        <div
          key={item.doc_id}
          className="result-item"
          onClick={() => onSelect(item.doc_id)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && onSelect(item.doc_id)}
        >
          <div className="result-header">
            <span className="result-filename">{item.filename}</span>
            <span className="result-score">{item.score.toFixed(4)}</span>
          </div>
          <div
            className="result-snippet"
            dangerouslySetInnerHTML={{ __html: item.snippet }}
          />
          <div className="result-meta">
            {item.content_length} tokens · {new Date(item.created_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}