"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AgentStatusInfo, AgentStatus } from "@/types";

interface Props {
  agents: AgentStatusInfo[];
  collapsed: boolean;
  onToggle: () => void;
  totalTime?: number;
  totalSources?: number;
}

const statusIcon: Record<AgentStatus, string> = {
  queued: "○",
  running: "◉",
  done: "✓",
  failed: "✗",
  partial: "!",
};

const statusColor: Record<AgentStatus, string> = {
  queued: "text-slate-500",
  running: "text-indigo-400",
  done: "text-emerald-400",
  failed: "text-red-400",
  partial: "text-amber-400",
};

const statusLabel: Record<AgentStatus, string> = {
  queued: "queued",
  running: "running",
  done: "done",
  failed: "failed",
  partial: "partial",
};

export default function AgentStatusPanel({ agents, collapsed, onToggle, totalTime, totalSources }: Props) {
  const allDone = agents.every((a) => a.status === "done" || a.status === "failed" || a.status === "partial");

  if (collapsed && allDone) {
    return (
      <motion.button
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        onClick={onToggle}
        className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-800/80 border border-slate-700 text-sm text-slate-300 hover:bg-slate-700/80 transition-colors"
      >
        <span className="text-emerald-400">✓</span>
        <span>
          {agents.length} agents completed in {totalTime?.toFixed(1)}s
          {totalSources ? ` · ${totalSources} sources analysed` : ""}
        </span>
      </motion.button>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="bg-slate-900/90 border border-slate-700/50 rounded-xl p-4 backdrop-blur-sm w-full max-w-lg"
      >
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Agent Pipeline</h3>
          {allDone && (
            <button onClick={onToggle} className="text-xs text-slate-500 hover:text-slate-300">
              Collapse
            </button>
          )}
        </div>
        <div className="space-y-2">
          {agents.map((agent, i) => (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`flex items-center gap-3 py-1.5 px-2 rounded-lg ${
                agent.status === "running" ? "bg-indigo-500/10 agent-running" : ""
              }`}
            >
              <span className={`text-sm font-mono ${statusColor[agent.status]}`}>
                [{statusIcon[agent.status]}]
              </span>
              <span className="text-sm text-slate-300 flex-1">{agent.displayName}</span>
              <span className="text-xs text-slate-500 font-mono flex items-center gap-1.5">
                <span
                  className={`inline-block w-16 h-0.5 rounded ${
                    agent.status === "running"
                      ? "bg-indigo-500/50"
                      : agent.status === "done"
                      ? "bg-emerald-500/30"
                      : agent.status === "failed"
                      ? "bg-red-500/30"
                      : "bg-slate-700"
                  }`}
                />
                {agent.status === "running" || agent.status === "done" || agent.status === "partial"
                  ? `${agent.elapsed.toFixed(1)}s`
                  : statusLabel[agent.status]}
                {agent.status === "failed" && agent.error && (
                  <span className="text-red-400 ml-1">— {agent.error}</span>
                )}
                {agent.status === "partial" && agent.error && (
                  <span className="text-amber-400 ml-1">— {agent.error}</span>
                )}
              </span>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
