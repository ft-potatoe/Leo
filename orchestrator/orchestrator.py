import asyncio
import traceback
from datetime import datetime, timezone

from orchestrator.agent_registry import AgentRegistry
from agents.confidence_agent import ConfidenceAgent
from agents.confidence_verifier_agent import ConfidenceVerifierAgent
from agents.synthesizer_agent import SynthesizerAgent
from memory.memory_manager import MemoryManager
from schemas.agent_output import AgentOutput
from schemas.query_schema import QueryRequest, OrchestratorResponse
from tools.cache import get_cache

AGENT_TIMEOUT_SECONDS = 60


class Orchestrator:
    """
    Core orchestration engine.

    Pipeline:
        1. Cache check  – return cached result for identical (product, query) pairs
        2. Agent selection  – pick relevant specialists based on query keywords
        3. Parallel execution – run selected agents concurrently (with timeout)
           → emits agent_started / agent_complete SSE events via event_queue
        4. Result collection – gather successes and capture failures
        5. Confidence processing – score outputs via ConfidenceAgent
        6. Synthesis – merge results via SynthesizerAgent
           → emits synthesis_complete SSE event
        7. Cache store – persist result for 1 hour
        8. Memory update – store session context for follow-ups
    """

    def __init__(self, registry: AgentRegistry, memory: MemoryManager) -> None:
        self.registry = registry
        self.memory = memory
        self.confidence_agent = ConfidenceAgent()
        self.confidence_verifier = ConfidenceVerifierAgent()
        self.synthesizer_agent = SynthesizerAgent()
        self._cache = get_cache()

    # ── Public entry points ───────────────────────────────────────────────────

    async def run(
        self,
        request: QueryRequest,
        event_queue: asyncio.Queue | None = None,
    ) -> OrchestratorResponse:
        """
        Single-pass orchestration.

        Args:
            request: The query request.
            event_queue: Optional asyncio.Queue for SSE streaming events.
                         Receives dicts with {"event": str, ...}.
                         Caller must send a sentinel None after this coroutine finishes.
        """
        product_key = request.company_name or request.product_name or ""

        # ── 0. Cache check ──────────────────────────────────────────────────
        cached = self._cache.get(product_key, request.query)
        if cached is not None:
            if event_queue:
                await event_queue.put({
                    "event": "cache_hit",
                    "message": "Returning cached result",
                    "timestamp": _now(),
                })
                await event_queue.put({"event": "synthesis_complete", "result": cached, "timestamp": _now()})
            return OrchestratorResponse(**cached)

        # ── 1. Agent selection ──────────────────────────────────────────────
        selected_agents = self.registry.resolve_agents(request.query)

        # Retrieve prior context for follow-up enrichment
        prior_context = self.memory.get_context(request.session_id)
        if prior_context and request.context is None:
            request.context = prior_context.get("last_summary", "")

        # ── 2. Parallel execution with streaming ────────────────────────────
        async def _run_agent(agent):
            if event_queue:
                await event_queue.put({
                    "event": "agent_started",
                    "agent": agent.name,
                    "timestamp": _now(),
                })
            try:
                result = await asyncio.wait_for(
                    agent.run(request), timeout=AGENT_TIMEOUT_SECONDS
                )
                if event_queue:
                    await event_queue.put({
                        "event": "agent_complete",
                        "agent": agent.name,
                        "status": "success",
                        "finding_count": len(result.findings),
                        "timestamp": _now(),
                    })
                return result
            except asyncio.TimeoutError as e:
                if event_queue:
                    await event_queue.put({
                        "event": "agent_complete",
                        "agent": agent.name,
                        "status": "timeout",
                        "timestamp": _now(),
                    })
                raise asyncio.TimeoutError(f"{agent.name} timed out") from e
            except Exception as e:
                if event_queue:
                    await event_queue.put({
                        "event": "agent_complete",
                        "agent": agent.name,
                        "status": "error",
                        "error": str(e),
                        "timestamp": _now(),
                    })
                raise

        tasks = [_run_agent(agent) for agent in selected_agents]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # ── 3. Result collection ────────────────────────────────────────────
        successful_outputs: list[AgentOutput] = []
        errors: list[str] = []

        for agent, result in zip(selected_agents, raw_results):
            if isinstance(result, Exception):
                error_msg = f"{agent.name}: {type(result).__name__} – {result}"
                errors.append(error_msg)
                successful_outputs.append(
                    AgentOutput(agent_name=agent.name, status="error", errors=[str(result)])
                )
            else:
                successful_outputs.append(result)

        # ── 4. Confidence processing ────────────────────────────────────────
        confidence_overview = self.confidence_agent.score_outputs(successful_outputs)
        verifier_output = self.confidence_verifier.verify_outputs(successful_outputs)
        successful_outputs.append(verifier_output)

        # ── 5. Synthesis ────────────────────────────────────────────────────
        synthesis = await self.synthesizer_agent.synthesize_async(
            query=request,
            outputs=successful_outputs,
            confidence_overview=confidence_overview,
        )

        # ── 6. Build response ───────────────────────────────────────────────
        from tools.llm_client import get_session_token_usage
        cost_info = get_session_token_usage()

        response = OrchestratorResponse(
            session_id=request.session_id,
            query=request.query,
            executive_summary=synthesis["executive_summary"],
            key_findings=synthesis["key_findings"],
            facts=synthesis["facts"],
            interpretations=synthesis["interpretations"],
            recommendations=synthesis["recommendations"],
            confidence_overview=synthesis["confidence_overview"],
            artifacts=synthesis["artifacts"],
            follow_up_questions=synthesis["follow_up_questions"],
            agent_outputs=[o.model_dump() for o in successful_outputs],
            errors=errors,
        )

        # Attach cost metadata to the response (stored in first artifact slot if no other way)
        response_dict = response.model_dump()
        response_dict["cost_info"] = cost_info

        # ── 7. Cache store ──────────────────────────────────────────────────
        self._cache.set(product_key, request.query, response_dict)

        # ── 8. Memory update ────────────────────────────────────────────────
        self.memory.store(
            session_id=request.session_id,
            query=request.query,
            summary=synthesis["executive_summary"],
        )

        # ── SSE: synthesis complete ─────────────────────────────────────────
        if event_queue:
            await event_queue.put({
                "event": "synthesis_complete",
                "result": response_dict,
                "timestamp": _now(),
            })

        return response

    async def run_deep(self, request: QueryRequest) -> OrchestratorResponse:
        """
        Multi-hop deep research entry point.
        Delegates to DeepResearchEngine which recursively decomposes
        the query into sub-threads, cross-references findings, and
        returns an enriched OrchestratorResponse with the full thread tree.
        """
        from orchestrator.deep_research_engine import DeepResearchEngine
        engine = DeepResearchEngine(self)
        response, threads, depth = await engine.run_deep(request)
        return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
