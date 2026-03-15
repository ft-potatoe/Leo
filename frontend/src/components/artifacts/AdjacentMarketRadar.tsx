"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

interface RadarNode {
  name: string;
  description: string;
  relevance: string;
  threat_timeline: string;
}

interface RadarRing {
  label: string;
  nodes: RadarNode[];
}

interface Props {
  payload: {
    rings: RadarRing[];
  };
}

const ringColors = [
  { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", fill: "rgba(239,68,68,0.15)" },
  { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", fill: "rgba(245,158,11,0.15)" },
  { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", fill: "rgba(59,130,246,0.15)" },
];

export default function AdjacentMarketRadar({ payload }: Props) {
  const [expandedNode, setExpandedNode] = useState<string | null>(null);

  const cx = 250;
  const cy = 200;
  const radii = [80, 140, 200];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4 space-y-4"
    >
      <h3 className="text-sm font-semibold text-slate-200">Adjacent Market Radar</h3>
      <p className="text-xs text-slate-400">Markets converging with yours</p>

      <div className="flex justify-center">
        <svg viewBox="0 0 500 400" className="w-full max-w-lg">
          {/* Concentric circles */}
          {radii.map((r, i) => (
            <g key={i}>
              <circle cx={cx} cy={cy} r={r} fill="none" stroke="#334155" strokeDasharray="4 4" strokeWidth={1} />
              <text x={cx + r + 5} y={cy - 5} fill="#64748b" fontSize={9}>
                {payload.rings[i]?.label}
              </text>
            </g>
          ))}

          {/* Center dot */}
          <circle cx={cx} cy={cy} r={6} fill="#6366f1" />
          <text x={cx} y={cy + 18} fill="#a5b4fc" fontSize={10} textAnchor="middle" fontWeight={600}>
            You
          </text>

          {/* Nodes */}
          {payload.rings.map((ring, ringIdx) => {
            const radius = radii[ringIdx];
            const angleStep = (2 * Math.PI) / Math.max(ring.nodes.length, 1);
            const startAngle = -Math.PI / 2;

            return ring.nodes.map((node, nodeIdx) => {
              const angle = startAngle + nodeIdx * angleStep + ringIdx * 0.5;
              const nx = cx + radius * Math.cos(angle);
              const ny = cy + radius * Math.sin(angle);
              const colors = ringColors[ringIdx];
              const isExpanded = expandedNode === node.name;

              return (
                <g
                  key={node.name}
                  onClick={() => setExpandedNode(isExpanded ? null : node.name)}
                  style={{ cursor: "pointer" }}
                >
                  <circle cx={nx} cy={ny} r={isExpanded ? 10 : 7} fill={colors.fill} stroke={colors.fill} strokeWidth={2} />
                  <circle cx={nx} cy={ny} r={4} fill={colors.fill.replace("0.15", "0.6")} />
                  <text
                    x={nx}
                    y={ny - 14}
                    fill="#94a3b8"
                    fontSize={10}
                    textAnchor="middle"
                    fontWeight={isExpanded ? 600 : 400}
                  >
                    {node.name}
                  </text>
                </g>
              );
            });
          })}
        </svg>
      </div>

      {/* Expanded node detail */}
      <AnimatePresence>
        {expandedNode && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-slate-800/40 rounded-lg p-3 space-y-1"
          >
            {payload.rings.flatMap((r) => r.nodes).filter((n) => n.name === expandedNode).map((node) => (
              <div key={node.name}>
                <h4 className="text-sm font-medium text-slate-200">{node.name}</h4>
                <p className="text-xs text-slate-400">{node.description}</p>
                <p className="text-xs text-slate-300 mt-1">{node.relevance}</p>
                <span className="inline-block mt-1 text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
                  Threat timeline: {node.threat_timeline}
                </span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {payload.rings.map((ring, i) => (
          <div key={ring.label} className="flex items-center gap-1.5">
            <div className={`w-3 h-3 rounded-full ${ringColors[i].bg} ${ringColors[i].border} border`} />
            <span className="text-xs text-slate-400">{ring.label}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
