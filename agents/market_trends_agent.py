"""
MarketTrendsAgent — gathers market signals including category growth,
new product launches, hiring trends, discussion trends, emerging keywords,
and funding announcements. Uses LLM for deep trend analysis.
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

MARKET_TRENDS_SYSTEM_PROMPT = """You are a market trends analyst. You analyze web search results, news, community discussions, and industry data to identify market direction, growth signals, and emerging patterns.

You must respond with valid JSON matching this schema:
{
  "findings": [
    {
      "statement": "Specific, grounded market trend finding",
      "type": "fact|interpretation|recommendation",
      "confidence": "low|medium|high",
      "rationale": "Evidence-backed reasoning citing specific sources"
    }
  ],
  "trend_timeline": [
    {
      "category": "growth|launch|funding|hiring|sentiment",
      "signal": "description of the signal",
      "source": "url or source name",
      "strength": "strong|moderate|weak"
    }
  ],
  "signal_summary": {
    "market": "market name",
    "overall_direction": "accelerating|stable|decelerating|consolidating",
    "growth_signals": 0,
    "product_launches": 0,
    "funding_signals": 0,
    "hiring_signals": 0,
    "emerging_keywords": ["keyword1", "keyword2"],
    "sentiment": "positive|cautious|negative|mixed"
  }
}"""


class MarketTrendsAgent(BaseAgent):
    name = "MarketTrendsAgent"

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
                entity=query.company_name or query.product_name or "",
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
        market = query.company_name or query.product_name or "the target market"
        evidence_text = "\n\n---\n\n".join(
            f"Source ({t['source_type']}): {t['url']}\nTitle: {t['title']}\nContent:\n{t['text']}"
            for t in scraped_texts[:15]
        )

        user_prompt = f"""Analyze market trends and signals for "{market}".

User's question: {query.query}

Collected market data:
{evidence_text}

Provide:
1. Key growth indicators and market direction
2. Notable product launches and new entrants
3. Funding activity and investor sentiment
4. Community discussion sentiment (from Reddit/HN)
5. Emerging keywords and themes
6. Overall market trajectory assessment
"""
        result = await analyze_with_llm_json(MARKET_TRENDS_SYSTEM_PROMPT, user_prompt)

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
            timeline = result.get("trend_timeline", [])
            if timeline:
                artifacts.append(Artifact(artifact_type="trend_timeline", payload={"entries": timeline}))
            summary = result.get("signal_summary", {})
            if summary:
                artifacts.append(Artifact(artifact_type="signal_summary", payload=summary))

        if not findings:
            findings.append(Finding(
                statement=f"Market trend analysis for {market} completed with limited data.",
                type="interpretation",
                confidence="low",
                rationale="Insufficient signals from available sources.",
            ))

        return findings, artifacts

    async def collect_sources(self, query: QueryRequest, errors: list[str]) -> list[dict]:
        search_query = f"{query.company_name} {query.product_name} market trends {query.query}".strip()
        sources: list[dict] = []

        try:
            web_results, reddit_posts, hn_stories = await asyncio.gather(
                search_web(search_query, num_results=5),
                search_reddit(search_query, limit=3),
                search_hackernews(search_query, limit=3),
            )
        except Exception as e:
            errors.append(f"Source collection failed: {str(e)}")
            return sources

        for r in web_results:
            r["source_type"] = "web_search"
            sources.append(r)
        for p in reddit_posts:
            p["source_type"] = "reddit"
            sources.append(p)
        for s in hn_stories:
            s["source_type"] = "hackernews"
            sources.append(s)

        # Scrape top web results for deeper content
        urls_to_scrape = [r["url"] for r in web_results[:2]]
        scrape_tasks = [scrape_page(url) for url in urls_to_scrape]
        try:
            scraped_pages = await asyncio.gather(*scrape_tasks, return_exceptions=True)
            for page in scraped_pages:
                if isinstance(page, dict) and page.get("text"):
                    page["source_type"] = "scraped_page"
                    page["snippet"] = page.get("text", "")[:300]
                    sources.append(page)
        except Exception as e:
            errors.append(f"Scraping failed: {str(e)}")

        return sources

    def extract_signals(self, sources: list[dict]) -> dict:
        """Fallback regex-based signal extraction."""
        signals = {
            "growth_indicators": [],
            "product_launches": [],
            "hiring_trends": [],
            "discussion_sentiment": [],
            "emerging_keywords": [],
            "funding_activity": [],
        }
        for src in sources:
            text = (src.get("snippet", "") + " " + src.get("title", "")).lower()
            if any(kw in text for kw in ["grow", "growth", "increase", "surge", "yoy", "projected"]):
                signals["growth_indicators"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["launch", "new product", "released", "shipped", "show hn"]):
                signals["product_launches"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if any(kw in text for kw in ["hiring", "job", "openings", "posted", "recruiting"]):
                signals["hiring_trends"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
            if src.get("source_type") in ("reddit", "hackernews"):
                sentiment = "cautious" if any(kw in text for kw in ["crowded", "risk", "hype", "overrated"]) else "positive"
                signals["discussion_sentiment"].append({"signal": src.get("snippet", ""), "sentiment": sentiment})
            if any(kw in text for kw in ["ai-native", "composable", "open-source", "vertical saas", "api-first"]):
                matched = [kw for kw in ["ai-native", "composable", "open-source", "vertical saas", "api-first"] if kw in text]
                signals["emerging_keywords"].extend(matched)
            if any(kw in text for kw in ["funding", "raised", "series", "venture", "$"]):
                signals["funding_activity"].append({"signal": src.get("snippet", ""), "source": src.get("url", "")})
        signals["emerging_keywords"] = list(set(signals["emerging_keywords"]))
        return signals

    def generate_findings(self, signals: dict, query: QueryRequest) -> list[Finding]:
        findings: list[Finding] = []
        market = query.company_name or query.product_name or "the target market"
        if signals["growth_indicators"]:
            findings.append(Finding(
                statement=f"The {market} market shows growth signals across {len(signals['growth_indicators'])} sources.",
                type="fact",
                confidence="high" if len(signals["growth_indicators"]) >= 2 else "medium",
                rationale=f"Detected {len(signals['growth_indicators'])} growth indicators.",
            ))
        if signals["funding_activity"]:
            findings.append(Finding(
                statement=f"Active funding rounds detected in the {market} space.",
                type="fact",
                confidence="high" if len(signals["funding_activity"]) >= 2 else "medium",
                rationale=f"Found {len(signals['funding_activity'])} funding signals.",
            ))
        if not findings:
            findings.append(Finding(
                statement=f"Insufficient data for market trends for {market}.",
                type="interpretation",
                confidence="low",
                rationale="No strong signals detected.",
            ))
        return findings

    def _generate_artifacts(self, signals: dict, query: QueryRequest) -> list[Artifact]:
        market = query.company_name or query.product_name or "target market"
        timeline_entries = []
        for category in ["growth_indicators", "product_launches", "funding_activity"]:
            for sig in signals.get(category, []):
                timeline_entries.append({
                    "category": category,
                    "signal": sig.get("signal", "")[:200],
                    "source": sig.get("source", ""),
                })
        signal_summary = {
            "market": market,
            "total_sources_analyzed": sum(len(v) if isinstance(v, list) else 0 for v in signals.values()),
            "growth_signal_count": len(signals["growth_indicators"]),
            "product_launch_count": len(signals["product_launches"]),
            "emerging_keywords": signals["emerging_keywords"],
        }
        return [
            Artifact(artifact_type="trend_timeline", payload={"entries": timeline_entries}),
            Artifact(artifact_type="signal_summary", payload=signal_summary),
        ]
