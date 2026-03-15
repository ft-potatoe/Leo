"""
Specialist agents — re-exports for backward compatibility.
All real implementations live in their own modules.
"""

from agents.win_loss_agent import WinLossAgent
from agents.pricing_agent import PricingAgent
from agents.positioning_agent import PositioningAgent
from agents.competitive_agent import CompetitiveLandscapeAgent
from agents.market_trends_agent import MarketTrendsAgent
from agents.adjacent_threat_agent import AdjacentThreatAgent

__all__ = [
    "WinLossAgent",
    "PricingAgent",
    "PositioningAgent",
    "CompetitiveLandscapeAgent",
    "MarketTrendsAgent",
    "AdjacentThreatAgent",
]
