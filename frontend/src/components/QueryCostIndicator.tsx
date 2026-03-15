"use client";

import { motion, AnimatePresence } from "framer-motion";

interface Props {
  queryCost: number;
  sessionCost: number;
  visible: boolean;
}

export default function QueryCostIndicator({ queryCost, sessionCost, visible }: Props) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          className="fixed right-4 top-1/2 -translate-y-1/2 z-30"
        >
          <div className="bg-slate-900/90 border border-slate-700/50 rounded-lg p-3 backdrop-blur-sm text-xs space-y-1">
            <div className="text-slate-400">
              This query: <span className="text-slate-200 font-mono">~${queryCost.toFixed(2)}</span>
            </div>
            <div className="text-slate-400">
              Session: <span className="text-slate-200 font-mono">~${sessionCost.toFixed(2)}</span>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
