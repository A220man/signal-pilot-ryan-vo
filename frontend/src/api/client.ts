/**
 * Typed API client for Signal Pilot backend.
 * All functions call the real HTTP endpoints and throw on non-2xx responses.
 */

import type {
  DocumentResponse,
  DocumentSummary,
  DocumentUpload,
  HealthResponse,
  SearchResponse,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // Keep default status text
    }
    throw new ApiError(`HTTP ${response.status}: ${detail}`, response.status);
  }
  return response.json() as Promise<T>;
}

/** Upload and index a document. */
export async function uploadDocument(
  filename: string,
  content: string,
  mimeType?: string,
): Promise<DocumentResponse> {
  const payload: DocumentUpload = { filename, content, ...(mimeType && { mime_type: mimeType }) };
  const response = await fetch(`${BASE_URL}/api/v1/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse<DocumentResponse>(response);
}

/** Search indexed documents with BM25 ranking. */
export async function searchDocuments(
  query: string,
  limit = 20,
  offset = 0,
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    query,
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(`${BASE_URL}/api/v1/search?${params}`, {
    method: "POST",
  });
  return handleResponse<SearchResponse>(response);
}

/** Retrieve a single document by ID. */
export async function getDocument(id: number): Promise<DocumentResponse> {
  const response = await fetch(`${BASE_URL}/api/v1/documents/${id}`);
  return handleResponse<DocumentResponse>(response);
}

/** List indexed documents with pagination. */
export async function listDocuments(
  limit = 50,
  offset = 0,
): Promise<DocumentSummary[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(`${BASE_URL}/api/v1/documents?${params}`);
  return handleResponse<DocumentSummary[]>(response);
}

/** Delete a document by ID. */
export async function deleteDocument(id: number): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/v1/documents/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail || "Delete failed", response.status);
  }
}

/** Check backend health and document count. */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${BASE_URL}/api/v1/health`);
  return handleResponse<HealthResponse>(response);
}

export { ApiError };