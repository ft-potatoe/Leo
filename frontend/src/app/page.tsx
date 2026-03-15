"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ProductContextBar from "@/components/ProductContextBar";
import AgentStatusPanel from "@/components/AgentStatusPanel";
import SuggestedChips from "@/components/SuggestedChips";
import QueryCostIndicator from "@/components/QueryCostIndicator";
import ArtifactRenderer from "@/components/ArtifactRenderer";
import FindingsDisplay from "@/components/FindingsDisplay";
import SourceTrail from "@/components/SourceTrail";
import AuditTrail from "@/components/AuditTrail";
import { ChatMessage, ProductContext, AgentStatusInfo, OrchestratorResponse, QueryMetadata } from "@/types";
import { sendQuery } from "@/lib/api";
import { DEMO_AGENTS, STARTER_CHIPS, MOCK_RESPONSE } from "@/lib/mock-data";

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatusInfo[]>([]);
  const [agentPanelCollapsed, setAgentPanelCollapsed] = useState(false);
  const [sessionId] = useState(() => generateId());
  const [sessionCost, setSessionCost] = useState(0);
  const [currentQueryCost, setCurrentQueryCost] = useState(0);
  const [product, setProduct] = useState<ProductContext>({
    name: "Vector Agents",
    url: "vectoragents.ai",
  });
  const [suggestedChips, setSuggestedChips] = useState<string[]>(STARTER_CHIPS);
  const [useMock, setUseMock] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, agentStatuses, scrollToBottom]);

  // Simulate agent execution with staggered timing
  const simulateAgentExecution = useCallback((): Promise<AgentStatusInfo[]> => {
    return new Promise((resolve) => {
      const agents = DEMO_AGENTS.map((a) => ({ ...a }));
      setAgentStatuses([...agents]);
      setAgentPanelCollapsed(false);

      // Schedule of agent state changes for realistic demo
      const schedule = [
        { time: 100, agent: 0, status: "running" as const },
        { time: 200, agent: 4, status: "running" as const },
        { time: 800, agent: 1, status: "running" as const },
        { time: 1500, agent: 4, status: "done" as const, elapsed: 1.3 },
        { time: 2000, agent: 0, status: "done" as const, elapsed: 1.9 },
        { time: 2200, agent: 3, status: "running" as const },
        { time: 2500, agent: 5, status: "running" as const },
        { time: 3000, agent: 2, status: "running" as const },
        { time: 3400, agent: 1, status: "done" as const, elapsed: 2.6 },
        { time: 4000, agent: 3, status: "done" as const, elapsed: 1.8 },
        { time: 4500, agent: 5, status: "done" as const, elapsed: 2.0 },
        { time: 5200, agent: 2, status: "done" as const, elapsed: 2.2 },
      ];

      const timers: NodeJS.Timeout[] = [];
      const elapsed: Record<number, number> = {};

      // Start elapsed timers
      const startTimes: Record<number, number> = {};

      schedule.forEach(({ time, agent, status, elapsed: finalElapsed }) => {
        const timer = setTimeout(() => {
          if (status === "running") {
            startTimes[agent] = Date.now();
          }
          agents[agent].status = status;
          if (finalElapsed) {
            agents[agent].elapsed = finalElapsed;
            elapsed[agent] = finalElapsed;
          } else if (status === "running") {
            agents[agent].elapsed = 0;
          }
          setAgentStatuses([...agents]);
        }, time);
        timers.push(timer);
      });

      // Running elapsed counter
      const intervalTimer = setInterval(() => {
        let updated = false;
        agents.forEach((a, i) => {
          if (a.status === "running" && startTimes[i]) {
            a.elapsed = (Date.now() - startTimes[i]) / 1000;
            updated = true;
          }
        });
        if (updated) {
          setAgentStatuses([...agents]);
        }
      }, 100);

      // Resolve when all done
      const resolveTimer = setTimeout(() => {
        clearInterval(intervalTimer);
        resolve(agents);
      }, 5500);

      timers.push(resolveTimer);
    });
  }, []);

  const handleSubmit = async (query: string) => {
    if (!query.trim() || isProcessing) return;

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content: query.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsProcessing(true);
    const queryCost = 0.01 + Math.random() * 0.04;
    setCurrentQueryCost(queryCost);

    const startTime = Date.now();

    // Start agent animation
    const finalAgentStatuses = await simulateAgentExecution();

    let response: OrchestratorResponse;

    if (useMock) {
      response = { ...MOCK_RESPONSE, query: query.trim() };
    } else {
      try {
        response = await sendQuery({
          query: query.trim(),
          company_name: product.name,
          product_name: product.name,
          context: messages.length > 0
            ? `Previous queries: ${messages.filter((m) => m.role === "user").map((m) => m.content).join("; ")}`
            : undefined,
          session_id: sessionId,
        });
      } catch {
        // Fallback to mock on API error
        response = { ...MOCK_RESPONSE, query: query.trim() };
      }
    }

    const totalLatency = (Date.now() - startTime) / 1000;
    const totalSources = response.agent_outputs.reduce(
      (sum, ao) => sum + ao.evidence.length,
      0
    );

    const metadata: QueryMetadata = {
      timestamp: new Date(),
      agentsUsed: response.agent_outputs.map((ao) => ao.agent_name),
      sourcesHit: totalSources,
      totalLatency,
      estimatedCost: queryCost,
    };

    const assistantMessage: ChatMessage = {
      id: generateId(),
      role: "assistant",
      content: response.executive_summary,
      timestamp: new Date(),
      response,
      agentStatuses: finalAgentStatuses,
      metadata,
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setSessionCost((prev) => prev + queryCost);
    setSuggestedChips(response.follow_up_questions.slice(0, 3));
    setIsProcessing(false);

    // Auto-collapse agent panel after brief delay
    setTimeout(() => setAgentPanelCollapsed(true), 1500);
  };

  const allSources = messages
    .filter((m) => m.response)
    .flatMap((m) => m.response!.agent_outputs.flatMap((ao) => ao.evidence));

  return (
    <div className="h-screen flex flex-col bg-slate-950">
      {/* Product Context Bar */}
      <ProductContextBar product={product} onUpdate={setProduct} />

      {/* Query Cost Indicator */}
      <QueryCostIndicator
        queryCost={currentQueryCost}
        sessionCost={sessionCost}
        visible={messages.length > 0}
      />

      {/* Main Chat Area */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 lg:px-16 xl:px-32 py-6">
        {/* Empty State */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-8">
            <div className="text-center space-y-3">
              <h1 className="text-3xl font-bold text-slate-100">Leo</h1>
              <p className="text-slate-400 text-sm max-w-md">
                Growth intelligence powered by 6 specialist AI agents. Ask any strategic question
                about your market, competitors, pricing, or positioning.
              </p>
            </div>
            <SuggestedChips chips={suggestedChips} onSelect={handleSubmit} />
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useMock}
                  onChange={(e) => setUseMock(e.target.checked)}
                  className="rounded border-slate-600 bg-slate-800"
                />
                Demo mode (mock data)
              </label>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {message.role === "user" ? (
                <div className="max-w-xl bg-indigo-500/20 border border-indigo-500/30 rounded-2xl rounded-tr-sm px-4 py-3">
                  <p className="text-sm text-slate-200">{message.content}</p>
                </div>
              ) : (
                <div className="w-full space-y-4">
                  {/* Context indicator */}
                  {messages.filter((m) => m.role === "user").length > 1 && (
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500/50" />
                      Building on previous context
                    </div>
                  )}

                  {/* Executive Summary */}
                  <div className="bg-slate-900/50 border border-slate-800 rounded-2xl rounded-tl-sm px-5 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm text-slate-200 leading-relaxed">{message.content}</p>
                      {message.metadata && <AuditTrail metadata={message.metadata} />}
                    </div>
                  </div>

                  {/* Findings with fact/interpretation toggle */}
                  {message.response && (
                    <FindingsDisplay
                      facts={message.response.facts}
                      interpretations={message.response.interpretations}
                      recommendations={message.response.recommendations}
                    />
                  )}

                  {/* Artifacts */}
                  {message.response && message.response.artifacts.length > 0 && (
                    <ArtifactRenderer artifacts={message.response.artifacts} />
                  )}

                  {/* Source trail */}
                  {message.response && (
                    <SourceTrail
                      sources={message.response.agent_outputs.flatMap((ao) => ao.evidence)}
                    />
                  )}

                  {/* Degradation notice */}
                  {message.response && message.response.errors.length > 0 && (
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-sm text-amber-300">
                      This brief was generated with partial data.{" "}
                      {message.response.errors.join(". ")}
                      <button className="ml-2 text-amber-400 underline hover:text-amber-200">
                        Retry
                      </button>
                    </div>
                  )}

                  {/* Agent output errors */}
                  {message.response &&
                    message.response.agent_outputs
                      .filter((ao) => ao.status === "error" || ao.status === "timeout")
                      .map((ao) => (
                        <div
                          key={ao.agent_name}
                          className="bg-red-500/10 border border-red-500/20 rounded-lg p-2 text-xs text-red-300"
                        >
                          [✗] {ao.agent_name} — {ao.status}
                          {ao.errors.length > 0 && `: ${ao.errors[0]}`}
                        </div>
                      ))}
                </div>
              )}
            </motion.div>
          ))}

          {/* Agent Status Panel (during processing) */}
          <AnimatePresence>
            {isProcessing && (
              <div className="flex justify-start">
                <AgentStatusPanel
                  agents={agentStatuses}
                  collapsed={agentPanelCollapsed}
                  onToggle={() => setAgentPanelCollapsed(!agentPanelCollapsed)}
                  totalTime={agentStatuses.reduce((sum, a) => sum + a.elapsed, 0)}
                  totalSources={allSources.length}
                />
              </div>
            )}
          </AnimatePresence>

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Suggested Chips (after messages) */}
      {!isProcessing && messages.length > 0 && suggestedChips.length > 0 && (
        <div className="px-4 md:px-8 lg:px-16 xl:px-32 pb-2">
          <div className="max-w-4xl mx-auto">
            <SuggestedChips chips={suggestedChips} onSelect={handleSubmit} />
          </div>
        </div>
      )}

      {/* Input Bar */}
      <div className="border-t border-slate-800 bg-slate-950/80 backdrop-blur-sm px-4 md:px-8 lg:px-16 xl:px-32 py-4">
        <div className="max-w-4xl mx-auto">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(input);
            }}
            className="flex items-center gap-3"
          >
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your market, competitors, pricing, positioning..."
                disabled={isProcessing}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 disabled:opacity-50 transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isProcessing}
              className="px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white text-sm font-medium rounded-xl transition-colors"
            >
              {isProcessing ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-slate-500 border-t-indigo-400 rounded-full animate-spin" />
                  Analysing
                </span>
              ) : (
                "Send"
              )}
            </button>
          </form>
          {messages.length > 0 && (
            <div className="flex justify-center mt-2">
              <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useMock}
                  onChange={(e) => setUseMock(e.target.checked)}
                  className="rounded border-slate-600 bg-slate-800"
                />
                Demo mode
              </label>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
