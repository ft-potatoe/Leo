"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Finding } from "@/types";

interface Props {
  facts: Finding[];
  interpretations: Finding[];
  recommendations: Finding[];
}

type FilterMode = "all" | "facts" | "analysis";

const confidenceBadge: Record<string, string> = {
  high: "bg-emerald-500/20 text-emerald-400",
  medium: "bg-amber-500/20 text-amber-400",
  low: "bg-red-500/20 text-red-400",
};

export default function FindingsDisplay({ facts, interpretations, recommendations }: Props) {
  const [filter, setFilter] = useState<FilterMode>("all");

  const showFacts = filter === "all" || filter === "facts";
  const showAnalysis = filter === "all" || filter === "analysis";

  return (
    <div className="space-y-3">
      {/* Toggle */}
      <div className="flex gap-1 bg-slate-800/50 rounded-lg p-0.5 w-fit">
        {(["all", "facts", "analysis"] as FilterMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setFilter(mode)}
            className={`px-3 py-1 rounded-md text-xs transition-colors ${
              filter === mode
                ? "bg-indigo-500/20 text-indigo-300"
                : "text-slate-400 hover:text-slate-300"
            }`}
          >
            {mode === "all" ? "Show all" : mode === "facts" ? "Facts only" : "Analysis only"}
          </button>
        ))}
      </div>

      {/* Facts */}
      {showFacts && facts.length > 0 && (
        <div className="space-y-2">
          {facts.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="border-l-2 border-blue-500 bg-blue-500/5 rounded-r-lg p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-slate-200">{f.statement}</p>
                <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${confidenceBadge[f.confidence]}`}>
                  {f.confidence}
                </span>
              </div>
              {f.rationale && <p className="text-xs text-slate-500 mt-1">{f.rationale}</p>}
            </motion.div>
          ))}
        </div>
      )}

      {/* Interpretations */}
      {showAnalysis && interpretations.length > 0 && (
        <div className="space-y-2">
          {interpretations.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="border-l-2 border-slate-500 bg-slate-500/5 rounded-r-lg p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-slate-300 italic">{f.statement}</p>
                <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${confidenceBadge[f.confidence]}`}>
                  {f.confidence}
                </span>
              </div>
              {f.rationale && <p className="text-xs text-slate-500 mt-1">{f.rationale}</p>}
            </motion.div>
          ))}
        </div>
      )}

      {/* Recommendations */}
      {showAnalysis && recommendations.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-400">Recommendations</h4>
          {recommendations.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="border-l-2 border-indigo-500 bg-indigo-500/5 rounded-r-lg p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-slate-200">{f.statement}</p>
                <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${confidenceBadge[f.confidence]}`}>
                  {f.confidence}
                </span>
              </div>
              {f.rationale && <p className="text-xs text-slate-500 mt-1">{f.rationale}</p>}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
