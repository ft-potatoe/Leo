import { QueryRequest, OrchestratorResponse } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Standard JSON query ───────────────────────────────────────────────────────

export async function sendQuery(request: QueryRequest): Promise<OrchestratorResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ── SSE Streaming query ───────────────────────────────────────────────────────

export interface SSEEvent {
  event: string;
  agent?: string;
  status?: string;
  finding_count?: number;
  message?: string;
  result?: OrchestratorResponse & { cost_info?: Record<string, unknown> };
  timestamp?: string;
}

/**
 * Stream intelligence events from the backend via SSE.
 * Yields each parsed event object as it arrives.
 * Terminates after synthesis_complete or error.
 */
export async function* streamQuery(
  request: QueryRequest
): AsyncGenerator<SSEEvent, void, unknown> {
  const res = await fetch(`${API_BASE}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Stream error: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data: ")) continue;
        try {
          const event: SSEEvent = JSON.parse(line.slice(6));
          yield event;
          if (event.event === "synthesis_complete" || event.event === "error") {
            return;
          }
        } catch {
          // Malformed JSON — skip
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}

// ── Health check ──────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

// ── Cost info ─────────────────────────────────────────────────────────────────

export async function getCostInfo(): Promise<Record<string, unknown>> {
  try {
    const res = await fetch(`${API_BASE}/cost`);
    return res.ok ? res.json() : {};
  } catch {
    return {};
  }
}
