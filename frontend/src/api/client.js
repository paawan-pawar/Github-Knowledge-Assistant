// In local dev, this stays "/api" and Vite's dev-server proxy (vite.config.js)
// forwards it to the backend. In production there's no such proxy, so set
// VITE_API_BASE_URL at build time to your deployed backend's full URL, e.g.
// VITE_API_BASE_URL=https://repo-radar-api.onrender.com/api
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore parse failure, fall back to statusText */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/health"),

  importRepo: (url, branch, forceReindex = false) =>
    request("/repos", {
      method: "POST",
      body: JSON.stringify({ url, branch: branch || null, force_reindex: forceReindex }),
    }),

  listRepos: () => request("/repos"),
  getRepo: (repoId) => request(`/repos/${repoId}`),
  deleteRepo: (repoId) => request(`/repos/${repoId}`, { method: "DELETE" }),

  getTree: (repoId) => request(`/repos/${repoId}/tree`),
  getFile: (repoId, path) => request(`/repos/${repoId}/file?path=${encodeURIComponent(path)}`),
  searchFiles: (repoId, q) => request(`/repos/${repoId}/files/search?q=${encodeURIComponent(q)}`),

  search: (repoId, query, topK = 10) =>
    request(`/repos/${repoId}/search`, {
      method: "POST",
      body: JSON.stringify({ query, top_k: topK }),
    }),

  explain: (repoId, path, startLine, endLine, question) =>
    request(`/repos/${repoId}/explain`, {
      method: "POST",
      body: JSON.stringify({ path, start_line: startLine || null, end_line: endLine || null, question: question || null }),
    }),

  getArchitecture: (repoId) => request(`/repos/${repoId}/architecture`),

  generateFileDoc: (repoId, path) =>
    request(`/repos/${repoId}/docs/file`, { method: "POST", body: JSON.stringify({ path }) }),
  generateRepoDoc: (repoId) => request(`/repos/${repoId}/docs/repo`, { method: "POST" }),
  repoDocDownloadUrl: (repoId) => `${BASE}/repos/${repoId}/docs/repo/download`,

  getBugs: (repoId, aiReview = true) => request(`/repos/${repoId}/bugs?ai_review=${aiReview}`),

  getCommits: (repoId) => request(`/repos/${repoId}/commits`),
};

/**
 * Streams a chat response over SSE. Calls onEvent for every {type, ...}
 * payload the backend emits (token | sources | error | done).
 * Returns an abort() function.
 */
export function streamChat(repoId, messages, { model, topK = 8, onEvent, onError }) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE}/repos/${repoId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages, model: model || null, top_k: topK }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        let detail = res.statusText;
        try {
          detail = (await res.json()).detail || detail;
        } catch {
          /* ignore */
        }
        onError?.(detail);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          const dataLine = chunk.split("\n").find((l) => l.startsWith("data:"));
          if (!dataLine) continue;
          try {
            const payload = JSON.parse(dataLine.slice(5).trim());
            onEvent?.(payload);
          } catch {
            /* ignore malformed chunk */
          }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") onError?.(err.message || "Connection lost");
    }
  })();

  return () => controller.abort();
}

export { ApiError };
