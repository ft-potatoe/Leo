"""
CompetitiveLandscapeAgent — gathers competitive intelligence including
competitor positioning, feature launches, pricing changes, and partnerships.
Uses LLM for deep competitive analysis.
"""

import asyncio
from datetime import datetime, timezone

from agents.base_agent import BaseAgent
from schemas.agent_output import AgentOutput
from schemas.evidence_schema import Evidence
from schemas.artifact_schema import Artifact
from schemas.finding_schema import Finding
from schemas.query_schema import QueryRequest
from tools.search_tools import search_web
from tools.scraper_tools import scrape_page
from tools.discussion_tools import search_reddit, search_hackernews
from tools.llm_client import analyze_with_llm_json, is_llm_available

COMPETITIVE_SYSTEM_PROMPT = """You are a competitive intelligence analyst. You analyze web data, community discussions, and product pages to map the competitive landscape.

You must respond with valid JSON matching this schema:
{
  "findings": [
    {
      "statement": "Specific competitive intelligence finding",
      "type": "fact|interpretation|recommendation",
      "confidence": "low|medium|high",
      "rationale": "Evidence-backed reasoning"
    }
  ],
  "competitor_matrix": {
    "company_name": {
      "positioning": "how they position themselves",
      "key_features": ["feature1", "feature2"],
      "pricing_approach": "freemium|enterprise|tiered|usage-based",
      "strengths": ["strength1"],
      "weaknesses": ["weakness1"],
      "recent_moves": ["notable recent actions"]
    }
  },
  "feature_comparison": {
    "feature_category": {
      "company_a": true,
      "company_b": false
    }
  },
  "competitive_dynamics": "1-2 sentence summary of competitive landscape"
}"""


class CompetitiveLandscapeAgent(BaseAgent):
    name = "CompetitiveLandscapeAgent"

    async def run(self, query: QueryRequest) -> AgentOutput:
        errors: list[str] = []
        evidence: list[Evidence] = []
        scraped_texts: list[dict] = []

        sources = await self.collect_sources(query, errors)

        for src in sources:
            evidence.append(Evidence(
                source_type=src.get("source_type", "web_search"),
                url=src.get("url", ""),
                title=src.get("title", ""),
                snippet=src.get("snippet", ""),
                collected_at=src.get("collected_at", datetime.now(timezone.utc).isoformat()),
                entity=src.get("entity", query.company_name or ""),
            ))
            text = src.get("text", "") or src.get("snippet", "")
            if text:
                scraped_texts.append({
                    "url": src.get("url", ""),
                    "title": src.get("title", ""),
                    "source_type": src.get("source_type", "web"),
                    "text": text[:1500],
                })

        if is_llm_available() and scraped_texts:
            findings, artifacts = await self._llm_analyze(scraped_texts, query)
        else:
            signals = self.extract_signals(sources)
            findings = self.generate_findings(signals, query)
            artifacts = self._generate_artifacts(signals, query)

        return AgentOutput(
            agent_name=self.name,
            status="success" if not errors else "error",
            findings=findings,
            evidence=evidence,
            artifacts=artifacts,
            errors=errors,
        )

    async def _llm_analyze(
        self, scraped_texts: list[dict], query: QueryRequest
    ) -> tuple[list[Finding], list[Artifact]]:
        company = query.company_name or query.product_name or "the company"
        evidence_text = "\n\n---\n\n".join(
            f"Source ({t['source_type']}): {t['url']}\nTitle: {t['title']}\nContent:\n{t['text']}"
            for t in scraped_texts[:15]
        )

        user_prompt = f"""Map the competitive landscape for "{company}".

User's question: {query.query}

Collected competitive intelligence:
{evidence_text}

Provide:
1. Key competitors and their positioning
2. Feature comparison across competitors
3. Pricing approaches in the market
4. Recent competitive moves (launches, partnerships, pricing changes)
5. Strengths and weaknesses of each competitor
6. Strategic recommendations for {company}
"""
        result = await analyze_with_llm_json(COMPETITIVE_SYSTEM_PROMPT, user_prompt)

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
            matrix = result.get("competitor_matrix", {})
            if matrix:
                artifacts.append(Artifact(artifact_type="competitor_matrix", payload=matrix))
            comparison = result.get("feature_comparison", {})
            if comparison:
                artifacts.append(Artifact(artifact_type="feature_comparison", payload=comparison))
            dynamics = result.get("competitive_dynamics", "")
            if dynamics:
                artifacts.append(Artifact(
                    artifact_type="competitive_summary",
                    payload={"summary": dynamics, "competitor_count": len(matrix)},
                ))

        if not findings:
            findings.append(Finding(
                statement=f"Competitive analysis for {company} completed with limited data.",
                type="interpretation",
                confidence="low",
                rationale="Insufficient competitive data from available sources.",
            ))

        return findings, artifacts

    async def collect_sources(self, query: QueryRequest, errors: list[str]) -> list[dict]:
        company = query.company_name or query.product_name or "company"
        base_query = f"{company} competitors {query.query}".strip()
        sources: list[dict] = []

        try:
            competitor_results, pricing_results, feature_results, reddit_posts, hn_stories = await asyncio.gather(
                search_web(f"{base_query} competitive landscape", num_results=3),
                search_web(f"{company} competitor pricing comparison", num_results=3),
                search_web(f"{company} competitor features integrations", num_results=3),
                search_reddit(f"{company} vs competitors", limit=3),
                search_hackernews(f"{company} alternative", limit=2),
            )
        except Exception as e:
            errors.append(f"Source collection failed: {str(e)}")
            return sources

        for r in competitor_results:
            r["source_type"] = "web_search"
            r["entity"] = company
            sources.append(r)
        for r in pricing_results:
            r["source_type"] = "pricing_research"
            r["entity"] = company
            sources.append(r)
        for r in feature_results:
            r["source_type"] = "feature_research"
            r["entity"] = company
            sources.append(r)
        for p in reddit_posts:
            p["source_type"] = "reddit"
            p["entity"] = company
            sources.append(p)
        for s in hn_stories:
            s["source_type"] = "hackernews"
            s["entity"] = company
            sources.append(s)

        urls_to_scrape = [r["url"] for r in competitor_results[:2]]
        try:
            scraped = await asyncio.gather(
                *[scrape_page(url) for url in urls_to_scrape],
                return_exceptions=True,
            )
            for page in scraped:
                if isinstance(page, dict) and page.get("text"):
                    page["source_type"] = "scraped_page"
                    page["snippet"] = page.get("text", "")[:300]
                    page["entity"] = company
                    sources.append(page)
        except Exception as e:
            errors.append(f"Scraping failed: {str(e)}")

        return sources

    def extract_signals(self, sources: list[dict]) -> dict:
        """Fallback regex-based signal extraction."""
        signals = {
            "positioning": [],
            "feature_launches": [],
            "pricing_signals": [],
            "integrations_partnerships": [],
            "competitor_mentions": [],
        }
        for src in sources:
            text = (src.get("snippet", "") + " " + src.get("title", "")).lower()
            if any(kw in text for kw in ["leader", "positioned", "ranked", "market share"]):
                signals["positioning"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["launch", "feature", "released", "shipped"]):
                signals["feature_launches"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["pricing", "price", "cost", "tier", "freemium"]):
                signals["pricing_signals"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["integration", "partnership", "partner"]):
                signals["integrations_partnerships"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if src.get("source_type") in ("reddit", "hackernews"):
                if any(kw in text for kw in ["vs", "alternative", "switched", "compared"]):
                    signals["competitor_mentions"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
        return signals

    def generate_findings(self, signals: dict, query: QueryRequest) -> list[Finding]:
        findings: list[Finding] = []
        company = query.company_name or "the company"
        if signals["positioning"]:
            findings.append(Finding(
                statement=f"{company} appears in competitive positioning data across {len(signals['positioning'])} sources.",
                type="fact",
                confidence="high" if len(signals["positioning"]) >= 2 else "medium",
                rationale=f"Found {len(signals['positioning'])} positioning references.",
            ))
        if signals["feature_launches"]:
            findings.append(Finding(
                statement=f"Competitors are shipping new features — {len(signals['feature_launches'])} launch signals detected.",
                type="fact",
                confidence="medium",
                rationale="Feature launch signals from web and product pages.",
            ))
        if not findings:
            findings.append(Finding(
                statement=f"Insufficient competitive data for {company}.",
                type="interpretation",
                confidence="low",
                rationale="No strong signals detected.",
            ))
        return findings

    def _generate_artifacts(self, signals: dict, query: QueryRequest) -> list[Artifact]:
        company = query.company_name or "target company"
        competitor_matrix = {
            "company": company,
            "total_competitive_signals": sum(len(v) for v in signals.values()),
            "positioning_mentions": len(signals["positioning"]),
            "feature_launch_count": len(signals["feature_launches"]),
        }
        return [Artifact(artifact_type="competitor_matrix", payload=competitor_matrix)]
