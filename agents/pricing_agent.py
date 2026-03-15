"""
PricingAgent — analyzes pricing models and packaging approaches across
companies using public pricing pages, reviews, and search results.
Uses LLM reasoning over scraped data for deeper analysis.
"""

import asyncio
from datetime import datetime, timezone

from agents.base_agent import BaseAgent
from schemas.agent_output import AgentOutput, Evidence, Artifact
from schemas.finding_schema import Finding
from schemas.query_schema import QueryRequest
from tools.search_tools import search_web
from tools.scraper_tools import scrape_page
from tools.signal_extractors import detect_pricing_signals
from tools.llm_client import analyze_with_llm_json, is_llm_available

PRICING_SYSTEM_PROMPT = """You are a pricing intelligence analyst. You analyze pricing pages, product pages, and reviews to extract pricing model insights.

You must respond with valid JSON matching this schema:
{
  "findings": [
    {
      "statement": "Clear, specific finding about pricing",
      "type": "fact|interpretation|recommendation",
      "confidence": "low|medium|high",
      "rationale": "Why you believe this, citing specific evidence"
    }
  ],
  "pricing_profiles": {
    "company_name": {
      "pricing_model": "tiered|freemium|enterprise|usage_based|seat_based|hybrid",
      "detected_tiers": ["free", "pro", "enterprise"],
      "has_free_trial": true,
      "has_self_serve": true,
      "sales_led": true,
      "price_points": ["any specific prices found"],
      "packaging_notes": "any notable packaging details"
    }
  },
  "market_pricing_summary": "1-2 sentence summary of pricing patterns in this market"
}"""


class PricingAgent(BaseAgent):
    name = "PricingAgent"

    async def run(self, query: QueryRequest) -> AgentOutput:
        company = query.company_name or "the target company"
        evidence: list[Evidence] = []
        all_signals: list[dict] = []
        pricing_profiles: dict[str, list[dict]] = {}
        errors: list[str] = []
        scraped_texts: list[dict] = []

        try:
            sources = await self._collect_sources(company, query.query)
            scraped = await self._scrape_sources(sources)

            for page in scraped:
                text = page.get("text", "")
                if not text:
                    continue

                signals = detect_pricing_signals(text)
                url = page.get("url", "")
                entity = self._infer_entity(url, page.get("title", ""), company)

                if signals:
                    pricing_profiles.setdefault(entity, []).extend(signals)
                    all_signals.extend(signals)

                evidence.append(Evidence(
                    source_type="pricing_page",
                    url=url,
                    title=page.get("title", ""),
                    snippet=text[:300],
                    collected_at=page.get("collected_at", datetime.now(timezone.utc).isoformat()),
                ))
                scraped_texts.append({
                    "entity": entity,
                    "url": url,
                    "title": page.get("title", ""),
                    "text": text[:2000],
                })
        except Exception as e:
            errors.append(f"Pricing research failed: {e}")

        # Use LLM for deep analysis if available
        if is_llm_available() and scraped_texts:
            findings, artifacts = await self._llm_analyze(scraped_texts, company, query.query, all_signals)
        else:
            findings = self._generate_findings(all_signals, pricing_profiles, company)
            artifacts = self._build_artifacts(pricing_profiles)

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
            f"Source: {t['entity']} ({t['url']})\nTitle: {t['title']}\nContent:\n{t['text']}"
            for t in scraped_texts
        )
        regex_summary = ", ".join(set(s["signal"] for s in regex_signals)) if regex_signals else "none detected"

        user_prompt = f"""Analyze the following pricing data for "{company}".

User's question: {query}

Pre-detected pricing signals (regex): {regex_summary}

Collected evidence:
{evidence_text}

Provide detailed pricing intelligence including:
1. What pricing model each company uses
2. Specific price points if visible
3. How the market pricing compares (PLG vs sales-led, freemium prevalence)
4. Strategic recommendations for {company}'s pricing approach
"""
        result = await analyze_with_llm_json(PRICING_SYSTEM_PROMPT, user_prompt)

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
            profiles = result.get("pricing_profiles", {})
            if profiles:
                artifacts.append(Artifact(artifact_type="pricing_table", payload=profiles))
            summary = result.get("market_pricing_summary", "")
            if summary:
                artifacts.append(Artifact(
                    artifact_type="packaging_comparison",
                    payload={"market_summary": summary, "profiles": profiles},
                ))

        if not findings:
            findings.append(Finding(
                statement=f"Pricing analysis for {company} completed with limited data.",
                type="interpretation",
                confidence="low",
                rationale="LLM analysis returned no structured findings.",
            ))

        return findings, artifacts

    async def _collect_sources(self, company: str, query: str) -> list[dict]:
        searches = await asyncio.gather(
            search_web(f"{company} pricing plans"),
            search_web(f"{company} competitors pricing comparison"),
            search_web(f"{company} pricing review cost"),
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
        if not page.get("text") and source.get("snippet"):
            page["text"] = source["snippet"]
            page["title"] = source.get("title", "")
        return page

    def _infer_entity(self, url: str, title: str, default: str) -> str:
        combined = (url + " " + title).lower()
        if "://" in url:
            domain = url.split("://")[1].split("/")[0].replace("www.", "").split(".")[0]
            if domain and domain not in ("g2", "capterra", "trustradius", "reddit", "google"):
                return domain
        return default

    def _generate_findings(self, signals, profiles, company) -> list[Finding]:
        if not signals:
            return [Finding(
                statement=f"No pricing signals detected for {company} from public sources.",
                type="interpretation",
                confidence="low",
                rationale="Could not find or parse pricing information.",
            )]
        findings: list[Finding] = []
        for entity, entity_signals in profiles.items():
            signal_types = list({s["signal"] for s in entity_signals})
            if "contact_sales" in signal_types and "tiered" not in signal_types:
                findings.append(Finding(
                    statement=f"{entity} appears to use enterprise-led custom pricing.",
                    type="fact",
                    confidence="medium",
                    rationale="Pricing page shows contact-sales signals with no self-serve tiers.",
                ))
            elif "tiered" in signal_types:
                extras = [s for s in signal_types if s != "tiered"]
                desc = f" with {', '.join(extras)}" if extras else ""
                findings.append(Finding(
                    statement=f"{entity} uses a tiered pricing model{desc}.",
                    type="fact",
                    confidence="high" if len(entity_signals) >= 3 else "medium",
                    rationale=f"Detected {len(entity_signals)} pricing signal(s) on their page.",
                ))
            else:
                findings.append(Finding(
                    statement=f"{entity} pricing shows signals: {', '.join(signal_types)}.",
                    type="fact",
                    confidence="medium",
                    rationale=f"Based on {len(entity_signals)} detected pricing pattern(s).",
                ))
        return findings

    def _build_artifacts(self, profiles) -> list[Artifact]:
        if not profiles:
            return []
        pricing_table = {}
        for entity, signals in profiles.items():
            pricing_table[entity] = {
                "detected_models": list({s["signal"] for s in signals}),
                "signal_count": len(signals),
            }
        return [Artifact(artifact_type="pricing_table", payload=pricing_table)]
