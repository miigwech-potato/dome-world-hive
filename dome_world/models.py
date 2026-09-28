"""
Dome-World Domain Models

These data classes represent the core entities of the bot-swarm ecosystem.
They map directly onto passive architectural principles:

- BotState: Captures a momentary, non-authoritative snapshot of a swarm
  participant. States are observational only; the swarm itself remains
  the sole source of truth.

- SpatialLog: Encodes Flow-Core spatial rules (position, velocity vector,
  influence radius). Logs are append-only and never rewrite history,
  reflecting the principle of temporal immutability.

- Observation: A formatted, human-readable record ready for The Landing
  Board. Observations are deliberately passive — they describe what was
  seen, never prescribe action.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import uuid


class SwarmPhase(str, Enum):
    """
    High-level lifecycle phases of a bot-swarm participant.

    Mapping to passive architecture:
    - IDLE / OBSERVING: Pure passive monitoring; no side-effects.
    - COORDINATING: Internal consensus formation (still non-authoritative
      from the Landing Board's perspective).
    - ACTING: Transient execution window; telemetry is captured but
      never used to drive the Landing Board itself.
    - DISSOLVING: Graceful wind-down; final state is sealed.
    """
    IDLE = "idle"
    OBSERVING = "observing"
    COORDINATING = "coordinating"
    ACTING = "acting"
    DISSOLVING = "dissolving"


@dataclass
class BotState:
    """
    Immutable snapshot of a single bot within the swarm.

    Passive principle: A BotState is a *projection* of reality, not a
    command. Downstream systems (telemetry, Landing Board) may read it
    freely but must never treat it as an authoritative control signal.
    """
    bot_id: str
    phase: SwarmPhase
    position: tuple[float, float, float]  # (x, y, z) in Flow-Core space
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    influence_radius: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for structured storage / transmission."""
        data = asdict(self)
        data["phase"] = self.phase.value
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotState":
        """Rehydrate from structured storage."""
        data = data.copy()
        data["phase"] = SwarmPhase(data["phase"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["position"] = tuple(data["position"])
        data["velocity"] = tuple(data["velocity"])
        return cls(**data)


@dataclass
class SpatialLog:
    """
    Structured log entry capturing spatial Flow-Core events.

    Flow-Core rules embodied here:
    1. Locality   – every event is anchored to a concrete coordinate.
    2. Continuity – velocity & influence imply smooth temporal evolution.
    3. Non-interference – the log never mutates prior entries; it only
       appends. This mirrors the passive observer stance of the Landing Board.
    """
    event_type: str
    bot_states: List[BotState]
    spatial_context: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "event_type": self.event_type,
            "bot_states": [b.to_dict() for b in self.bot_states],
            "spatial_context": self.spatial_context,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpatialLog":
        data = data.copy()
        data["bot_states"] = [BotState.from_dict(b) for b in data["bot_states"]]
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def to_markdown(self) -> str:
        """
        Render a human-readable Markdown observation suitable for
        The Landing Board.

        The format deliberately emphasizes observation over prescription:
        timestamps, coordinates, and phase transitions are stated factually.
        """
        lines = [
            f"### Spatial Log `{self.log_id[:8]}`",
            f"**Event**: `{self.event_type}`  ",
            f"**Recorded**: {self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "#### Bot Swarm Snapshot",
            "",
            "| Bot ID | Phase | Position (x,y,z) | Velocity | Radius |",
            "|--------|-------|------------------|----------|--------|",
        ]
        for bot in self.bot_states:
            pos = f"({bot.position[0]:.2f}, {bot.position[1]:.2f}, {bot.position[2]:.2f})"
            vel = f"({bot.velocity[0]:.2f}, {bot.velocity[1]:.2f}, {bot.velocity[2]:.2f})"
            lines.append(
                f"| `{bot.bot_id[:12]}` | {bot.phase.value} | {pos} | {vel} | {bot.influence_radius:.2f} |"
            )
        if self.notes:
            lines.extend(["", "#### Notes", "", self.notes])
        if self.spatial_context:
            lines.extend(["", "#### Spatial Context", "", "```json"])
            lines.append(json.dumps(self.spatial_context, indent=2))
            lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("*Passive observation — no control signals emitted.*")
        return "\n".join(lines)


@dataclass
class Observation:
    """
    A ready-to-post Landing Board entry.

    Observations are the final, human-facing artifact of the telemetry
    pipeline. They inherit the passive stance of SpatialLog and add
    optional GitHub metadata (issue number, repository, etc.).
    """
    title: str
    body_markdown: str
    source_log_id: Optional[str] = None
    tags: List[str] = field(default_factory=lambda: ["dome-world", "bot-swarm", "observation"])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "body_markdown": self.body_markdown,
            "source_log_id": self.source_log_id,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }
