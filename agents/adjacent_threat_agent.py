"""
AdjacentThreatAgent — identifies threats from companies entering from
nearby markets, substitutes, platform encroachment, and emerging startups.
Uses LLM for deep threat analysis.
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

ADJACENT_THREAT_SYSTEM_PROMPT = """You are an adjacent market threat analyst. You identify threats from companies entering from nearby markets, platform encroachment, substitute products, and emerging startups that could disrupt the target company's position.

You must respond with valid JSON matching this schema:
{
  "findings": [
    {
      "statement": "Specific threat finding",
      "type": "fact|interpretation|recommendation",
      "confidence": "low|medium|high",
      "rationale": "Evidence-backed reasoning"
    }
  ],
  "threat_map": {
    "adjacent_entrants": [
      {"name": "company", "from_market": "their original market", "threat_level": "high|medium|low", "evidence": "why they're a threat"}
    ],
    "platform_encroachment": [
      {"platform": "name", "capability": "what they're building", "threat_level": "high|medium|low"}
    ],
    "substitutes": [
      {"name": "product/approach", "how_it_substitutes": "explanation"}
    ],
    "emerging_startups": [
      {"name": "startup", "approach": "what they do differently", "stage": "seed|series_a|growth"}
    ]
  },
  "category_overlap": {
    "expanding_into_our_space": ["company1", "company2"],
    "we_could_expand_into": ["adjacent market1"],
    "consolidation_risk": "high|medium|low"
  },
  "overall_threat_level": "high|medium|low",
  "defensive_recommendations": ["recommendation1", "recommendation2"]
}"""


class AdjacentThreatAgent(BaseAgent):
    name = "AdjacentThreatAgent"

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

        user_prompt = f"""Analyze adjacent market threats for "{company}".

User's question: {query.query}

Collected data:
{evidence_text}

Identify:
1. Companies entering from adjacent markets
2. Platform encroachment (big tech building native capabilities)
3. Substitute products or approaches
4. Emerging startups with disruptive approaches
5. Category consolidation and expansion trends
6. Defensive recommendations for {company}
"""
        result = await analyze_with_llm_json(ADJACENT_THREAT_SYSTEM_PROMPT, user_prompt)

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
            threat_map = result.get("threat_map", {})
            if threat_map:
                threat_map["overall_threat_level"] = result.get("overall_threat_level", "medium")
                artifacts.append(Artifact(artifact_type="threat_map", payload=threat_map))
            overlap = result.get("category_overlap", {})
            if overlap:
                artifacts.append(Artifact(artifact_type="category_overlap", payload=overlap))
            defenses = result.get("defensive_recommendations", [])
            if defenses:
                for rec in defenses:
                    findings.append(Finding(
                        statement=rec,
                        type="recommendation",
                        confidence="medium",
                        rationale="Based on adjacent threat analysis.",
                    ))

        if not findings:
            findings.append(Finding(
                statement=f"Adjacent threat analysis for {company} completed with limited data.",
                type="interpretation",
                confidence="low",
                rationale="Insufficient data to identify clear threats.",
            ))

        return findings, artifacts

    async def collect_sources(self, query: QueryRequest, errors: list[str]) -> list[dict]:
        company = query.company_name or query.product_name or "company"
        sources: list[dict] = []

        try:
            adjacent_results, platform_results, startup_results, reddit_posts, hn_stories = await asyncio.gather(
                search_web(f"{company} adjacent market entrants new competitors", num_results=3),
                search_web(f"{company} platform encroachment big tech bundling", num_results=3),
                search_web(f"{company} emerging startup substitute alternative", num_results=3),
                search_reddit(f"{company} new competitor platform threat", limit=3),
                search_hackernews(f"{company} disruption startup alternative", limit=3),
            )
        except Exception as e:
            errors.append(f"Source collection failed: {str(e)}")
            return sources

        for r in adjacent_results:
            r["source_type"] = "adjacent_market_search"
            r["entity"] = company
            sources.append(r)
        for r in platform_results:
            r["source_type"] = "platform_threat_search"
            r["entity"] = company
            sources.append(r)
        for r in startup_results:
            r["source_type"] = "emerging_startup_search"
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

        urls_to_scrape = [r["url"] for r in (adjacent_results + platform_results)[:3]]
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
            "adjacent_entrants": [],
            "substitutes": [],
            "platform_encroachment": [],
            "emerging_startups": [],
            "category_expansion": [],
        }
        for src in sources:
            text = (src.get("snippet", "") + " " + src.get("title", "")).lower()
            if any(kw in text for kw in ["entering", "expanding into", "adjacent", "new competitor", "pivot"]):
                signals["adjacent_entrants"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["substitute", "alternative", "replacement", "switched"]):
                signals["substitutes"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["platform", "native", "built-in", "bundl", "embedded"]):
                signals["platform_encroachment"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["startup", "seed", "series a", "early-stage", "new entrant"]):
                signals["emerging_startups"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["expand", "broader", "category", "all-in-one", "suite"]):
                signals["category_expansion"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
        return signals

    def generate_findings(self, signals: dict, query: QueryRequest) -> list[Finding]:
        findings: list[Finding] = []
        company = query.company_name or "the company"
        if signals["adjacent_entrants"]:
            findings.append(Finding(
                statement=f"Detected {len(signals['adjacent_entrants'])} adjacent market entrants targeting {company}'s space.",
                type="fact",
                confidence="high" if len(signals["adjacent_entrants"]) >= 2 else "medium",
                rationale="Cross-referenced web search and discussion sources.",
            ))
        if signals["platform_encroachment"]:
            findings.append(Finding(
                statement=f"Platform encroachment detected — {len(signals['platform_encroachment'])} signals of native capabilities overlapping with {company}.",
                type="fact",
                confidence="medium",
                rationale="Detected platform bundling signals.",
            ))
        if not findings:
            findings.append(Finding(
                statement=f"No strong adjacent threats detected for {company}.",
                type="interpretation",
                confidence="low",
                rationale="Insufficient data from available sources.",
            ))
        return findings

    def _generate_artifacts(self, signals: dict, query: QueryRequest) -> list[Artifact]:
        company = query.company_name or "target company"
        threat_map = {
            "company": company,
            "threat_vectors": {k: {"count": len(v)} for k, v in signals.items()},
            "overall_threat_level": "high" if sum(len(v) for v in signals.values()) >= 10 else "medium",
        }
        return [Artifact(artifact_type="threat_map", payload=threat_map)]
