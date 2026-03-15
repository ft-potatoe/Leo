"use client";

import { motion } from "framer-motion";

interface InsightItem {
  insight: string;
  frequency: number;
  sentiment: number;
  sources: string[];
}

interface Props {
  payload: {
    wins: InsightItem[];
    losses: InsightItem[];
    buyer_summary: string;
  };
}

function SentimentBar({ value }: { value: number }) {
  const width = Math.abs(value) * 100;
  const isPositive = value > 0;
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${isPositive ? "bg-emerald-500" : "bg-red-500"}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-xs text-slate-500">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

function InsightCard({ item, type }: { item: InsightItem; type: "win" | "loss" }) {
  return (
    <div className="bg-slate-800/40 rounded-lg p-3 space-y-2">
      <p className="text-sm text-slate-200">{item.insight}</p>
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">Mentioned {item.frequency} times</span>
        <SentimentBar value={item.sentiment} />
      </div>
      <div className="flex flex-wrap gap-1">
        {item.sources?.map((s) => (
          <span
            key={s}
            className={`text-xs px-2 py-0.5 rounded ${
              type === "win" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
            }`}
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function WinLossAnalysis({ payload }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 space-y-4"
    >
      <h3 className="text-sm font-semibold text-slate-200">Win / Loss Analysis</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-3">
            Why deals are won
          </h4>
          <div className="space-y-2">
            {payload.wins?.map((item, i) => (
              <InsightCard key={i} item={item} type="win" />
            ))}
          </div>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-3">
            Why deals are lost
          </h4>
          <div className="space-y-2">
            {payload.losses?.map((item, i) => (
              <InsightCard key={i} item={item} type="loss" />
            ))}
          </div>
        </div>
      </div>
      <div className="bg-slate-800/30 rounded-lg p-3 border-l-2 border-indigo-500">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
          Buyer&apos;s Perspective Summary
        </h4>
        <p className="text-sm text-slate-300 leading-relaxed">{payload.buyer_summary}</p>
      </div>
    </motion.div>
  );
}
