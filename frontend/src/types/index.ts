/**
 * Type definitions for Signal Pilot frontend.
 * Derived from the actual backend API response envelopes.
 */

export interface DocumentUpload {
  filename: string;
  content: string;
  mime_type?: string;
}

export interface DocumentResponse {
  id: number;
  filename: string;
  content: string;
  content_length: number;
  file_size: number;
  mime_type: string | null;
  created_at: string;
}

export interface DocumentSummary {
  id: number;
  filename: string;
  content_length: number;
  file_size: number;
  mime_type: string | null;
  created_at: string;
}

export interface SearchResultItem {
  doc_id: number;
  filename: string;
  score: number;
  snippet: string;
  content_length: number;
  created_at: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  offset: number;
  limit: number;
  results: SearchResultItem[];
  applied_filters: Record<string, string>;
}

export interface HealthResponse {
  status: string;
  version: string;
  demo_mode: boolean;
  document_count: number;
}

export type ViewState = "idle" | "loading" | "error";

export interface ErrorState {
  error: string | null;
  view: ViewState;
}