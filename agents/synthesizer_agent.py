"""
SynthesizerAgent — combines outputs from all specialist agents into a
unified strategic response.  Uses Claude for a cohesive executive summary
when available; falls back to simple string concatenation otherwise.
"""

from agents.base_agent import BaseAgent
from schemas.agent_output import AgentOutput
from schemas.query_schema import QueryRequest
from tools.llm_client import analyze_with_llm, is_llm_available

SYNTHESIS_SYSTEM_PROMPT = """You are a senior strategy consultant synthesizing intelligence from multiple specialist research agents. 

Your task is to produce a cohesive executive summary that:
1. Opens with the single most important strategic insight
2. Weaves findings from different agents into a unified narrative (do NOT list agent names)
3. Highlights where multiple agents converge on the same conclusion (high confidence)
4. Calls out contradictions or gaps in the data
5. Ends with 2-3 prioritized strategic recommendations

Write in clear, direct executive-briefing style. Keep it under 300 words.
Do NOT use bullet points — write flowing paragraphs.
Do NOT mention agent names or internal tool names."""


class SynthesizerAgent(BaseAgent):
    """
    Combines outputs from all specialist agents into a unified response.
    Produces: executive_summary, key_findings, facts, interpretations,
    recommendations, confidence_overview, artifacts, follow_up_questions.
    """

    name = "SynthesizerAgent"

    async def run(self, query: QueryRequest) -> AgentOutput:
        # Not used via normal run(); see synthesize() instead.
        return AgentOutput(agent_name=self.name, status="success")

    async def synthesize(
        self,
        query: QueryRequest,
        outputs: list[AgentOutput],
        confidence_overview: dict,
    ) -> dict:
        facts: list[dict] = []
        interpretations: list[dict] = []
        recommendations: list[dict] = []
        all_findings: list[dict] = []
        all_artifacts: list[dict] = []

        for output in outputs:
            if output.status != "success":
                continue
            for f in output.findings:
                entry = {
                    "agent": output.agent_name,
                    "statement": f.statement,
                    "confidence": f.confidence,
                    "rationale": f.rationale,
                }
                all_findings.append(entry)
                if f.type == "fact":
                    facts.append(entry)
                elif f.type == "interpretation":
                    interpretations.append(entry)
                elif f.type == "recommendation":
                    recommendations.append(entry)

            for a in output.artifacts:
                all_artifacts.append(
                    {"agent": output.agent_name, "artifact_type": a.artifact_type, "payload": a.payload}
                )

        # Build executive summary — LLM when available, else fallback
        executive_summary = await self._build_executive_summary(
            query, all_findings, confidence_overview
        )

        # Generate follow-up questions based on gaps
        follow_ups = self._generate_follow_ups(query, outputs, confidence_overview)

        return {
            "executive_summary": executive_summary,
            "key_findings": all_findings,
            "facts": facts,
            "interpretations": interpretations,
            "recommendations": recommendations,
            "confidence_overview": confidence_overview,
            "artifacts": all_artifacts,
            "follow_up_questions": follow_ups,
        }

    async def _build_executive_summary(
        self,
        query: QueryRequest,
        all_findings: list[dict],
        confidence_overview: dict,
    ) -> str:
        """Use Claude for a cohesive summary; fall back to concatenation."""
        if is_llm_available() and all_findings:
            return await self._llm_summarize(query, all_findings, confidence_overview)
        return self._fallback_summary(all_findings)

    async def _llm_summarize(
        self,
        query: QueryRequest,
        all_findings: list[dict],
        confidence_overview: dict,
    ) -> str:
        company = query.company_name or query.product_name or "the target company"

        findings_text = "\n".join(
            f"- [{f['confidence'].upper()}] {f['statement']} (Rationale: {f['rationale']})"
            for f in all_findings
        )

        confidence_text = "\n".join(
            f"- {name}: confidence={info.get('confidence', 'n/a')}, evidence={info.get('evidence_count', 0)}"
            for name, info in confidence_overview.items()
            if isinstance(info, dict)
        )

        user_prompt = f"""Synthesize the following intelligence findings into a strategic executive summary for "{company}".

User's original question: {query.query}

All findings from specialist research agents:
{findings_text}

Agent confidence levels:
{confidence_text}

Write a cohesive executive summary that weaves these findings together."""

        result = await analyze_with_llm(
            SYNTHESIS_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=1024,
            temperature=0.4,
        )

        if result and not result.startswith("[LLM error"):
            return result

        return self._fallback_summary(all_findings)

    def _fallback_summary(self, all_findings: list[dict]) -> str:
        """Simple concatenation fallback when LLM is unavailable."""
        high_conf = [f for f in all_findings if f["confidence"] == "high"]
        summary_points = high_conf[:3] if high_conf else all_findings[:3]
        return "Key insights: " + " | ".join(
            f["statement"] for f in summary_points
        )

    def _generate_follow_ups(
        self,
        query: QueryRequest,
        outputs: list[AgentOutput],
        confidence_overview: dict,
    ) -> list[str]:
        questions: list[str] = []

        # Suggest deeper dives for low-confidence areas
        for agent_name, info in confidence_overview.items():
            if isinstance(info, dict) and info.get("confidence") == "low":
                questions.append(f"Can you provide more data on {agent_name.replace('Agent', '')} analysis?")

        # Generic follow-ups
        company = query.company_name or "this company"
        questions.extend([
            f"What is {company}'s ideal customer profile?",
            f"How does {company}'s retention compare to competitors?",
            "What are the biggest risks to current market positioning?",
        ])

        return questions[:5]
