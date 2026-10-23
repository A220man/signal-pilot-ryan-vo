import { useState, useEffect } from "react";

interface SearchBarProps {
  onSearch: (query: string, mimeType?: string) => void;
  isLoading: boolean;
}

const MIME_TYPES = [
  { value: "", label: "All types" },
  { value: "text/plain", label: "Text" },
  { value: "text/markdown", label: "Markdown" },
  { value: "application/json", label: "JSON" },
];

export function SearchBar({ onSearch, isLoading }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [mimeType, setMimeType] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), mimeType || undefined);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="search-form">
      <div className="search-input-group">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter search terms…"
          disabled={isLoading}
          maxLength={500}
        />
        <select
          value={mimeType}
          onChange={(e) => setMimeType(e.target.value)}
          disabled={isLoading}
          className="mime-filter-select"
        >
          {MIME_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>
      <button type="submit" disabled={isLoading || !query.trim()} className="btn-primary">
        {isLoading ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
