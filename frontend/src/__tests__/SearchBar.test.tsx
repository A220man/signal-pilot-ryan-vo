import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SearchBar } from "../components/SearchBar";

describe("SearchBar", () => {
  it("renders input field and search button", () => {
    render(<SearchBar onSearch={vi.fn()} isLoading={false} />);

    expect(screen.getByPlaceholderText("Enter search terms…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("calls onSearch with query and mimeType when submitted", () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} isLoading={false} />);

    fireEvent.change(screen.getByPlaceholderText("Enter search terms…"), {
      target: { value: "test query" },
    });
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "text/markdown" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(onSearch).toHaveBeenCalledWith("test query", "text/markdown");
  });

  it("calls onSearch with query only when mimeType is All types", () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} isLoading={false} />);

    fireEvent.change(screen.getByPlaceholderText("Enter search terms…"), {
      target: { value: "test query" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(onSearch).toHaveBeenCalledWith("test query", undefined);
  });

  it("disables input and button when isLoading", () => {
    render(<SearchBar onSearch={vi.fn()} isLoading={true} />);

    expect(screen.getByPlaceholderText("Enter search terms…")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Searching…" })).toBeDisabled();
    expect(screen.getByRole("combobox")).toBeDisabled();
  });

  it("does not call onSearch for empty query", () => {
    const onSearch = vi.fn();
    render(<SearchBar onSearch={onSearch} isLoading={false} />);

    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(onSearch).not.toHaveBeenCalled();
  });

  it("shows mime type options", () => {
    render(<SearchBar onSearch={vi.fn()} isLoading={false} />);

    const select = screen.getByRole("combobox");
    expect(screen.getByRole("option", { name: "All types" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Text" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Markdown" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "JSON" })).toBeInTheDocument();
  });
});