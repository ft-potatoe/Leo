"use client";

import { motion } from "framer-motion";
import { useState } from "react";

interface BriefItem {
  claim: string;
  confidence: "high" | "medium" | "low";
  source_count: number;
  sources: string[];
}

interface Props {
  payload: {
    executive_summary: string;
    opportunities: BriefItem[];
    risks: BriefItem[];
    recommended_bets: BriefItem[];
  };
}

const confidenceBadge: Record<string, string> = {
  high: "bg-emerald-500/20 text-emerald-400",
  medium: "bg-amber-500/20 text-amber-400",
  low: "bg-red-500/20 text-red-400",
};

function BriefSection({ title, items, icon }: { title: string; items: BriefItem[]; icon: string }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
        {icon} {title}
      </h4>
      <div className="space-y-2">
        {items?.map((item, i) => (
          <div key={i} className="bg-slate-800/40 rounded-lg p-3">
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm text-slate-200 flex-1">{item.claim}</p>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`text-xs px-2 py-0.5 rounded-full ${confidenceBadge[item.confidence]}`}>
                  {item.confidence}
                </span>
                <span className="text-xs text-slate-500">{item.source_count} sources</span>
              </div>
            </div>
            <button
              onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
              className="text-xs text-indigo-400 hover:text-indigo-300 mt-2"
            >
              {expandedIdx === i ? "Hide sources" : "Show sources"}
            </button>
            {expandedIdx === i && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="mt-2 flex flex-wrap gap-1"
              >
                {item.sources?.map((s) => (
                  <span key={s} className="text-xs px-2 py-0.5 rounded bg-slate-700/50 text-slate-400">
                    {s}
                  </span>
                ))}
              </motion.div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function StrategicBrief({ payload }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 space-y-4"
    >
      <h3 className="text-sm font-semibold text-slate-200">Strategic Brief</h3>
      <div className="bg-slate-800/30 rounded-lg p-3">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Executive Summary</h4>
        <p className="text-sm text-slate-300 leading-relaxed">{payload.executive_summary}</p>
      </div>
      <BriefSection title="Top 3 Opportunities" items={payload.opportunities} icon="🟢" />
      <BriefSection title="Top 3 Risks" items={payload.risks} icon="🔴" />
      <BriefSection title="Recommended Bets" items={payload.recommended_bets} icon="🎯" />
    </motion.div>
  );
}
