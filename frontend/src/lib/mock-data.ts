import { OrchestratorResponse, AgentStatusInfo } from "@/types";

export const DEMO_AGENTS: AgentStatusInfo[] = [
  { name: "market_trends", displayName: "Market & Trend Sensing", status: "queued", elapsed: 0 },
  { name: "competitive_landscape", displayName: "Competitive Landscape", status: "queued", elapsed: 0 },
  { name: "win_loss", displayName: "Win / Loss Intelligence", status: "queued", elapsed: 0 },
  { name: "pricing", displayName: "Pricing & Packaging", status: "queued", elapsed: 0 },
  { name: "positioning", displayName: "Positioning & Messaging", status: "queued", elapsed: 0 },
  { name: "adjacent_threat", displayName: "Adjacent Market Collision", status: "queued", elapsed: 0 },
];

export const STARTER_CHIPS = [
  "Is Vector competitive in the AI SDR market?",
  "Is the digital workers category accelerating or consolidating?",
  "What should Vector build over the next 6 months?",
];

export const MOCK_RESPONSE: OrchestratorResponse = {
  session_id: "demo-001",
  query: "Is Vector competitive in the AI SDR market?",
  executive_summary:
    "Vector Agents holds a strong position in the emerging AI SDR market, with differentiated automation capabilities. However, the competitive landscape is intensifying rapidly with 3 well-funded competitors entering in the last 6 months. Key risks include pricing pressure from usage-based entrants and feature parity from established CRM platforms adding AI capabilities.",
  key_findings: [
    {
      statement: "The AI SDR market grew 340% YoY in 2025, reaching $2.1B in ARR across tracked vendors.",
      type: "fact",
      confidence: "high",
      rationale: "Corroborated by 5 independent sources including Gartner and CB Insights reports.",
    },
    {
      statement: "Vector's win rate has declined from 45% to 32% in enterprise deals over the past two quarters.",
      type: "fact",
      confidence: "medium",
      rationale: "Based on G2 review analysis and 3 Reddit discussions mentioning competitive displacement.",
    },
    {
      statement: "Competitor X raised $50M Series B in Feb 2026, suggesting aggressive enterprise expansion within 6 months.",
      type: "interpretation",
      confidence: "medium",
      rationale: "Funding pattern matches typical enterprise go-to-market timeline.",
    },
    {
      statement: "Vector should invest in native CRM integrations to defend against platform encroachment.",
      type: "recommendation",
      confidence: "high",
      rationale: "Integration gaps cited as #1 reason for deal losses in review analysis.",
    },
  ],
  facts: [
    {
      statement: "The AI SDR market grew 340% YoY in 2025, reaching $2.1B in ARR.",
      type: "fact",
      confidence: "high",
      rationale: "Gartner, CB Insights, and 3 industry reports.",
    },
    {
      statement: "Competitor X raised $50M Series B in Feb 2026.",
      type: "fact",
      confidence: "high",
      rationale: "TechCrunch, Crunchbase confirmed.",
    },
    {
      statement: "Vector Agents currently has 1,200+ G2 reviews with 4.3/5 average rating.",
      type: "fact",
      confidence: "high",
      rationale: "Direct G2 data.",
    },
    {
      statement: "3 new entrants raised >$20M each in the past 6 months.",
      type: "fact",
      confidence: "high",
      rationale: "Crunchbase funding data.",
    },
  ],
  interpretations: [
    {
      statement: "The market is transitioning from early-adopter to early-majority phase, suggesting feature completeness will matter more than novelty.",
      type: "interpretation",
      confidence: "medium",
      rationale: "Based on adoption curve analysis and market maturity signals.",
    },
    {
      statement: "Competitor X's Series B signals enterprise expansion within 6 months.",
      type: "interpretation",
      confidence: "medium",
      rationale: "Typical post-B enterprise GTM timeline.",
    },
  ],
  recommendations: [
    {
      statement: "Prioritize native CRM integrations (Salesforce, HubSpot) in Q2.",
      type: "recommendation",
      confidence: "high",
      rationale: "Integration gaps are the #1 cited loss reason.",
    },
    {
      statement: "Consider usage-based pricing tier to compete with emerging low-cost entrants.",
      type: "recommendation",
      confidence: "medium",
      rationale: "3 of 5 new entrants use usage-based models attracting SMB segment.",
    },
  ],
  confidence_overview: {
    overall: "medium",
    evidence_count: 47,
    source_diversity: "high",
    contradictions: 1,
    flags: ["Win/loss data limited to public reviews — direct customer interviews recommended"],
  },
  artifacts: [
    {
      artifact_type: "competitive_scorecard",
      payload: {
        competitors: [
          {
            name: "SalesAI Pro",
            positioning: "Enterprise-first AI SDR with deep Salesforce integration",
            strengths: ["Salesforce native", "SOC2 compliant", "Enterprise playbooks"],
            weaknesses: ["Expensive", "Slow onboarding", "Limited customization"],
            threat_level: "high",
            sources: ["g2.com/salesai-pro", "techcrunch.com/salesai-series-b"],
          },
          {
            name: "OutboundBot",
            positioning: "Usage-based AI outreach for SMBs",
            strengths: ["Low entry price", "Quick setup", "Good API"],
            weaknesses: ["Limited enterprise features", "No CRM integration", "Small team"],
            threat_level: "medium",
            sources: ["producthunt.com/outboundbot", "reddit.com/r/sales/outboundbot"],
          },
          {
            name: "ReplyEngine",
            positioning: "AI-powered multi-channel sales engagement",
            strengths: ["Multi-channel", "Good UX", "Strong content generation"],
            weaknesses: ["New to market", "Unproven at scale", "Limited analytics"],
            threat_level: "medium",
            sources: ["capterra.com/replyengine"],
          },
          {
            name: "HubSpot AI",
            positioning: "Integrated AI SDR within HubSpot CRM ecosystem",
            strengths: ["Massive distribution", "Free tier", "Ecosystem lock-in"],
            weaknesses: ["Generic AI", "Not specialized", "Lags on innovation"],
            threat_level: "high",
            sources: ["hubspot.com/ai", "g2.com/hubspot"],
          },
        ],
      },
    },
    {
      artifact_type: "trend_chart",
      payload: {
        title: "AI SDR Market Growth",
        data: [
          { month: "Jan 2025", value: 420, event: null },
          { month: "Apr 2025", value: 680, event: "SalesAI Pro Series A ($20M)" },
          { month: "Jul 2025", value: 1100, event: null },
          { month: "Oct 2025", value: 1500, event: "OutboundBot launch" },
          { month: "Jan 2026", value: 1850, event: "ReplyEngine Series A ($25M)" },
          { month: "Mar 2026", value: 2100, event: "SalesAI Pro Series B ($50M)" },
        ],
        yAxisLabel: "Market ARR ($M)",
        sourceCount: 12,
        confidence: "high",
      },
    },
    {
      artifact_type: "positioning_map",
      payload: {
        xAxis: { label: "SMB", labelEnd: "Enterprise" },
        yAxis: { label: "Automation", labelEnd: "Augmentation" },
        competitors: [
          { name: "Vector Agents", x: 0.6, y: 0.7, isTarget: true },
          { name: "SalesAI Pro", x: 0.85, y: 0.5, isTarget: false },
          { name: "OutboundBot", x: 0.2, y: 0.8, isTarget: false },
          { name: "ReplyEngine", x: 0.45, y: 0.6, isTarget: false },
          { name: "HubSpot AI", x: 0.7, y: 0.3, isTarget: false },
        ],
      },
    },
    {
      artifact_type: "strategic_brief",
      payload: {
        executive_summary:
          "Vector Agents is well-positioned but faces increasing pressure from both specialized AI SDR startups and CRM platform incumbents adding AI capabilities.",
        opportunities: [
          {
            claim: "Enterprise segment is underserved by pure-play AI SDR vendors",
            confidence: "high",
            source_count: 8,
            sources: ["gartner.com/ai-sdr-2026", "forrester.com/sales-automation"],
          },
          {
            claim: "Usage-based pricing could unlock SMB segment growth",
            confidence: "medium",
            source_count: 5,
            sources: ["openviewpartners.com/plg-benchmarks"],
          },
          {
            claim: "Multi-channel orchestration is an emerging differentiator",
            confidence: "medium",
            source_count: 4,
            sources: ["saleshacker.com/multichannel-2026"],
          },
        ],
        risks: [
          {
            claim: "HubSpot and Salesforce adding native AI SDR features threatens distribution advantage",
            confidence: "high",
            source_count: 6,
            sources: ["hubspot.com/ai-roadmap", "salesforce.com/einstein-sdr"],
          },
          {
            claim: "Price compression from VC-funded competitors operating at a loss",
            confidence: "medium",
            source_count: 4,
            sources: ["crunchbase.com/ai-sdr-funding"],
          },
          {
            claim: "Regulatory risk around AI-generated outreach (EU AI Act implications)",
            confidence: "low",
            source_count: 2,
            sources: ["euaiact.com/sales-automation"],
          },
        ],
        recommended_bets: [
          {
            claim: "Build native Salesforce + HubSpot integrations as top priority",
            confidence: "high",
            source_count: 11,
            sources: ["g2.com/vector-reviews", "reddit.com/r/sales"],
          },
          {
            claim: "Launch usage-based tier targeting 10-50 person sales teams",
            confidence: "medium",
            source_count: 6,
            sources: ["openviewpartners.com/usage-pricing"],
          },
          {
            claim: "Invest in compliance and SOC2 to differentiate in enterprise",
            confidence: "high",
            source_count: 7,
            sources: ["gartner.com/enterprise-ai-requirements"],
          },
        ],
      },
    },
    {
      artifact_type: "win_loss_analysis",
      payload: {
        wins: [
          {
            insight: "Superior AI personalization quality compared to template-based competitors",
            frequency: 23,
            sentiment: 0.85,
            sources: ["g2.com/vector-reviews", "capterra.com/vector"],
          },
          {
            insight: "Faster time-to-value with self-serve onboarding",
            frequency: 18,
            sentiment: 0.78,
            sources: ["producthunt.com/vector-agents"],
          },
          {
            insight: "Better multi-language support for international teams",
            frequency: 12,
            sentiment: 0.72,
            sources: ["g2.com/vector-reviews"],
          },
        ],
        losses: [
          {
            insight: "Missing native CRM integrations force manual data sync",
            frequency: 31,
            sentiment: -0.82,
            sources: ["g2.com/vector-reviews", "reddit.com/r/sales/vector-issues"],
          },
          {
            insight: "Pricing perceived as too high for SMB teams under 20 reps",
            frequency: 19,
            sentiment: -0.65,
            sources: ["capterra.com/vector", "trustradius.com/vector"],
          },
          {
            insight: "Limited reporting and analytics compared to SalesAI Pro",
            frequency: 14,
            sentiment: -0.58,
            sources: ["g2.com/vector-vs-salesai"],
          },
        ],
        buyer_summary:
          "Buyers consistently praise Vector's AI quality and ease of use, but cite integration gaps and pricing as primary barriers. Enterprise buyers specifically need deeper CRM connectivity, while SMB buyers need a lower entry price point. The most common switching trigger is when teams outgrow Vector's reporting capabilities.",
      },
    },
    {
      artifact_type: "pricing_intelligence",
      payload: {
        competitors: [
          {
            name: "Vector Agents",
            model: "per-seat",
            entry_price: "$99/seat/mo",
            enterprise_price: "$249/seat/mo",
            packaging: "3 tiers: Starter, Pro, Enterprise",
          },
          {
            name: "SalesAI Pro",
            model: "per-seat",
            entry_price: "$149/seat/mo",
            enterprise_price: "$399/seat/mo",
            packaging: "2 tiers: Business, Enterprise + custom",
          },
          {
            name: "OutboundBot",
            model: "usage-based",
            entry_price: "$0.02/email",
            enterprise_price: "$0.01/email (volume)",
            packaging: "Pay-as-you-go + monthly commitments",
          },
          {
            name: "ReplyEngine",
            model: "flat",
            entry_price: "$299/mo (5 seats)",
            enterprise_price: "$999/mo (25 seats)",
            packaging: "Team plans with seat bundles",
          },
          {
            name: "HubSpot AI",
            model: "per-seat",
            entry_price: "Free (basic)",
            enterprise_price: "$150/seat/mo",
            packaging: "Included in Sales Hub tiers",
          },
        ],
        willingness_to_pay: [
          { signal: "SMB teams willing to pay $50-80/seat/mo for core AI SDR features", confidence: "high" },
          { signal: "Enterprise buyers expect $200-400/seat/mo but demand SSO, audit logs, and CRM sync", confidence: "high" },
          { signal: "Usage-based pricing gaining preference among teams with variable outreach volume", confidence: "medium" },
        ],
        gaps: [
          "No competitor offers a hybrid per-seat + usage model — opportunity for Vector",
          "Free tier from HubSpot is compressing entry-level willingness to pay",
          "Annual contracts with 20%+ discount are standard — Vector's 10% discount is below market",
        ],
      },
    },
    {
      artifact_type: "adjacent_market_radar",
      payload: {
        rings: [
          {
            label: "Direct Competitors",
            nodes: [
              {
                name: "SalesAI Pro",
                description: "Enterprise AI SDR platform",
                relevance: "Direct feature competitor with stronger CRM integrations",
                threat_timeline: "Now",
              },
              {
                name: "OutboundBot",
                description: "Usage-based AI outreach",
                relevance: "Competing on price in SMB segment",
                threat_timeline: "Now",
              },
            ],
          },
          {
            label: "Adjacent Movers",
            nodes: [
              {
                name: "HubSpot AI",
                description: "CRM platform adding AI SDR",
                relevance: "Massive distribution, bundling AI features free",
                threat_timeline: "6-12 months",
              },
              {
                name: "Salesforce Einstein SDR",
                description: "CRM-native AI selling assistant",
                relevance: "Could make standalone AI SDR tools redundant for Salesforce shops",
                threat_timeline: "6-12 months",
              },
            ],
          },
          {
            label: "Emerging Threats",
            nodes: [
              {
                name: "OpenAI Operator",
                description: "General-purpose AI agent",
                relevance: "Could commoditize AI SDR as a generic agent workflow",
                threat_timeline: "12-24 months",
              },
              {
                name: "Anthropic Tool Use",
                description: "AI agent framework",
                relevance: "Enables DIY AI SDR builds, reducing need for specialized tools",
                threat_timeline: "12-18 months",
              },
            ],
          },
        ],
      },
    },
  ],
  follow_up_questions: [
    "What specific CRM integrations should Vector prioritize first?",
    "How does Vector's churn rate compare to competitors?",
    "What pricing model changes would maximize revenue?",
  ],
  agent_outputs: [
    {
      agent_name: "MarketTrendsAgent",
      status: "success",
      findings: [],
      evidence: [
        { source_type: "web_search", url: "gartner.com/ai-sdr-2026", title: "Gartner AI SDR Market Report 2026", snippet: "The AI SDR market reached $2.1B...", collected_at: "2026-03-15T10:00:00Z", entity: "AI SDR Market" },
        { source_type: "web_search", url: "cbinsights.com/ai-sales", title: "AI Sales Tech Funding Tracker", snippet: "340% YoY growth in AI SDR category...", collected_at: "2026-03-15T10:00:01Z", entity: "AI SDR Market" },
      ],
      artifacts: [],
      errors: [],
    },
    {
      agent_name: "CompetitiveLandscapeAgent",
      status: "success",
      findings: [],
      evidence: [
        { source_type: "web_search", url: "g2.com/ai-sdr-comparison", title: "G2 AI SDR Category", snippet: "Top rated AI SDR tools compared...", collected_at: "2026-03-15T10:00:02Z", entity: "Competitors" },
      ],
      artifacts: [],
      errors: [],
    },
    {
      agent_name: "WinLossAgent",
      status: "success",
      findings: [],
      evidence: [
        { source_type: "reddit", url: "reddit.com/r/sales/vector-review", title: "Vector Agents honest review", snippet: "Great AI but CRM integration...", collected_at: "2026-03-15T10:00:03Z", entity: "Vector Agents" },
      ],
      artifacts: [],
      errors: [],
    },
    {
      agent_name: "PricingAgent",
      status: "success",
      findings: [],
      evidence: [
        { source_type: "scraped_page", url: "vectoragents.ai/pricing", title: "Vector Agents Pricing", snippet: "Starting at $99/seat/mo...", collected_at: "2026-03-15T10:00:04Z", entity: "Vector Agents" },
      ],
      artifacts: [],
      errors: [],
    },
    {
      agent_name: "PositioningAgent",
      status: "success",
      findings: [],
      evidence: [
        { source_type: "scraped_page", url: "vectoragents.ai", title: "Vector Agents Homepage", snippet: "AI-powered sales development...", collected_at: "2026-03-15T10:00:05Z", entity: "Vector Agents" },
      ],
      artifacts: [],
      errors: [],
    },
    {
      agent_name: "AdjacentThreatAgent",
      status: "success",
      findings: [],
      evidence: [
        { source_type: "web_search", url: "techcrunch.com/ai-agents-2026", title: "The AI Agent Landscape", snippet: "General-purpose AI agents threatening...", collected_at: "2026-03-15T10:00:06Z", entity: "AI Agents" },
      ],
      artifacts: [],
      errors: [],
    },
  ],
  errors: [],
};
