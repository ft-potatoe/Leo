"""
DeepResearchEngine — multi-hop research pipeline.

Hackathon constraint 7.3: instead of a single-pass search → extract → return,
this engine performs recursive sub-query decomposition, parallel thread execution,
cross-referencing, and convergence detection to surface intelligence with
higher confidence and broader coverage.

Pipeline per hop:
    1. Run agents on current query (delegates to Orchestrator.run)
    2. LLM identifies knowledge gaps and spawns sub-queries
    3. Sub-queries execute in parallel (each as their own thread)
    4. LLM cross-references findings across all threads
    5. Repeat until max_depth, convergence, or no new sub-queries
"""

import asyncio
import uuid
from dataclasses import dataclass, field

from schemas.query_schema import QueryRequest, OrchestratorResponse
from schemas.research_thread_schema import ResearchThread, CrossReference
from schemas.finding_schema import Finding
from tools.llm_client import analyze_with_llm_json, is_llm_available

# ── Prompts ──────────────────────────────────────────────────────────────────

SUB_QUERY_DECOMPOSITION_PROMPT = """You are a strategic research director. Given an original research question and collected findings, your job is to identify gaps and create focused follow-up sub-queries.

You must respond with valid JSON only, matching this schema:
{
  "sub_queries": [
    {
      "query": "Specific focused follow-up question",
      "rationale": "Why this sub-query closes a gap in current knowledge",
      "priority": "high|medium|low"
    }
  ],
  "sufficient_coverage": false,
  "coverage_rationale": "Brief explanation of whether we have enough information"
}

Rules:
- Generate 2-4 sub-queries maximum
- Each sub-query must be meaningfully different from the parent and siblings
- Focus on gaps: missing data, low-confidence areas, contradictions needing resolution
- If findings already provide sufficient coverage, set sufficient_coverage to true and return an empty sub_queries list
- Do NOT generate sub-queries that just rephrase the original question"""


CROSS_REFERENCE_PROMPT = """You are a senior intelligence analyst. You have findings from multiple parallel research threads. 
Identify relationships between findings: corroboration, contradictions, and new leads.

Respond with valid JSON only:
{
  "cross_references": [
    {
      "thread_a_id": "thread id string",
      "thread_b_id": "thread id string",
      "relationship": "corroborates|contradicts|extends",
      "statement_a": "key statement from thread A",
      "statement_b": "key statement from thread B",
      "explanation": "Why these findings relate and what it means for confidence"
    }
  ],
  "consensus_findings": [
    {
      "theme": "What multiple threads agree on",
      "confidence_boost": "high|medium",
      "supporting_thread_ids": ["id1", "id2"]
    }
  ],
  "contradiction_flags": [
    {
      "theme": "What threads disagree on",
      "thread_ids": ["id1", "id2"],
      "explanation": "Nature of the contradiction"
    }
  ]
}"""


# ── Core engine ──────────────────────────────────────────────────────────────

class DeepResearchEngine:
    """
    Recursive multi-hop research engine.

    Usage:
        engine = DeepResearchEngine(orchestrator)
        result, threads, depth = await engine.run_deep(request)
    """

    def __init__(self, orchestrator) -> None:
        # Avoids circular import — Orchestrator is passed in at construction time
        self.orchestrator = orchestrator

    async def run_deep(
        self, request: QueryRequest
    ) -> tuple[OrchestratorResponse, list[ResearchThread], int]:
        """
        Entry point.  Returns:
            - OrchestratorResponse enriched with cross-reference data
            - list[ResearchThread] — full thread tree (for API consumers)
            - int — max depth actually reached
        """
        all_threads: list[ResearchThread] = []
        max_depth_reached = 0

        # ── Root thread (hop 0) ─────────────────────────────────────
        root_thread = ResearchThread(
            thread_id=str(uuid.uuid4()),
            parent_id=None,
            query=request.query,
            depth=0,
            status="running",
        )
        all_threads.append(root_thread)

        root_response = await self._run_single_hop(request, root_thread)

        # ── Recursive deepening ─────────────────────────────────────
        active_threads = [root_thread]
        current_depth = 0

        while current_depth < request.max_depth:
            new_sub_queries: list[tuple[str, QueryRequest, str]] = []  # (parent_id, query_req, rationale)

            # For each active thread, ask LLM if we should go deeper
            decomposition_tasks = [
                self._decompose_sub_queries(t, request)
                for t in active_threads
            ]
            decompositions = await asyncio.gather(*decomposition_tasks, return_exceptions=True)

            for thread, result in zip(active_threads, decompositions):
                if isinstance(result, Exception) or result is None:
                    continue
                sub_queries, sufficient = result
                if sufficient:
                    continue
                for sq in sub_queries:
                    sub_req = QueryRequest(
                        query=sq["query"],
                        company_name=request.company_name,
                        product_name=request.product_name,
                        context=f"Parent query: {thread.query}",
                        session_id=request.session_id,
                        depth=current_depth + 1,
                        max_depth=request.max_depth,
                        parent_query_id=thread.thread_id,
                    )
                    new_sub_queries.append((thread.thread_id, sub_req, sq.get("rationale", "")))

            if not new_sub_queries:
                break  # Convergence — no new threads to spawn

            current_depth += 1
            max_depth_reached = current_depth

            # ── Spawn all sub-queries in parallel ──────────────────
            new_threads: list[ResearchThread] = []
            hop_tasks = []
            for parent_id, sub_req, rationale in new_sub_queries:
                child_thread = ResearchThread(
                    thread_id=str(uuid.uuid4()),
                    parent_id=parent_id,
                    query=sub_req.query,
                    depth=current_depth,
                    status="running",
                )
                all_threads.append(child_thread)
                new_threads.append(child_thread)

                # Register child in parent
                parent = next((t for t in all_threads if t.thread_id == parent_id), None)
                if parent:
                    parent.sub_thread_ids.append(child_thread.thread_id)

                hop_tasks.append(self._run_single_hop(sub_req, child_thread))

            await asyncio.gather(*hop_tasks, return_exceptions=True)
            active_threads = new_threads

        # ── Cross-reference all threads ─────────────────────────────
        cross_refs = await self._cross_reference_threads(all_threads)
        _apply_cross_references(all_threads, cross_refs)

        # ── Enrich root response with thread metadata ───────────────
        root_response.research_threads = [_thread_to_dict(t) for t in all_threads]
        root_response.depth_reached = max_depth_reached

        # Inject cross-reference consensus into key_findings
        _inject_cross_ref_findings(root_response, all_threads, cross_refs)

        return root_response, all_threads, max_depth_reached

    async def _run_single_hop(
        self, request: QueryRequest, thread: ResearchThread
    ) -> OrchestratorResponse:
        """Run a single orchestrator pass and populate the thread with results."""
        try:
            response = await self.orchestrator.run(request)
            thread.status = "complete"
            # Collect findings from all agents
            for finding_dict in response.key_findings:
                thread.findings.append(Finding(
                    statement=finding_dict.get("statement", ""),
                    type=finding_dict.get("type", "interpretation"),  # type: ignore[arg-type]
                    confidence=finding_dict.get("confidence", "medium"),  # type: ignore[arg-type]
                    rationale=finding_dict.get("rationale", ""),
                ))
            return response
        except Exception as e:
            thread.status = "error"
            thread.error = str(e)
            # Return a minimal error response
            return OrchestratorResponse(
                session_id=request.session_id,
                query=request.query,
                executive_summary=f"Thread failed: {e}",
                errors=[str(e)],
            )

    async def _decompose_sub_queries(
        self, thread: ResearchThread, original_request: QueryRequest
    ) -> tuple[list[dict], bool] | None:
        """
        Ask the LLM to identify knowledge gaps and generate sub-queries.
        Returns (sub_queries_list, sufficient_coverage_bool) or None on failure.
        """
        if not is_llm_available():
            return None  # No LLM → no decomposition

        if not thread.findings:
            return None  # Nothing to base decomposition on

        findings_text = "\n".join(
            f"- [{f.confidence.upper()}] {f.statement}"
            for f in thread.findings[:20]
        )

        user_prompt = f"""Original research question: "{original_request.query}"
Company/Product: {original_request.company_name or original_request.product_name or "not specified"}

Current thread question: "{thread.query}"
Current depth: {thread.depth}

Findings gathered so far:
{findings_text}

Identify knowledge gaps and generate targeted sub-queries to fill them.
Keep in mind: we want DEEPER insight, not broader. Focus on drilling into specific gaps."""

        result = await analyze_with_llm_json(SUB_QUERY_DECOMPOSITION_PROMPT, user_prompt)
        if not result or not isinstance(result, dict):
            return None

        sub_queries = result.get("sub_queries", [])
        sufficient = result.get("sufficient_coverage", False)

        # Filter to high/medium priority only
        sub_queries = [
            sq for sq in sub_queries
            if sq.get("priority", "medium") in ("high", "medium")
        ]

        return sub_queries, sufficient

    async def _cross_reference_threads(
        self, threads: list[ResearchThread]
    ) -> dict:
        """
        Run a cross-referencing pass across all completed threads.
        Returns the raw LLM result dict.
        """
        if not is_llm_available():
            return {}

        completed = [t for t in threads if t.status == "complete" and t.findings]
        if len(completed) < 2:
            return {}

        threads_text = "\n\n".join(
            f"Thread ID: {t.thread_id}\nQuery: {t.query}\nDepth: {t.depth}\nFindings:\n"
            + "\n".join(f"  - [{f.confidence}] {f.statement}" for f in t.findings[:10])
            for t in completed[:10]  # Cap at 10 threads for token budget
        )

        user_prompt = f"""Analyze these research threads and find relationships between their findings:

{threads_text}

Identify corroborations, contradictions, and extensions across threads."""

        result = await analyze_with_llm_json(CROSS_REFERENCE_PROMPT, user_prompt)
        return result if isinstance(result, dict) else {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _apply_cross_references(
    threads: list[ResearchThread], cross_ref_result: dict
) -> None:
    """Attach CrossReference objects to the relevant threads."""
    thread_map = {t.thread_id: t for t in threads}
    for ref in cross_ref_result.get("cross_references", []):
        a_id = ref.get("thread_a_id", "")
        b_id = ref.get("thread_b_id", "")
        if a_id not in thread_map or b_id not in thread_map:
            continue
        cross_ref = CrossReference(
            source_thread_id=a_id,
            target_thread_id=b_id,
            relationship=ref.get("relationship", "corroborates"),  # type: ignore[arg-type]
            source_statement=ref.get("statement_a", ""),
            target_statement=ref.get("statement_b", ""),
            explanation=ref.get("explanation", ""),
        )
        thread_map[a_id].cross_references.append(cross_ref)
        thread_map[b_id].cross_references.append(cross_ref)


def _inject_cross_ref_findings(
    response: OrchestratorResponse,
    threads: list[ResearchThread],
    cross_ref_result: dict,
) -> None:
    """Add consensus and contradiction findings from cross-referencing into the response."""
    for consensus in cross_ref_result.get("consensus_findings", []):
        response.key_findings.append({
            "agent": "DeepResearch:CrossRef",
            "statement": f"Multi-thread consensus: {consensus.get('theme', '')}",
            "confidence": consensus.get("confidence_boost", "high"),
            "rationale": f"Supported by threads: {', '.join(consensus.get('supporting_thread_ids', []))}",
            "source": "cross_reference",
        })
        response.facts.append(response.key_findings[-1])

    for contradiction in cross_ref_result.get("contradiction_flags", []):
        response.key_findings.append({
            "agent": "DeepResearch:CrossRef",
            "statement": f"Contradicting signals detected: {contradiction.get('theme', '')}",
            "confidence": "medium",
            "rationale": contradiction.get("explanation", ""),
            "source": "cross_reference",
        })
        response.interpretations.append(response.key_findings[-1])


def _thread_to_dict(thread: ResearchThread) -> dict:
    """Serialize a ResearchThread for JSON output."""
    return {
        "thread_id": thread.thread_id,
        "parent_id": thread.parent_id,
        "query": thread.query,
        "depth": thread.depth,
        "status": thread.status,
        "error": thread.error,
        "finding_count": len(thread.findings),
        "findings": [
            {
                "statement": f.statement,
                "type": f.type,
                "confidence": f.confidence,
                "rationale": f.rationale,
            }
            for f in thread.findings
        ],
        "sub_thread_ids": thread.sub_thread_ids,
        "cross_references": [
            {
                "source_thread_id": cr.source_thread_id,
                "target_thread_id": cr.target_thread_id,
                "relationship": cr.relationship,
                "explanation": cr.explanation,
            }
            for cr in thread.cross_references
        ],
    }
