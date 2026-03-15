"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Evidence } from "@/types";

interface Props {
  sources: Evidence[];
}

const typeColors: Record<string, string> = {
  web_search: "text-emerald-400",
  reddit: "text-orange-400",
  hackernews: "text-amber-400",
  scraped_page: "text-blue-400",
};

const confidenceColors: Record<string, string> = {
  verified: "bg-emerald-500",
  inferred: "bg-amber-500",
  "low-signal": "bg-red-500",
};

function getSourceConfidence(source: Evidence): string {
  if (source.source_type === "web_search" && source.url) return "verified";
  if (source.source_type === "scraped_page") return "verified";
  if (source.source_type === "reddit" || source.source_type === "hackernews") return "inferred";
  return "low-signal";
}

function getSourceCategory(type: string): string {
  const map: Record<string, string> = {
    web_search: "News & Research",
    scraped_page: "Product Pages",
    reddit: "Reviews & Discussions",
    hackernews: "Reviews & Discussions",
  };
  return map[type] || "Other";
}

function getDomain(url: string): string {
  try {
    return url.replace(/^https?:\/\//, "").split("/")[0];
  } catch {
    return url;
  }
}

export default function SourceTrail({ sources }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!sources?.length) return null;

  const grouped = (sources ?? []).reduce<Record<string, Evidence[]>>((acc, s) => {
    const cat = getSourceCategory(s.source_type);
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(s);
    return acc;
  }, {});

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-slate-400 hover:text-slate-300 transition-colors"
      >
        Sources ({sources.length}) {expanded ? "▾" : "▸"}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 space-y-3"
          >
            {Object.entries(grouped).map(([category, items]) => (
              <div key={category}>
                <h5 className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">{category}</h5>
                <div className="space-y-1">
                  {items.map((s, i) => {
                    const conf = getSourceConfidence(s);
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className={`w-1.5 h-1.5 rounded-full ${confidenceColors[conf]}`} />
                        <span className={typeColors[s.source_type] || "text-slate-400"}>
                          {s.title || getDomain(s.url)}
                        </span>
                        <span className="text-slate-600">—</span>
                        <span className="text-slate-500">{getDomain(s.url)}</span>
                        {s.collected_at && (
                          <span className="text-slate-600 ml-auto">
                            retrieved {new Date(s.collected_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
            <div className="flex gap-3 text-xs text-slate-500">
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> verified</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> inferred</span>
              <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-red-500" /> low-signal</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
