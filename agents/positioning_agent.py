"""
PositioningAgent — analyzes messaging, differentiation, category framing,
and identifies positioning gaps by comparing competitor homepage copy.
Uses LLM reasoning for deep messaging analysis.
"""

import asyncio
from datetime import datetime, timezone

from agents.base_agent import BaseAgent
from schemas.agent_output import AgentOutput, Evidence, Artifact
from schemas.finding_schema import Finding
from schemas.query_schema import QueryRequest
from tools.search_tools import search_web
from tools.scraper_tools import extract_page_sections
from tools.signal_extractors import detect_positioning_signals
from tools.llm_client import analyze_with_llm_json, is_llm_available

POSITIONING_SYSTEM_PROMPT = """You are a positioning and messaging strategist. You analyze company homepages, product pages, and marketing copy to identify positioning strategy, messaging gaps, and differentiation opportunities.

You must respond with valid JSON matching this schema:
{
  "findings": [
    {
      "statement": "Specific finding about positioning or messaging",
      "type": "fact|interpretation|recommendation",
      "confidence": "low|medium|high",
      "rationale": "Evidence-backed reasoning"
    }
  ],
  "positioning_summary": {
    "company_name": {
      "core_narrative": "What they claim to be",
      "key_claims": ["list of main value propositions"],
      "target_audience": "Who they're speaking to",
      "tone": "Professional/Casual/Technical/etc.",
      "overused_phrases": ["cliché phrases found"],
      "differentiation_strength": "strong|moderate|weak"
    }
  },
  "message_gap_heatmap": {
    "claim_type": {
      "company_a": true,
      "company_b": false
    }
  },
  "whitespace_opportunities": ["positioning angles no competitor is claiming"]
}"""


class PositioningAgent(BaseAgent):
    name = "PositioningAgent"

    async def run(self, query: QueryRequest) -> AgentOutput:
        company = query.company_name or "the target company"
        evidence: list[Evidence] = []
        positioning_data: dict[str, dict] = {}
        errors: list[str] = []
        scraped_texts: list[dict] = []

        try:
            sources = await self._collect_sources(company, query.query)
            scraped = await self._scrape_sources(sources)

            for page in scraped:
                text = page.get("text", "")
                hero = page.get("sections", {}).get("hero", "")
                if not text:
                    continue

                analysis = detect_positioning_signals(hero or text)
                entity = self._infer_entity(page.get("url", ""), page.get("title", ""), company)
                positioning_data[entity] = {
                    "claims": analysis["claims"],
                    "overused": analysis["overused_phrases"],
                    "icp_hints": analysis["icp_hints"],
                    "hero_snippet": (hero or text)[:200],
                }
                evidence.append(Evidence(
                    source_type="website",
                    url=page.get("url", ""),
                    title=page.get("title", ""),
                    snippet=(hero or text)[:300],
                    collected_at=page.get("collected_at", datetime.now(timezone.utc).isoformat()),
                ))
                scraped_texts.append({
                    "entity": entity,
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "hero": (hero or "")[:500],
                    "full_text": text[:2000],
                })
        except Exception as e:
            errors.append(f"Positioning research failed: {e}")

        if is_llm_available() and scraped_texts:
            findings, artifacts = await self._llm_analyze(scraped_texts, company, query.query, positioning_data)
        else:
            findings = self._generate_findings(positioning_data, company)
            artifacts = self._build_artifacts(positioning_data)

        return AgentOutput(
            agent_name=self.name,
            status="success" if findings else "error",
            findings=findings,
            evidence=evidence,
            artifacts=artifacts,
            errors=errors,
        )

    async def _llm_analyze(
        self, scraped_texts: list[dict], company: str, query: str, regex_data: dict
    ) -> tuple[list[Finding], list[Artifact]]:
        evidence_text = "\n\n---\n\n".join(
            f"Company: {t['entity']} ({t['url']})\nTitle: {t['title']}\nHero section:\n{t['hero']}\n\nFull page:\n{t['full_text']}"
            for t in scraped_texts
        )

        user_prompt = f"""Analyze the positioning and messaging for "{company}" and its competitors.

User's question: {query}

Collected homepage and product page data:
{evidence_text}

Provide:
1. Each company's core positioning narrative and key claims
2. Target audience signals for each company
3. Overused/cliché phrases that weaken differentiation
4. A message gap heatmap showing which claims each company makes vs doesn't
5. Whitespace opportunities — positioning angles nobody is claiming
6. Specific recommendations for {company}'s messaging strategy
"""
        result = await analyze_with_llm_json(POSITIONING_SYSTEM_PROMPT, user_prompt)

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
            pos_summary = result.get("positioning_summary", {})
            if pos_summary:
                artifacts.append(Artifact(artifact_type="positioning_summary", payload=pos_summary))
            heatmap = result.get("message_gap_heatmap", {})
            if heatmap:
                artifacts.append(Artifact(artifact_type="message_gap_heatmap", payload=heatmap))
            whitespace = result.get("whitespace_opportunities", [])
            if whitespace:
                artifacts.append(Artifact(
                    artifact_type="whitespace_analysis",
                    payload={"opportunities": whitespace},
                ))

        if not findings:
            findings.append(Finding(
                statement=f"Positioning analysis for {company} completed with limited data.",
                type="interpretation",
                confidence="low",
                rationale="Could not extract enough messaging data.",
            ))

        return findings, artifacts

    async def _collect_sources(self, company: str, query: str) -> list[dict]:
        searches = await asyncio.gather(
            search_web(f"{company} homepage"),
            search_web(f"{company} competitors homepage messaging"),
            search_web(f"{company} product features tagline"),
            return_exceptions=True,
        )
        sources = []
        for result in searches:
            if isinstance(result, list):
                sources.extend(result)
        return sources

    async def _scrape_sources(self, sources: list[dict]) -> list[dict]:
        tasks = []
        for src in sources[:6]:
            url = src.get("url", "")
            if url:
                tasks.append(self._scrape_one(src))
        if not tasks:
            return []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict) and r.get("text")]

    async def _scrape_one(self, source: dict) -> dict:
        page = await extract_page_sections(source["url"])
        if not page.get("text") and source.get("snippet"):
            page["text"] = source["snippet"]
            page["title"] = source.get("title", "")
            page["sections"] = {"hero": source["snippet"]}
        return page

    def _infer_entity(self, url: str, title: str, default: str) -> str:
        if "://" in url:
            domain = url.split("://")[1].split("/")[0].replace("www.", "").split(".")[0]
            if domain and domain not in ("g2", "capterra", "trustradius", "reddit", "google"):
                return domain
        return default

    def _generate_findings(self, data: dict[str, dict], company: str) -> list[Finding]:
        if not data:
            return [Finding(
                statement=f"No positioning data found for {company}.",
                type="interpretation",
                confidence="low",
                rationale="Could not scrape or analyze any competitor pages.",
            )]
        findings: list[Finding] = []
        for entity, info in data.items():
            claims = info.get("claims", {})
            if claims:
                top_claims = sorted(claims.items(), key=lambda x: -x[1])[:3]
                claim_summary = ", ".join(c[0].replace("_claim", "") for c in top_claims)
                findings.append(Finding(
                    statement=f"{entity}'s messaging emphasizes: {claim_summary}.",
                    type="fact",
                    confidence="medium",
                    rationale="Detected from homepage/product page copy analysis.",
                ))
        return findings

    def _build_artifacts(self, data: dict[str, dict]) -> list[Artifact]:
        if not data:
            return []
        all_claim_types = set()
        for info in data.values():
            all_claim_types.update(info.get("claims", {}).keys())
        heatmap = {}
        for entity, info in data.items():
            entity_claims = info.get("claims", {})
            heatmap[entity] = {claim: entity_claims.get(claim, 0) for claim in sorted(all_claim_types)}
        return [Artifact(artifact_type="message_gap_heatmap", payload=heatmap)]
