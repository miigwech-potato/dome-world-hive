"""
Dome-World: Autonomous Bot-Swarm Ecosystem Core

This package provides local utilities for bot-swarm telemetry,
spatial Flow-Core rule logging, and GitHub-integrated observation
posting to "The Landing Board".

Architectural Principles (Passive Observation Layer):
- Bot-swarm states are treated as immutable event streams.
- Spatial data follows Flow-Core rules: locality, continuity, and
  non-interference (passive monitoring only).
- The Landing Board acts as a permanent, append-only public ledger
  of observations — never mutating prior swarm history.
"""

__version__ = "0.1.0"
__author__ = "Dome-World Architects"

from .models import BotState, SpatialLog, Observation, SwarmMetrics, SwarmPhase
from .notation import SwarmReading, read_swarm, bot_glyph
from .telemetry import TelemetryStore
from .github_client import GitHubLandingBoard
from .cli import main

__all__ = [
    "BotState",
    "SpatialLog",
    "Observation",
    "SwarmMetrics",
    "SwarmPhase",
    "SwarmReading",
    "read_swarm",
    "bot_glyph",
    "TelemetryStore",
    "GitHubLandingBoard",
    "main",
]
