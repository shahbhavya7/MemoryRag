// Shapes that mirror the FastAPI backend's Pydantic schemas.

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

// The five memory types the router can choose from (Phase 5/6).
export const MEMORY_TYPES = [
  "document",
  "code",
  "decision",
  "workflow",
  "conversation",
] as const;

export type MemoryType = (typeof MEMORY_TYPES)[number];

// --- Chat (Phase 6 graph) ---
export interface ChatSource {
  text: string;
  score: number;
  memory_type: string | null;
  source_ref: string | null;
}

export interface ChatResponse {
  answer: string;
  memory_types: string[]; // which memory type(s) the router picked
  sources: ChatSource[];
  memory_update: Record<string, unknown> | null;
  message_id: number | null;
}

// --- Context trace (Phase 7) ---
export interface TokenBreakdown {
  system: number;
  history: number;
  context: number;
  total: number;
}

export interface RetrievedItemTrace {
  memory_type: string | null;
  score: number;
  tokens: number;
  kept: boolean;
  preview: string;
}

export interface ContextTrace {
  message_id: number;
  token_budget: number;
  tokens: TokenBreakdown;
  history_messages_available: number;
  history_messages_kept: number;
  kept_count: number;
  dropped_count: number;
  retrieved: RetrievedItemTrace[];
}
