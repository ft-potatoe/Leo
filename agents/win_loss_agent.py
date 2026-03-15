"""
WinLossAgent — identifies buyer complaints, objections, switching reasons,
and friction points from public sources (reviews, Reddit, HN, forums).
Uses LLM reasoning for deeper buyer pain analysis.
"""

import asyncio
from collections import Counter
from datetime import datetime, timezone

from agents.base_agent import BaseAgent
from schemas.agent_output import AgentOutput, Evidence, Artifact
from schemas.finding_schema import Finding
from schemas.query_schema import QueryRequest
from tools.search_tools import search_web, search_reddit, search_hackernews
from tools.scraper_tools import scrape_page
from tools.signal_extractors import detect_review_signals
from tools.llm_client import analyze_with_llm_json, is_llm_available

WIN_LOSS_SYSTEM_PROMPT = """You are a win/loss intelligence analyst. You analyze reviews, forum discussions, and buyer feedback to identify why customers choose, leave, or reject products.

You must respond with valid JSON matching this schema:
{
  "findings": [
    {
      "statement": "Clear finding about buyer behavior or pain point",
      "type": "fact|interpretation|recommendation",
      "confidence": "low|medium|high",
      "rationale": "Evidence-backed reasoning"
    }
  ],
  "objection_map": {
    "category_name": {
      "severity": "high|medium|low",
      "frequency": "number of mentions",
      "example_quotes": ["direct quotes or paraphrases from sources"],
      "impact": "how this affects buying decisions"
    }
  },
  "buyer_pain_clusters": {
    "cost": 0,
    "reliability": 0,
    "usability": 0,
    "support": 0,
    "features": 0,
    "churn": 0
  },
  "switching_patterns": "summary of why buyers switch to/from this product"
}"""


class WinLossAgent(BaseAgent):
    name = "WinLossAgent"

    async def run(self, query: QueryRequest) -> AgentOutput:
        company = query.company_name or "the target company"
        evidence: list[Evidence] = []
        all_signals: list[dict] = []
        errors: list[str] = []
        scraped_texts: list[dict] = []

        try:
            sources = await self._collect_sources(company, query.query)
            scraped = await self._scrape_sources(sources)
            for page in scraped:
                if not page.get("text"):
                    continue
                signals = detect_review_signals(page["text"])
                if signals:
                    all_signals.extend(signals)
                evidence.append(Evidence(
                    source_type=page.get("source_type", "web"),
                    url=page.get("url", ""),
                    title=page.get("title", ""),
                    snippet=page["text"][:300],
                    collected_at=page.get("collected_at", datetime.now(timezone.utc).isoformat()),
                ))
                scraped_texts.append({
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "source_type": page.get("source_type", "web"),
                    "text": page["text"][:2000],
                })
        except Exception as e:
            errors.append(f"Source collection failed: {e}")

        if is_llm_available() and scraped_texts:
            findings, artifacts = await self._llm_analyze(scraped_texts, company, query.query, all_signals)
        else:
            findings = self._generate_findings(all_signals, company)
            artifacts = self._build_artifacts(all_signals)

        return AgentOutput(
            agent_name=self.name,
            status="success" if findings else "error",
            findings=findings,
            evidence=evidence,
            artifacts=artifacts,
            errors=errors,
        )

    async def _llm_analyze(
        self, scraped_texts: list[dict], company: str, query: str, regex_signals: list[dict]
    ) -> tuple[list[Finding], list[Artifact]]:
        evidence_text = "\n\n---\n\n".join(
            f"Source ({t['source_type']}): {t['url']}\nTitle: {t['title']}\nContent:\n{t['text']}"
            for t in scraped_texts
        )
        regex_summary = ", ".join(set(s["signal"] for s in regex_signals)) if regex_signals else "none"

        user_prompt = f"""Analyze buyer sentiment and win/loss signals for "{company}".

User's question: {query}

Pre-detected review signals: {regex_summary}

Collected buyer feedback and reviews:
{evidence_text}

Identify:
1. Top buyer objections and pain points with severity
2. Why customers are switching to or from {company}
3. Recurring complaints and their business impact
4. Recommendations for addressing the most critical issues
"""
        result = await analyze_with_llm_json(WIN_LOSS_SYSTEM_PROMPT, user_prompt)

        findings: list[Finding] = []
        artifacts: list[Artifact] = []

        if result and isinstance(result, dict):
            for f in result.get("findings", []):
                findings.append(Finding(
                    statement=f.get("statement", ""),
                    type=f.get("type", "interpretation"),
                    confidence=f.get("confidence", "medium"),
                    rationale=f.get("rationale", ""),
                ))
            objection_map = result.get("objection_map", {})
            if objection_map:
                artifacts.append(Artifact(artifact_type="objection_map", payload=objection_map))
            pain_clusters = result.get("buyer_pain_clusters", {})
            if pain_clusters:
                artifacts.append(Artifact(artifact_type="buyer_pain_clusters", payload=pain_clusters))

        if not findings:
            findings.append(Finding(
                statement=f"Win/loss analysis for {company} completed with limited data.",
                type="interpretation",
                confidence="low",
                rationale="Insufficient buyer feedback found in public sources.",
            ))

        return findings, artifacts

    async def _collect_sources(self, company: str, query: str) -> list[dict]:
        searches = await asyncio.gather(
            search_web(f"{company} review complaints problems"),
            search_web(f"{company} vs competitors switched from"),
            search_reddit(f"{company} complaints issues problems"),
            search_hackernews(f"{company} alternative"),
            return_exceptions=True,
        )
        sources = []
        for result in searches:
            if isinstance(result, list):
                sources.extend(result)
        return sources

    async def _scrape_sources(self, sources: list[dict]) -> list[dict]:
        tasks = []
        for src in sources[:8]:
            url = src.get("url", "")
            if url:
                tasks.append(self._scrape_one(src))
        if not tasks:
            return []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict) and r.get("text")]

    async def _scrape_one(self, source: dict) -> dict:
        page = await scrape_page(source["url"])
        page["source_type"] = source.get("source_type", "web")
        if not page.get("text") and source.get("snippet"):
            page["text"] = source["snippet"]
            page["title"] = source.get("title", "")
        return page

    def _generate_findings(self, signals: list[dict], company: str) -> list[Finding]:
        if not signals:
            return [Finding(
                statement=f"No clear win/loss signals found for {company} from public sources.",
                type="interpretation",
                confidence="low",
                rationale="Insufficient public data to identify patterns.",
            )]
        signal_counts = Counter(s["signal"] for s in signals)
        findings: list[Finding] = []
        for signal_type, count in signal_counts.most_common(5):
            label = signal_type.replace("_", " ")
            confidence = "high" if count >= 3 else "medium" if count >= 2 else "low"
            example = next((s for s in signals if s["signal"] == signal_type), {})
            findings.append(Finding(
                statement=f"Recurring buyer pain: '{label}' detected in {count} source(s).",
                type="fact",
                confidence=confidence,
                rationale=f"Matched pattern in public content. Example: {example.get('context', 'N/A')}",
            ))
        return findings

    def _build_artifacts(self, signals: list[dict]) -> list[Artifact]:
        if not signals:
            return []
        signal_counts = Counter(s["signal"] for s in signals)
        objection_map = {
            signal_type.replace("_", " "): {
                "count": count,
                "examples": [s.get("context", "") for s in signals if s["signal"] == signal_type][:3],
            }
            for signal_type, count in signal_counts.most_common()
        }
        return [Artifact(artifact_type="objection_map", payload=objection_map)]
