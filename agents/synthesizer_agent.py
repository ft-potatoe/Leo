import asyncio

from agents.base_agent import BaseAgent
from schemas.agent_output import AgentOutput
from schemas.query_schema import QueryRequest


_SYNTHESIS_SYSTEM_PROMPT = """You are a senior intelligence analyst producing boardroom-quality competitive intelligence briefs.
Given structured findings from multiple research agents, synthesize a compelling executive summary.

Rules:
- Lead with the single most important insight
- Be specific and evidence-grounded — no filler phrases
- Separate what is known (facts) from what is inferred (interpretations)
- Keep summary to 2-4 sentences
- Return ONLY the summary text, no JSON, no markdown"""


class SynthesizerAgent(BaseAgent):
    """
    Combines outputs from all specialist agents into a unified response.
    Produces: executive_summary, key_findings, facts, interpretations,
    recommendations, confidence_overview, artifacts, follow_up_questions.

    synthesize_async() uses Claude for the executive summary when available;
    synthesize() remains synchronous as a fallback.
    """

    name = "SynthesizerAgent"

    async def run(self, query: QueryRequest) -> AgentOutput:
        # Not used via normal run(); see synthesize_async() instead.
        return AgentOutput(agent_name=self.name, status="success")

    # ── Primary async path (uses LLM) ────────────────────────────────────────

    async def synthesize_async(
        self,
        query: QueryRequest,
        outputs: list[AgentOutput],
        confidence_overview: dict,
    ) -> dict:
        """Synthesize agent outputs, using Claude for the executive summary."""
        base = self._build_base(query, outputs, confidence_overview)

        # Try LLM-powered executive summary
        llm_summary = await self._llm_executive_summary(query, base["key_findings"])
        if llm_summary:
            base["executive_summary"] = llm_summary

        # Generate follow-ups (sync — fast)
        base["follow_up_questions"] = self._generate_follow_ups(query, outputs, confidence_overview)

        return base

    # ── Legacy sync path (no LLM) ────────────────────────────────────────────

    def synthesize(
        self,
        query: QueryRequest,
        outputs: list[AgentOutput],
        confidence_overview: dict,
    ) -> dict:
        """Synchronous synthesis without LLM (used as fallback or in tests)."""
        base = self._build_base(query, outputs, confidence_overview)
        base["follow_up_questions"] = self._generate_follow_ups(query, outputs, confidence_overview)
        return base

    # ── Internals ─────────────────────────────────────────────────────────────

    def _build_base(
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
                    "type": f.type,
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

        # Fallback summary (overridden by LLM if available)
        high_conf = [f for f in all_findings if f["confidence"] == "high"]
        summary_points = high_conf[:3] if high_conf else all_findings[:3]
        fallback_summary = "Key insights: " + " | ".join(
            f["statement"] for f in summary_points
        ) if summary_points else "No significant findings detected."

        return {
            "executive_summary": fallback_summary,
            "key_findings": all_findings,
            "facts": facts,
            "interpretations": interpretations,
            "recommendations": recommendations,
            "confidence_overview": confidence_overview,
            "artifacts": all_artifacts,
            "follow_up_questions": [],
        }

    async def _llm_executive_summary(
        self, query: QueryRequest, findings: list[dict]
    ) -> str:
        """Use Claude to write the executive summary. Returns '' on failure."""
        try:
            from tools.llm_client import is_llm_available, call_claude_with_search
            if not is_llm_available() or not findings:
                return ""

            findings_text = "\n".join(
                f"[{f['confidence'].upper()}] ({f['type']}) {f['statement']}"
                for f in findings[:15]
            )
            company = query.company_name or query.product_name or "the target company"
            user_prompt = (
                f"Company/Product: {company}\n"
                f"Research question: {query.query}\n\n"
                f"Agent findings:\n{findings_text}\n\n"
                "Write the executive summary now."
            )

            text, _, _ = await call_claude_with_search(
                system_prompt=_SYNTHESIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                use_web_search=False,  # synthesis uses existing findings only
            )
            return text.strip() if text else ""
        except Exception:
            return ""

    def _generate_follow_ups(
        self,
        query: QueryRequest,
        outputs: list[AgentOutput],
        confidence_overview: dict,
    ) -> list[str]:
        questions: list[str] = []

        for agent_name, info in confidence_overview.items():
            if isinstance(info, dict) and info.get("confidence") == "low":
                questions.append(
                    f"Can you provide more data on {agent_name.replace('Agent', '')} analysis?"
                )

        company = query.company_name or "this company"
        questions.extend([
            f"What is {company}'s ideal customer profile?",
            f"How does {company}'s retention compare to competitors?",
            "What are the biggest risks to current market positioning?",
        ])

        return questions[:5]
