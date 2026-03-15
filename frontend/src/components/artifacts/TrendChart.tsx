"use client";

import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from "recharts";

interface DataPoint {
  month: string;
  value: number;
  event: string | null;
}

interface Props {
  payload: {
    title: string;
    data: DataPoint[];
    yAxisLabel: string;
    sourceCount: number;
    confidence: string;
  };
}

const confidenceBadge: Record<string, string> = {
  high: "bg-emerald-500/20 text-emerald-400",
  medium: "bg-amber-500/20 text-amber-400",
  low: "bg-red-500/20 text-red-400",
};

export default function TrendChart({ payload }: Props) {
  const eventsData = payload.data.filter((d) => d.event);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-200">{payload.title}</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Based on {payload.sourceCount} sources</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${confidenceBadge[payload.confidence]}`}>
            confidence: {payload.confidence}
          </span>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={payload.data} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="month"
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={{ stroke: "#334155" }}
              tickLine={{ stroke: "#334155" }}
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={{ stroke: "#334155" }}
              tickLine={{ stroke: "#334155" }}
              label={{ value: payload.yAxisLabel, angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#e2e8f0",
                fontSize: "12px",
              }}
              formatter={(value) => [`$${value}M`, "Market ARR"]}
              labelFormatter={(label) => {
                const point = payload.data.find((d) => d.month === label);
                return point?.event ? `${label}\n📌 ${point.event}` : label;
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ fill: "#6366f1", r: 3 }}
              activeDot={{ r: 5, fill: "#818cf8" }}
            />
            {eventsData.map((d) => (
              <ReferenceDot
                key={d.month}
                x={d.month}
                y={d.value}
                r={6}
                fill="#f59e0b"
                stroke="#fbbf24"
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      {eventsData.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {eventsData.map((d) => (
            <span key={d.month} className="text-xs px-2 py-1 rounded bg-amber-500/10 text-amber-400">
              📌 {d.event}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}
