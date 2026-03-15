"use client";

import { Artifact } from "@/types";
import CompetitiveScorecard from "./artifacts/CompetitiveScorecard";
import TrendChart from "./artifacts/TrendChart";
import PositioningMap from "./artifacts/PositioningMap";
import StrategicBrief from "./artifacts/StrategicBrief";
import WinLossAnalysis from "./artifacts/WinLossAnalysis";
import PricingIntelligence from "./artifacts/PricingIntelligence";
import AdjacentMarketRadar from "./artifacts/AdjacentMarketRadar";

interface Props {
  artifacts: Artifact[];
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function ArtifactRenderer({ artifacts }: Props) {
  return (
    <div className="space-y-4">
      {artifacts.map((artifact, i) => {
        switch (artifact.artifact_type) {
          case "competitive_scorecard":
          case "competitor_matrix":
          case "feature_comparison":
            return <CompetitiveScorecard key={i} payload={artifact.payload as any} />;
          case "trend_chart":
          case "trend_timeline":
          case "signal_summary":
            return <TrendChart key={i} payload={artifact.payload as any} />;
          case "positioning_map":
          case "positioning_summary":
          case "message_gap_heatmap":
            return <PositioningMap key={i} payload={artifact.payload as any} />;
          case "strategic_brief":
            return <StrategicBrief key={i} payload={artifact.payload as any} />;
          case "win_loss_analysis":
          case "objection_map":
          case "buyer_pain_clusters":
            return <WinLossAnalysis key={i} payload={artifact.payload as any} />;
          case "pricing_intelligence":
          case "pricing_table":
          case "packaging_comparison":
            return <PricingIntelligence key={i} payload={artifact.payload as any} />;
          case "adjacent_market_radar":
          case "threat_map":
          case "category_overlap":
            return <AdjacentMarketRadar key={i} payload={artifact.payload as any} />;
          default:
            return (
              <div key={i} className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-slate-200 mb-2">
                  {artifact.artifact_type.replace(/_/g, " ")}
                </h3>
                <pre className="text-xs text-slate-400 overflow-x-auto">
                  {JSON.stringify(artifact.payload, null, 2)}
                </pre>
              </div>
            );
        }
      })}
    </div>
  );
}
