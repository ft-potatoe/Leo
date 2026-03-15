import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.query_schema import QueryRequest, OrchestratorResponse
from orchestrator.orchestrator import Orchestrator
from orchestrator.agent_registry import AgentRegistry
from memory.memory_manager import MemoryManager
from agents.specialist_agents import (
    PricingAgent,
    PositioningAgent,
    WinLossAgent,
)
from agents.market_trends_agent import MarketTrendsAgent
from agents.competitive_agent import CompetitiveLandscapeAgent
from agents.adjacent_threat_agent import AdjacentThreatAgent

router = APIRouter()

# ── Bootstrap registry, memory, and orchestrator ───────────────────────────────
memory = MemoryManager()
registry = AgentRegistry()

registry.register(PricingAgent(), keywords=["pricing", "price", "cost", "plan"])
registry.register(CompetitiveLandscapeAgent(), keywords=["competitor", "competition", "competitive", "versus", "vs"])
registry.register(MarketTrendsAgent(), keywords=["market", "trend", "industry", "growth"])
registry.register(PositioningAgent(), keywords=["positioning", "messaging", "brand", "narrative"])
registry.register(WinLossAgent(), keywords=["loss", "win", "customer", "churn", "deal"])
registry.register(AdjacentThreatAgent(), keywords=["adjacent", "disruption", "threat", "entrant"])

orchestrator = Orchestrator(registry=registry, memory=memory)


# ── Standard JSON endpoints ───────────────────────────────────────────────────

@router.post("/query", response_model=OrchestratorResponse)
async def handle_query(request: QueryRequest) -> OrchestratorResponse:
    try:
        result = await orchestrator.run(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/deep", response_model=OrchestratorResponse)
async def handle_deep_query(request: QueryRequest) -> OrchestratorResponse:
    """
    Multi-hop deep research endpoint.

    Runs the recursive DeepResearchEngine that:
    1. Runs agents on the initial query
    2. Uses LLM to decompose findings into targeted sub-queries
    3. Spawns sub-threads in parallel per hop
    4. Cross-references findings across all threads for consensus/contradiction
    5. Returns enriched response including research_threads tree and depth_reached

    Accepts same QueryRequest body as /query. Additional optional fields:
    - max_depth (int, default 3): maximum recursion depth
    """
    try:
        result = await orchestrator.run_deep(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SSE Streaming endpoint ────────────────────────────────────────────────────

@router.post("/query/stream")
async def handle_stream_query(request: QueryRequest):
    """
    Server-Sent Events streaming endpoint.

    Streams intelligence events as they are produced:
      - agent_started:      {event, agent, timestamp}
      - agent_complete:     {event, agent, status, finding_count, timestamp}
      - synthesis_complete: {event, result, timestamp}
      - cache_hit:          {event, message, timestamp}
      - error:              {event, message, timestamp}

    Clients should connect with:
        EventSource (via POST with fetch + ReadableStream in browsers)
        or httpx / requests in Python with stream=True.

    The stream ends after synthesis_complete or error.
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def _run():
        try:
            await orchestrator.run(request, event_queue=queue)
        except Exception as e:
            await queue.put({
                "event": "error",
                "message": str(e),
                "timestamp": _now(),
            })
        finally:
            await queue.put(None)  # sentinel → close stream

    async def _generate():
        task = asyncio.create_task(_run())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=120.0)
                except asyncio.TimeoutError:
                    yield _sse({"event": "timeout", "message": "Orchestrator timed out"})
                    break

                if event is None:
                    break

                yield _sse(event)

                # Close stream after synthesis or error
                if event.get("event") in ("synthesis_complete", "error"):
                    break
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Cost / cache info endpoints ───────────────────────────────────────────────

@router.get("/cost")
async def get_cost_info():
    """Return cumulative token usage and estimated cost for this server process."""
    from tools.llm_client import get_session_token_usage
    return get_session_token_usage()


@router.get("/cache/stats")
async def get_cache_stats():
    """Return cache statistics."""
    from tools.cache import get_cache
    return get_cache().stats()


@router.delete("/cache")
async def clear_cache():
    """Flush the agent result cache."""
    from tools.cache import get_cache
    get_cache().clear_all()
    return {"status": "cleared"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
