"use client";

import { motion } from "framer-motion";
import SourceTrail from "../SourceTrail";

interface Competitor {
  name: string;
  positioning: string;
  strengths: string[];
  weaknesses: string[];
  threat_level: "high" | "medium" | "low";
  sources: string[];
}

interface Props {
  payload: { competitors: Competitor[] };
}

const threatBadge = {
  high: "bg-red-500/20 text-red-400 border-red-500/30",
  medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  low: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

export default function CompetitiveScorecard({ payload }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-900/60 border border-slate-700/50 rounded-xl overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-slate-700/50">
        <h3 className="text-sm font-semibold text-slate-200">Competitive Scorecard</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700/50">
              <th className="text-left px-4 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">Competitor</th>
              <th className="text-left px-4 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">Positioning</th>
              <th className="text-left px-4 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">Strengths</th>
              <th className="text-left px-4 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">Weaknesses</th>
              <th className="text-left px-4 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">Threat</th>
            </tr>
          </thead>
          <tbody>
            {payload.competitors.map((c, i) => (
              <tr key={c.name} className={`border-b border-slate-800/50 ${i % 2 === 0 ? "bg-slate-800/20" : ""}`}>
                <td className="px-4 py-3 font-medium text-slate-200 whitespace-nowrap">{c.name}</td>
                <td className="px-4 py-3 text-slate-400 max-w-[200px]">{c.positioning}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {c.strengths.map((s) => (
                      <span key={s} className="inline-block px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs">
                        {s}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {c.weaknesses.map((w) => (
                      <span key={w} className="inline-block px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 text-xs">
                        {w}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full border text-xs font-medium ${threatBadge[c.threat_level]}`}>
                    {c.threat_level.charAt(0).toUpperCase() + c.threat_level.slice(1)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2">
        <SourceTrail
          sources={payload.competitors.flatMap((c) =>
            c.sources.map((s) => ({ url: s, title: s, source_type: "web_search", collected_at: new Date().toISOString(), snippet: "", entity: c.name }))
          )}
        />
      </div>
    </motion.div>
  );
}
