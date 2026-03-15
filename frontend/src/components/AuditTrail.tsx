"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { QueryMetadata } from "@/types";

interface Props {
  metadata: QueryMetadata;
}

export default function AuditTrail({ metadata }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="inline-block relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-500 hover:text-slate-300 hover:border-slate-500 transition-colors"
        title="Query audit trail"
      >
        i
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="absolute bottom-full right-0 mb-2 bg-slate-900 border border-slate-700 rounded-lg p-3 w-64 z-50 shadow-xl"
          >
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Query Audit Trail</h4>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Timestamp</span>
                <span className="text-slate-300">{metadata.timestamp.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Agents used</span>
                <span className="text-slate-300">{metadata.agentsUsed.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Sources hit</span>
                <span className="text-slate-300">{metadata.sourcesHit}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Total latency</span>
                <span className="text-slate-300">{metadata.totalLatency.toFixed(1)}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Est. cost</span>
                <span className="text-slate-300 font-mono">${metadata.estimatedCost.toFixed(2)}</span>
              </div>
              <div className="pt-1 border-t border-slate-800">
                <span className="text-slate-500">Agents:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {metadata.agentsUsed.map((a) => (
                    <span key={a} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-xs">
                      {a}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
