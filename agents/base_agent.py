import json
from abc import ABC, abstractmethod

from schemas.agent_output import AgentOutput
from schemas.artifact_schema import Artifact
from schemas.finding_schema import Finding
from schemas.query_schema import QueryRequest

# ── Per-agent system prompts ──────────────────────────────────────────────────

_AGENT_PROMPTS = {
    "MarketTrendsAgent": "You are a market intelligence analyst specialising in category trends, growth indicators, hiring signals, and funding activity.",
    "CompetitiveLandscapeAgent": "You are a competitive intelligence analyst identifying competitor positioning, feature launches, pricing moves, and market share signals.",
    "WinLossAgent": "You are a win/loss analyst surfacing WHY buyers choose or reject products from reviews, forums, and community posts.",
    "PricingAgent": "You are a pricing strategy analyst extracting pricing models, price points, packaging, and willingness-to-pay signals.",
    "PositioningAgent": "You are a brand positioning analyst studying messaging, taglines, homepage copy, and differentiation angles.",
    "AdjacentThreatAgent": "You are a strategic threat analyst identifying threats from adjacent categories, platform encroachment, and new entrants.",
}

# ── Per-agent artifact schemas (must match frontend component interfaces) ─────

_ARTIFACT_SCHEMAS: dict[str, str] = {
    "CompetitiveLandscapeAgent": """{
  "artifact_type": "competitive_scorecard",
  "payload": {
    "competitors": [
      {
        "name": "Competitor name",
        "positioning": "1-line positioning claim",
        "strengths": ["strength 1", "strength 2"],
        "weaknesses": ["weakness 1"],
        "threat_level": "high|medium|low",
        "sources": ["url1"]
      }
    ]
  }
}""",

    "MarketTrendsAgent": """{
  "artifact_type": "trend_chart",
  "payload": {
    "title": "Descriptive chart title",
    "data": [
      {"month": "Q1 24", "value": 80, "event": null},
      {"month": "Q2 24", "value": 110, "event": "Major product launch"},
      {"month": "Q3 24", "value": 145, "event": null},
      {"month": "Q4 24", "value": 180, "event": "Series B funding wave"},
      {"month": "Q1 25", "value": 220, "event": null}
    ],
    "yAxisLabel": "Market Activity Index",
    "sourceCount": 5,
    "confidence": "medium"
  }
}""",

    "WinLossAgent": """{
  "artifact_type": "win_loss_analysis",
  "payload": {
    "wins": [
      {"insight": "Why buyers choose this product", "frequency": 3, "sentiment": 0.8, "sources": ["reddit", "g2"]}
    ],
    "losses": [
      {"insight": "Why buyers leave or don't buy", "frequency": 5, "sentiment": -0.7, "sources": ["reddit"]}
    ],
    "buyer_summary": "2-3 sentence summary of the buyer's perspective based on sources"
  }
}""",

    "PricingAgent": """{
  "artifact_type": "pricing_intelligence",
  "payload": {
    "competitors": [
      {
        "name": "Product name",
        "model": "Tiered SaaS|Usage-based|Contact Sales|Freemium",
        "entry_price": "$49/mo or Free or N/A",
        "enterprise_price": "$500+/mo or Custom",
        "packaging": "Per seat / Per usage / Flat rate"
      }
    ],
    "willingness_to_pay": [
      {"signal": "Buyers mention paying $X for outcome Y", "confidence": "medium"}
    ],
    "gaps": ["Pricing gap or opportunity identified from sources"]
  }
}""",

    "PositioningAgent": """{
  "artifact_type": "positioning_map",
  "payload": {
    "xAxis": {"label": "Narrow / Vertical", "labelEnd": "Broad / Horizontal"},
    "yAxis": {"label": "SMB / Self-serve", "labelEnd": "Enterprise / Sales-led"},
    "competitors": [
      {"name": "Product A", "x": 0.3, "y": 0.7, "isTarget": false},
      {"name": "Target Co", "x": 0.6, "y": 0.4, "isTarget": true}
    ]
  }
}""",

    "AdjacentThreatAgent": """{
  "artifact_type": "adjacent_market_radar",
  "payload": {
    "rings": [
      {
        "label": "Immediate (0-12mo)",
        "nodes": [
          {"name": "Threat name", "description": "What they do", "relevance": "Why it matters", "threat_timeline": "0-6 months"}
        ]
      },
      {
        "label": "Emerging (1-2yr)",
        "nodes": [
          {"name": "Adjacent player", "description": "Their expansion plan", "relevance": "Overlap area", "threat_timeline": "12-24 months"}
        ]
      },
      {
        "label": "Horizon (2-3yr)",
        "nodes": [
          {"name": "Platform threat", "description": "Bundling risk", "relevance": "Category risk", "threat_timeline": "24-36 months"}
        ]
      }
    ]
  }
}""",
}

# ── Base class ────────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    """Abstract base class for all specialist agents."""

    name: str = "BaseAgent"

    @abstractmethod
    async def run(self, query: QueryRequest) -> AgentOutput:
        """Execute the agent's research task and return structured output."""
        ...

    async def _llm_enhance_findings(
        self,
        query: QueryRequest,
        sources: list[dict],
        fallback_findings: list[Finding],
        fallback_artifacts: list[Artifact] | None = None,
    ) -> tuple[list[Finding], list[Artifact]]:
        """
        Call Claude to analyse collected sources.
        Returns (findings, artifacts) with properly shaped payloads that
        match the frontend component interfaces.
        Falls back to (fallback_findings, fallback_artifacts) if LLM unavailable.
        """
        try:
            from tools.llm_client import is_llm_available, analyze_with_llm_json
            if not is_llm_available() or not sources:
                return fallback_findings, fallback_artifacts or []

            artifact_schema = _ARTIFACT_SCHEMAS.get(self.name, "")
            system_prompt = _build_system_prompt(
                self.name,
                _AGENT_PROMPTS.get(self.name, "You are an intelligence analyst."),
                artifact_schema,
            )

            sources_text = "\n\n".join(
                f"[{i+1}] {s.get('title','Untitled')}\nURL: {s.get('url','')}\n"
                f"Type: {s.get('source_type','web')}\nExcerpt: {s.get('snippet','')[:400]}"
                for i, s in enumerate(sources[:10])
            )

            company = query.company_name or query.product_name or "the target company"
            user_prompt = (
                f"Company/Product: {company}\n"
                f"Research question: {query.query}\n\n"
                f"Sources:\n{sources_text}"
            )

            result = await analyze_with_llm_json(system_prompt, user_prompt)
            if not result:
                return fallback_findings, fallback_artifacts or []

            # Parse findings
            llm_findings: list[Finding] = []
            for f in result.get("findings", []):
                try:
                    llm_findings.append(Finding(
                        statement=f["statement"],
                        type=f.get("type", "interpretation"),  # type: ignore[arg-type]
                        confidence=f.get("confidence", "medium"),  # type: ignore[arg-type]
                        rationale=f.get("rationale", ""),
                    ))
                except Exception:
                    continue

            # Parse artifact
            llm_artifacts: list[Artifact] = []
            art = result.get("artifact")
            if art and isinstance(art, dict) and art.get("artifact_type"):
                try:
                    llm_artifacts.append(Artifact(
                        artifact_type=art["artifact_type"],
                        payload=art.get("payload", {}),
                    ))
                except Exception:
                    pass

            findings_out = llm_findings if llm_findings else fallback_findings
            artifacts_out = llm_artifacts if llm_artifacts else (fallback_artifacts or [])
            return findings_out, artifacts_out

        except Exception:
            return fallback_findings, fallback_artifacts or []


def _build_system_prompt(agent_name: str, role: str, artifact_schema: str) -> str:
    artifact_instruction = ""
    if artifact_schema:
        artifact_instruction = f"""
Also generate ONE structured artifact with this EXACT shape (populate with real data from the sources):
{artifact_schema}
Include it in the JSON as the "artifact" key."""

    return f"""{role}
Analyse the provided search results and return structured intelligence.

Return ONLY valid JSON with this structure (no markdown, no code fences):
{{
  "findings": [
    {{
      "statement": "specific, evidence-grounded finding — quote or reference the source",
      "type": "fact|interpretation|recommendation",
      "confidence": "high|medium|low",
      "rationale": "cite which source number(s) support this"
    }}
  ],{artifact_instruction}
}}

Rules:
- Generate 4-7 findings
- fact = directly stated in a source; interpretation = your analysis; recommendation = actionable next step
- confidence: high = 3+ corroborating sources; medium = 1-2 sources; low = inferred
- For the artifact, use ONLY data from the sources — do not hallucinate names, prices, or URLs
- If sources lack data for a field, use "N/A" or omit that entry"""
