import json
from abc import ABC, abstractmethod

from schemas.agent_output import AgentOutput
from schemas.finding_schema import Finding
from schemas.query_schema import QueryRequest

# Per-agent system prompts for LLM analysis
_AGENT_PROMPTS = {
    "MarketTrendsAgent": """You are a market intelligence analyst specialising in identifying category trends, growth indicators, and strategic signals.
Analyse the provided search results and extract structured intelligence about market direction, category velocity, hiring signals, funding activity, and technology adoption trends.""",

    "CompetitiveLandscapeAgent": """You are a competitive intelligence analyst. Analyse search results to identify competitor positioning, feature launches, pricing moves, partnerships, messaging shifts, and market share signals.
Focus on what competitors are DOING, not just what they say.""",

    "WinLossAgent": """You are a win/loss analyst specialising in buyer psychology and deal dynamics. Analyse reviews, forum discussions, and community posts to surface WHY buyers choose or reject products.
Extract specific pain points, switching triggers, objections, and buying criteria.""",

    "PricingAgent": """You are a pricing strategy analyst. Extract pricing model intelligence: tiers, price points, packaging, willingness-to-pay signals, discounting behaviour, and PLG vs sales-led patterns from the sources.""",

    "PositioningAgent": """You are a brand positioning analyst. Analyse messaging, taglines, homepage copy, and ad content to identify positioning claims, differentiation angles, ICP targeting, and messaging gaps or over-crowded territory.""",

    "AdjacentThreatAgent": """You are a strategic threat analyst. Identify threats from adjacent categories, platform encroachment, new entrant patterns, and technology shifts that could disrupt the current category from unexpected directions.""",
}

_JSON_SCHEMA = """
Return ONLY valid JSON matching this schema (no markdown, no explanation):
{
  "findings": [
    {
      "statement": "specific, evidence-grounded finding",
      "type": "fact|interpretation|recommendation",
      "confidence": "high|medium|low",
      "rationale": "which source(s) support this and why"
    }
  ],
  "key_facts": ["direct factual claim 1", "direct factual claim 2"],
  "key_interpretations": ["analytical interpretation 1", "analytical interpretation 2"]
}
Generate 4-7 findings. Separate what is directly stated (fact) from what you infer (interpretation)."""


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
    ) -> list[Finding]:
        """
        Call Claude to analyse collected sources and return high-quality findings.
        Falls back to regex-based findings if LLM is unavailable or fails.
        """
        try:
            from tools.llm_client import is_llm_available, analyze_with_llm_json
            if not is_llm_available() or not sources:
                return fallback_findings

            system_prompt = _AGENT_PROMPTS.get(self.name, _AGENT_PROMPTS["CompetitiveLandscapeAgent"])
            system_prompt += "\n\n" + _JSON_SCHEMA

            # Build source context (cap at 10 sources to stay within token budget)
            sources_text = "\n\n".join(
                f"[{i+1}] {s.get('title', 'Untitled')}\nURL: {s.get('url', '')}\n"
                f"Type: {s.get('source_type', 'web')}\nExcerpt: {s.get('snippet', '')[:400]}"
                for i, s in enumerate(sources[:10])
            )

            company = query.company_name or query.product_name or "the target company"
            user_prompt = (
                f"Company/Product under analysis: {company}\n"
                f"Research question: {query.query}\n\n"
                f"Sources collected:\n{sources_text}"
            )

            result = await analyze_with_llm_json(system_prompt, user_prompt)
            if not result or "findings" not in result:
                return fallback_findings

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

            # If LLM returned good findings, use them; otherwise fall back
            return llm_findings if llm_findings else fallback_findings

        except Exception:
            return fallback_findings
