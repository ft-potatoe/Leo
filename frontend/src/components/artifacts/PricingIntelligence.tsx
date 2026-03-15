"use client";

import { motion } from "framer-motion";

interface CompetitorPricing {
  name: string;
  model: string;
  entry_price: string;
  enterprise_price: string;
  packaging: string;
}

interface WTPSignal {
  signal: string;
  confidence: "high" | "medium" | "low";
}

interface Props {
  payload: {
    competitors: CompetitorPricing[];
    willingness_to_pay: WTPSignal[];
    gaps: string[];
  };
}

const confidenceBadge: Record<string, string> = {
  high: "bg-emerald-500/20 text-emerald-400",
  medium: "bg-amber-500/20 text-amber-400",
  low: "bg-red-500/20 text-red-400",
};

export default function PricingIntelligence({ payload }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 space-y-4"
    >
      <h3 className="text-sm font-semibold text-slate-200">Pricing Intelligence</h3>

      {/* Pricing Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700/50">
              <th className="text-left px-3 py-2 text-xs font-medium text-slate-400 uppercase">Competitor</th>
              <th className="text-left px-3 py-2 text-xs font-medium text-slate-400 uppercase">Model</th>
              <th className="text-left px-3 py-2 text-xs font-medium text-slate-400 uppercase">Entry Price</th>
              <th className="text-left px-3 py-2 text-xs font-medium text-slate-400 uppercase">Enterprise</th>
              <th className="text-left px-3 py-2 text-xs font-medium text-slate-400 uppercase">Packaging</th>
            </tr>
          </thead>
          <tbody>
            {payload.competitors.map((c, i) => (
              <tr key={c.name} className={`border-b border-slate-800/50 ${i % 2 === 0 ? "bg-slate-800/20" : ""}`}>
                <td className="px-3 py-2 text-slate-200 font-medium">{c.name}</td>
                <td className="px-3 py-2">
                  <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-xs">{c.model}</span>
                </td>
                <td className="px-3 py-2 text-slate-300 font-mono text-xs">{c.entry_price}</td>
                <td className="px-3 py-2 text-slate-300 font-mono text-xs">{c.enterprise_price}</td>
                <td className="px-3 py-2 text-slate-400 text-xs">{c.packaging}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Willingness to Pay */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          Willingness-to-Pay Signals
        </h4>
        <div className="space-y-2">
          {payload.willingness_to_pay.map((s, i) => (
            <div key={i} className="flex items-start gap-2 bg-slate-800/30 rounded-lg p-2">
              <span className="text-slate-500 mt-0.5">•</span>
              <span className="text-sm text-slate-300 flex-1">{s.signal}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${confidenceBadge[s.confidence]}`}>
                {s.confidence}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Gaps */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          Pricing Gaps & Opportunities
        </h4>
        <div className="space-y-1.5">
          {payload.gaps.map((gap, i) => (
            <div key={i} className="flex items-start gap-2 bg-emerald-500/5 border-l-2 border-emerald-500/30 rounded-r-lg p-2">
              <span className="text-emerald-500 mt-0.5 shrink-0">▸</span>
              <span className="text-sm text-emerald-300">{gap}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
