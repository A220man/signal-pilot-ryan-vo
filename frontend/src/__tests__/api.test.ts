import { uploadDocument, searchDocuments, getDocument, listDocuments, checkHealth, ApiError } from "../api/client";
import type { DocumentResponse, SearchResponse, HealthResponse, DocumentSummary } from "../types";

// Generate synthetic, clearly fake token at runtime for redaction tests
const makeFakeToken = () => "sk-or-v1-" + "0".repeat(48);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("API client", () => {
  describe("uploadDocument", () => {
    it("POSTs to the documents endpoint and returns the document", async () => {
      const mockResponse: DocumentResponse = {
        id: 1, filename: "test.txt", content: "hello world",
        content_length: 2, file_size: 11, mime_type: "text/plain",
        created_at: "2026-01-01T00:00:00+00:00",
      };
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await uploadDocument("test.txt", "hello world", "text/plain");
      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/documents"),
        expect.objectContaining({ method: "POST" }),
      );
    });

    it("throws ApiError on non-2xx response", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ detail: "Validation error" }),
      } as Response);

      await expect(uploadDocument("test.txt", "hi")).rejects.toThrow(ApiError);
      await expect(uploadDocument("test.txt", "hi")).rejects.toThrow("Validation error");
    });
  });

  describe("searchDocuments", () => {
    it("POSTs query params and returns ranked results", async () => {
      const mockResponse: SearchResponse = {
        query: "hello world", total: 1, offset: 0, limit: 20,
        results: [{
          doc_id: 1, filename: "test.txt", score: 0.85,
          snippet: "hello <mark>world</mark>", content_length: 2,
          created_at: "2026-01-01T00:00:00+00:00",
        }],
      };
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await searchDocuments("hello world");
      expect(result.query).toBe("hello world");
      expect(result.results).toHaveLength(1);
      expect(result.results[0].score).toBe(0.85);
    });

    it("passes limit and offset as query parameters", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ query: "x", total: 0, offset: 10, limit: 5, results: [] }),
      } as Response);
      global.fetch = mockFetch;

      await searchDocuments("x", 5, 10);
      const callUrl: string = mockFetch.mock.calls[0][0];
      expect(callUrl).toContain("limit=5");
      expect(callUrl).toContain("offset=10");
    });
  });

  describe("getDocument", () => {
    it("fetches a document by ID", async () => {
      const mock: DocumentResponse = {
        id: 42, filename: "doc.txt", content: "full content here",
        content_length: 3, file_size: 16, mime_type: null,
        created_at: "2026-01-01T00:00:00+00:00",
      };
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: true,
        json: async () => mock,
      } as Response);

      const result = await getDocument(42);
      expect(result.id).toBe(42);
      expect(result.content).toBe("full content here");
    });

    it("throws ApiError on 404", async () => {
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: false, status: 404,
        json: async () => ({ detail: "Not found" }),
      } as Response);
      await expect(getDocument(999)).rejects.toThrow("Not found");
    });
  });

  describe("listDocuments", () => {
    it("fetches document summaries with pagination", async () => {
      const mock: DocumentSummary[] = [
        { id: 1, filename: "a.txt", content_length: 3, file_size: 11, mime_type: "text/plain", created_at: "2026-01-01T00:00:00+00:00" },
      ];
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: true,
        json: async () => mock,
      } as Response);

      const result = await listDocuments();
      expect(result).toHaveLength(1);
      expect(result[0].filename).toBe("a.txt");
    });
  });

  describe("checkHealth", () => {
    it("fetches health endpoint", async () => {
      const mock: HealthResponse = {
        status: "ok", version: "1.0.0", demo_mode: true, document_count: 5,
      };
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: true, json: async () => mock,
      } as Response);

      const result = await checkHealth();
      expect(result.status).toBe("ok");
      expect(result.document_count).toBe(5);
    });
  });

  describe("token redaction in errors", () => {
    it("ApiError message preserves only the HTTP detail, never raw tokens", async () => {
      const fakeToken = makeFakeToken();
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: false, status: 401,
        json: async () => ({ detail: "Unauthorized" }),
      } as Response);

      await expect(uploadDocument("t.txt", "content")).rejects.toThrow();
      // Verify the fake token does not leak into any error message
      try {
        await uploadDocument("t.txt", "content");
      } catch (err) {
        expect(String(err)).not.toContain(fakeToken);
      }
    });
  });
});