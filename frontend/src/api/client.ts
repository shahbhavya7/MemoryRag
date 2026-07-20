// A tiny fetch wrapper for the MemoryRAG backend.
//
// The JWT lives ONLY in memory (this module variable + React state that mirrors
// it) — deliberately NOT localStorage for now, so a page refresh logs you out.
// AuthContext calls setAuthToken() on login/logout; every request below then
// attaches it as a Bearer token automatically.

import type {
  ChatResponse,
  ContextTrace,
  DocumentUploadResult,
  EvalResponse,
  Memory,
  Project,
  Token,
  User,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8010";

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };

  const isFormData = options.body instanceof FormData;
  if (options.body && !isFormData && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    // Network-level failure (backend down, CORS blocked before response, etc.)
    throw new ApiError(0, `Cannot reach the API at ${API_URL}. Is the backend running?`);
  }

  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const data = await res.json();
      if (data?.detail) detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      // response had no JSON body — keep the status text
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // --- auth (Phase 2) ---
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: (email: string, password: string) =>
    request<Token>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  // --- projects (Phase 2) ---
  listProjects: () => request<Project[]>("/projects"),

  createProject: (name: string, description?: string) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, description: description ?? null }),
    }),

  // --- chat (Phase 6 routing graph) ---
  sendChat: (projectId: number, message: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, message }),
    }),

  // --- context trace (Phase 7) ---
  getContextTrace: (messageId: number) => request<ContextTrace>(`/context-trace/${messageId}`),

  // --- memories (Phase 5 / 9c) — scoped to a project ---
  listMemories: (projectId: number, memoryType?: string) => {
    const params = new URLSearchParams({ project_id: String(projectId) });
    if (memoryType) params.set("memory_type", memoryType);
    return request<Memory[]>(`/memories?${params.toString()}`);
  },

  createMemory: (projectId: number, memoryType: string, content: string, sourceRef?: string) =>
    request<Memory>("/memories", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        memory_type: memoryType,
        content,
        source_ref: sourceRef || null,
      }),
    }),

  // --- documents (Phase 3 / 9c) ---
  uploadDocument: (projectId: number, file: File) => {
    const form = new FormData();
    form.append("project_id", String(projectId));
    form.append("file", file);
    return request<DocumentUploadResult>("/documents/upload", { method: "POST", body: form });
  },

  // --- evaluation (Phase 7 / 9d) ---
  runEvaluation: (version?: string) =>
    request<EvalResponse>(`/evaluation/run${version ? `?version=${version}` : ""}`, { method: "POST" }),
};

export { API_URL };
