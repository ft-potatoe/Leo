// ── Types matching backend Pydantic schemas ──

export interface QueryRequest {
  query: string;
  company_name: string;
  product_name: string;
  context?: string;
  session_id: string;
}

export interface Finding {
  statement: string;
  type: "fact" | "interpretation" | "recommendation";
  confidence: "low" | "medium" | "high";
  rationale: string;
}

export interface Evidence {
  source_type: string;
  url: string;
  title: string;
  snippet: string;
  collected_at: string;
  entity: string;
}

export interface Artifact {
  artifact_type: string;
  payload: Record<string, unknown>;
}

export interface AgentOutput {
  agent_name: string;
  status: "success" | "error" | "timeout";
  findings: Finding[];
  evidence: Evidence[];
  artifacts: Artifact[];
  errors: string[];
}

export interface OrchestratorResponse {
  session_id: string;
  query: string;
  executive_summary: string;
  key_findings: Finding[];
  facts: Finding[];
  interpretations: Finding[];
  recommendations: Finding[];
  confidence_overview: Record<string, unknown>;
  artifacts: Artifact[];
  follow_up_questions: string[];
  agent_outputs: AgentOutput[];
  errors: string[];
}

// ── Frontend-specific types ──

export type AgentStatus = "queued" | "running" | "done" | "failed" | "partial";

export interface AgentStatusInfo {
  name: string;
  displayName: string;
  status: AgentStatus;
  elapsed: number;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  response?: OrchestratorResponse;
  agentStatuses?: AgentStatusInfo[];
  metadata?: QueryMetadata;
}

export interface QueryMetadata {
  timestamp: Date;
  agentsUsed: string[];
  sourcesHit: number;
  totalLatency: number;
  estimatedCost: number;
}

export interface ProductContext {
  name: string;
  url: string;
}
