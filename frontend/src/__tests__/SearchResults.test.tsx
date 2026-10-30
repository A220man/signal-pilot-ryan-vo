import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SearchResults } from "../components/SearchResults";
import type { SearchResultItem } from "../types";

const mockResults: SearchResultItem[] = [
  {
    doc_id: 1,
    filename: "ml-guide.txt",
    score: 0.9123,
    snippet: "Text about <mark>machine</mark> <mark>learning</mark> algorithms",
    content_length: 42,
    created_at: "2026-01-15T10:00:00+00:00",
  },
  {
    doc_id: 2,
    filename: "data-notes.md",
    score: 0.6543,
    snippet: "More <mark>machine</mark> data processing",
    content_length: 18,
    created_at: "2026-01-16T14:30:00+00:00",
  },
];

describe("SearchResults", () => {
  it("renders search results with filename, score, and snippet", () => {
    const { container } = render(
      <SearchResults
        results={mockResults}
        query="machine learning"
        total={2}
        isLoading={false}
        error={null}
        appliedFilters={{}}
        onSelect={() => {}}
      />,
    );

    // Both filenames are displayed
    expect(screen.getByText("ml-guide.txt")).toBeInTheDocument();
    expect(screen.getByText("data-notes.md")).toBeInTheDocument();

    // Scores are displayed
    expect(screen.getByText("0.9123")).toBeInTheDocument();
    expect(screen.getByText("0.6543")).toBeInTheDocument();

    // Snippet content is rendered (dangerouslySetInnerHTML with <mark> tags)
    expect(container.textContent).toContain("Text about machine learning");
    expect(container.textContent).toContain("More machine data processing");

    // Total count is shown
    expect(screen.getByText(/^2 results for/)).toBeInTheDocument();
  });

  it("shows empty state message when no results", () => {
    render(
      <SearchResults
        results={[]}
        query="nonexistent"
        total={0}
        isLoading={false}
        error={null}
        appliedFilters={{}}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByText(/No results found for "nonexistent"/)).toBeInTheDocument();
  });

  it("calls onSelect with doc_id when a result is clicked", () => {
    const onSelect = vi.fn();
    render(
      <SearchResults
        results={mockResults}
        query="test"
        total={2}
        isLoading={false}
        error={null}
        appliedFilters={{}}
        onSelect={onSelect}
      />,
    );

    fireEvent.click(screen.getByText("ml-guide.txt"));
    expect(onSelect).toHaveBeenCalledWith(1);
  });

  it("displays applied filters when present", () => {
    const { container } = render(
      <SearchResults
        results={mockResults}
        query="machine"
        total={2}
        isLoading={false}
        error={null}
        appliedFilters={{ mime_type: "text/plain" }}
        onSelect={() => {}}
      />,
    );

    expect(container.textContent).toContain("Filtered: mime_type=text/plain");
  });
});
