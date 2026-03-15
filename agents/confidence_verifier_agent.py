"""
ConfidenceVerifierAgent — inspects findings from all other agents,
normalizes confidence, detects low-evidence claims and contradictions,
and separates fact from interpretation.
Uses LLM for deeper semantic contradiction detection when available.
"""

from agents.base_agent import BaseAgent
from schemas.agent_output import AgentOutput, Artifact
from schemas.finding_schema import Finding
from schemas.query_schema import QueryRequest
from tools.llm_client import analyze_with_llm_json, is_llm_available

VERIFIER_SYSTEM_PROMPT = """You are a research quality auditor. You review findings from multiple specialist research agents and identify:

1. Contradictions — findings that conflict with each other
2. Unsupported claims — high-confidence statements with weak rationale
3. Consensus — findings where multiple agents agree
4. Evidence gaps — important areas with no coverage

You must respond with valid JSON matching this schema:
{
  "contradictions": [
    {
      "finding_a": "first contradicting statement",
      "finding_b": "second contradicting statement",
      "explanation": "why these contradict"
    }
  ],
  "unsupported_claims": [
    {
      "statement": "the claim",
      "issue": "why the evidence is insufficient"
    }
  ],
  "consensus_areas": [
    {
      "theme": "what multiple agents agree on",
      "supporting_agents": ["agent1", "agent2"],
      "confidence_boost": "high"
    }
  ],
  "evidence_gaps": ["area with no coverage"],
  "overall_quality": "high|medium|low",
  "quality_rationale": "1-2 sentence assessment"
}"""


class ConfidenceVerifierAgent(BaseAgent):
    """
    Post-processing agent that reviews outputs from all specialist agents.
    Not called via the normal run() path — use verify_outputs() instead.
    """

    name = "ConfidenceVerifierAgent"

    async def run(self, query: QueryRequest) -> AgentOutput:
        return AgentOutput(agent_name=self.name, status="success")

    async def verify_outputs(self, outputs: list[AgentOutput]) -> AgentOutput:
        """
        Inspect all agent outputs and produce:
        - normalized confidence scores
        - contradiction flags
        - evidence quality summary
        - confidence panel artifact
        """
        panel: dict[str, dict] = {}
        quality_issues: list[dict] = []
        all_statements: list[dict] = []
        verification_findings: list[Finding] = []

        for output in outputs:
            if output.agent_name == self.name:
                continue

            agent_score = self._score_agent(output)
            panel[output.agent_name] = agent_score

            # Normalize per-finding confidence
            for finding in output.findings:
                all_statements.append({
                    "agent": output.agent_name,
                    "statement": finding.statement,
                    "type": finding.type,
                    "original_confidence": finding.confidence,
                    "rationale": finding.rationale if hasattr(finding, "rationale") else "",
                })
                self._normalize_finding(finding, agent_score)

            # Flag quality issues
            issues = self._check_quality(output, agent_score)
            quality_issues.extend(issues)

        # Detect contradictions — LLM when available, else keyword-based
        if is_llm_available() and len(all_statements) >= 2:
            llm_findings, llm_artifacts = await self._llm_verify(all_statements, panel)
            verification_findings.extend(llm_findings)
        else:
            contradictions = self._detect_contradictions(all_statements)
            for c in contradictions:
                verification_findings.append(Finding(
                    statement=f"Potential contradiction: '{c['a']['statement'][:80]}...' vs '{c['b']['statement'][:80]}...'",
                    type="interpretation",
                    confidence="low",
                    rationale=f"Opposing signals from {c['a']['agent']} and {c['b']['agent']}.",
                ))

        # Summary findings
        low_confidence_agents = [
            name for name, info in panel.items() if info["confidence"] == "low"
        ]
        if low_confidence_agents:
            verification_findings.append(Finding(
                statement=f"Low confidence outputs from: {', '.join(low_confidence_agents)}.",
                type="fact",
                confidence="high",
                rationale="These agents had insufficient or low-diversity evidence.",
            ))

        high_confidence_agents = [
            name for name, info in panel.items() if info["confidence"] == "high"
        ]
        if high_confidence_agents:
            verification_findings.append(Finding(
                statement=f"High confidence outputs from: {', '.join(high_confidence_agents)}.",
                type="fact",
                confidence="high",
                rationale="Strong evidence count and source diversity.",
            ))

        if quality_issues:
            verification_findings.append(Finding(
                statement=f"Detected {len(quality_issues)} evidence quality issue(s) across agents.",
                type="fact",
                confidence="high",
                rationale="; ".join(q["issue"] for q in quality_issues[:5]),
            ))

        artifacts = [
            Artifact(artifact_type="confidence_panel", payload=panel),
            Artifact(
                artifact_type="evidence_quality_summary",
                payload={
                    "total_agents_reviewed": len(panel),
                    "high_confidence": len(high_confidence_agents),
                    "low_confidence": len(low_confidence_agents),
                    "contradictions_found": sum(
                        1 for f in verification_findings if "contradiction" in f.statement.lower()
                    ),
                    "quality_issues": quality_issues,
                },
            ),
        ]

        return AgentOutput(
            agent_name=self.name,
            status="success",
            findings=verification_findings,
            artifacts=artifacts,
        )

    async def _llm_verify(
        self, all_statements: list[dict], panel: dict
    ) -> tuple[list[Finding], list[Artifact]]:
        """Use Claude to detect semantic contradictions and assess quality."""
        findings_text = "\n".join(
            f"- [{s['agent']}] ({s['original_confidence']}) {s['statement']}"
            for s in all_statements
        )
        confidence_text = "\n".join(
            f"- {name}: confidence={info.get('confidence', 'n/a')}, evidence_count={info.get('evidence_count', 0)}, diversity={info.get('source_diversity', 0)}"
            for name, info in panel.items()
            if isinstance(info, dict)
        )

        user_prompt = f"""Review these findings from multiple research agents for quality issues:

Findings:
{findings_text}

Agent confidence scores:
{confidence_text}

Identify contradictions, unsupported claims, areas of consensus, and evidence gaps."""

        result = await analyze_with_llm_json(VERIFIER_SYSTEM_PROMPT, user_prompt)

        findings: list[Finding] = []
        artifacts: list[Artifact] = []

        if result and isinstance(result, dict):
            # Contradictions
            for c in result.get("contradictions", []):
                findings.append(Finding(
                    statement=f"Contradiction detected: {c.get('explanation', 'conflicting findings')}",
                    type="interpretation",
                    confidence="medium",
                    rationale=f"'{c.get('finding_a', '')[:60]}' vs '{c.get('finding_b', '')[:60]}'",
                ))

            # Unsupported claims
            for u in result.get("unsupported_claims", []):
                findings.append(Finding(
                    statement=f"Unsupported claim: {u.get('statement', '')[:100]}",
                    type="interpretation",
                    confidence="medium",
                    rationale=u.get("issue", "Evidence insufficient for stated confidence."),
                ))

            # Consensus
            for con in result.get("consensus_areas", []):
                findings.append(Finding(
                    statement=f"Multi-agent consensus: {con.get('theme', '')}",
                    type="fact",
                    confidence="high",
                    rationale=f"Supported by: {', '.join(con.get('supporting_agents', []))}",
                ))

            # Evidence gaps
            gaps = result.get("evidence_gaps", [])
            if gaps:
                findings.append(Finding(
                    statement=f"Evidence gaps identified: {'; '.join(gaps[:5])}",
                    type="interpretation",
                    confidence="medium",
                    rationale="Areas where no agent provided coverage.",
                ))

            # Quality assessment artifact
            quality = result.get("overall_quality", "medium")
            rationale = result.get("quality_rationale", "")
            if quality or rationale:
                artifacts.append(Artifact(
                    artifact_type="llm_quality_assessment",
                    payload={
                        "overall_quality": quality,
                        "rationale": rationale,
                        "contradictions": len(result.get("contradictions", [])),
                        "consensus_areas": len(result.get("consensus_areas", [])),
                        "evidence_gaps": gaps,
                    },
                ))

        return findings, artifacts

    def _score_agent(self, output: AgentOutput) -> dict:
        """Score an agent's output based on evidence quantity and diversity."""
        if output.status != "success":
            return {"confidence": "n/a", "reason": "agent failed"}

        evidence_count = len(output.evidence)
        source_types = set(e.source_type for e in output.evidence if e.source_type)
        diversity = len(source_types)
        finding_count = len(output.findings)
        fact_count = sum(1 for f in output.findings if f.type == "fact")
        interp_count = sum(1 for f in output.findings if f.type == "interpretation")

        # Base score from evidence
        if evidence_count >= 4:
            level = "high"
        elif evidence_count >= 2:
            level = "medium"
        else:
            level = "low"

        # Diversity bonus
        if diversity >= 3 and level == "medium":
            level = "high"
        elif diversity >= 2 and level == "low":
            level = "medium"

        # Penalize if mostly interpretations with little evidence
        if interp_count > fact_count and evidence_count < 2:
            level = "low"

        return {
            "confidence": level,
            "evidence_count": evidence_count,
            "source_diversity": diversity,
            "source_types": list(source_types),
            "finding_count": finding_count,
            "fact_count": fact_count,
            "interpretation_count": interp_count,
        }

    def _normalize_finding(self, finding: Finding, agent_score: dict) -> None:
        """Downgrade finding confidence if agent-level evidence is weak."""
        agent_conf = agent_score.get("confidence", "low")

        if agent_conf == "low" and finding.confidence == "high":
            finding.confidence = "medium"
        if agent_conf == "low" and finding.type == "interpretation":
            finding.confidence = "low"
        if agent_conf == "n/a":
            finding.confidence = "low"

    def _check_quality(self, output: AgentOutput, score: dict) -> list[dict]:
        """Flag evidence quality issues."""
        issues = []
        if score.get("evidence_count", 0) == 0 and output.findings:
            issues.append({
                "agent": output.agent_name,
                "issue": f"{output.agent_name} has {len(output.findings)} finding(s) but zero evidence.",
                "severity": "high",
            })
        if score.get("source_diversity", 0) <= 1 and score.get("evidence_count", 0) >= 2:
            issues.append({
                "agent": output.agent_name,
                "issue": f"{output.agent_name} evidence comes from a single source type.",
                "severity": "medium",
            })
        interp = score.get("interpretation_count", 0)
        facts = score.get("fact_count", 0)
        if interp > facts * 2 and interp >= 3:
            issues.append({
                "agent": output.agent_name,
                "issue": f"{output.agent_name} has {interp} interpretations vs {facts} facts — heavy on speculation.",
                "severity": "medium",
            })
        return issues

    def _detect_contradictions(self, statements: list[dict]) -> list[dict]:
        """Simple contradiction detection using opposing keyword pairs."""
        contradictions = []
        opposition_pairs = [
            ("expensive", "cheap"),
            ("expensive", "affordable"),
            ("growing", "declining"),
            ("leader", "lagging"),
            ("simple", "complex"),
            ("fast", "slow"),
            ("reliable", "unreliable"),
            ("strong", "weak"),
        ]

        for i, a in enumerate(statements):
            for b in statements[i + 1:]:
                if a["agent"] == b["agent"]:
                    continue
                a_lower = a["statement"].lower()
                b_lower = b["statement"].lower()
                for word_a, word_b in opposition_pairs:
                    if (word_a in a_lower and word_b in b_lower) or \
                       (word_b in a_lower and word_a in b_lower):
                        contradictions.append({"a": a, "b": b, "trigger": (word_a, word_b)})
                        break

        return contradictions
