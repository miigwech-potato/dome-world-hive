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

- SwarmMetrics: Derived, read-only aggregates computed from BotState
  snapshots. Includes movement expressed in Flow-Core notation.
  Metrics are projections only — never control inputs.

- Observation: A formatted, human-readable record ready for The Landing
  Board. Observations are deliberately passive — they describe what was
  seen, never prescribe action.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json
import math
import uuid

from .notation import (
    SwarmReading, bot_glyph, read_swarm, DEFAULT_EPSILON,
)


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

    def speed(self) -> float:
        """Scalar speed in Flow-Core units."""
        vx, vy, vz = self.velocity
        return math.sqrt(vx * vx + vy * vy + vz * vz)

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
class SwarmMetrics:
    """
    Derived swarm-level aggregates computed from a list of BotState snapshots.

    Passive principle: SwarmMetrics are pure projections. They describe
    collective geometry and motion; they never issue commands or rewrite
    history. Movement is recorded in Flow-Core notation for continuity
    with the spatial rule system.
    """
    bot_count: int = 0
    centroid: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    dispersion: float = 0.0
    mean_speed: float = 0.0
    max_speed: float = 0.0
    phase_histogram: Dict[str, int] = field(default_factory=dict)
    influence_overlaps: int = 0
    isolated_bots: int = 0
    net_flow: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    flow_magnitude: float = 0.0
    kinetic_energy_proxy: float = 0.0
    reading: Optional[SwarmReading] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bot_count": self.bot_count,
            "centroid": list(self.centroid),
            "dispersion": round(self.dispersion, 4),
            "mean_speed": round(self.mean_speed, 4),
            "max_speed": round(self.max_speed, 4),
            "phase_histogram": self.phase_histogram,
            "influence_overlaps": self.influence_overlaps,
            "isolated_bots": self.isolated_bots,
            "flow_core": {
                "net_flow": [round(v, 4) for v in self.net_flow],
                "flow_magnitude": round(self.flow_magnitude, 4),
                "kinetic_energy_proxy": round(self.kinetic_energy_proxy, 4),
                "definitions": "net_flow = mean velocity; flow_magnitude = size of net_flow; K = mean(speed^2)",
                "glyphs": self.reading.to_dict() if self.reading else None,
            },
        }

    def to_markdown(self) -> str:
        """Render metrics as a compact Markdown block for The Landing Board."""
        cx, cy, cz = self.centroid
        fx, fy, fz = self.net_flow
        phase_parts = ", ".join(f"{k}: {v}" for k, v in sorted(self.phase_histogram.items()))
        lines = [
            "#### Swarm Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Bot count | {self.bot_count} |",
            f"| Centroid | ({cx:.2f}, {cy:.2f}, {cz:.2f}) |",
            f"| Dispersion (RMS) | {self.dispersion:.3f} |",
            f"| Mean speed | {self.mean_speed:.3f} |",
            f"| Max speed | {self.max_speed:.3f} |",
            f"| Influence overlaps | {self.influence_overlaps} |",
            f"| Isolated bots | {self.isolated_bots} |",
            f"| Phase histogram | {phase_parts or '-'} |",
            "",
            "##### Flow-Core Movement",
            "",
            "| Symbol | Meaning | Value |",
            "|--------|---------|-------|",
            f"| net_flow | mean velocity vector | ({fx:.3f}, {fy:.3f}, {fz:.3f}) |",
            f"| flow_magnitude | size of net_flow | {self.flow_magnitude:.3f} |",
            f"| K | kinetic_energy_proxy mean(speed^2) | {self.kinetic_energy_proxy:.3f} |",
        ]
        if self.reading:
            r = self.reading
            lines.extend([
                "",
                f"**Reading**: {r.notation or '(level movement only)'}  ",
                f"上 rising: {r.rising}, 下 descending: {r.descending}, "
                f"𝄐 resting: {r.resting}, level: {r.level}",
            ])
            if r.open_question:
                lines.extend(["", f"**？** {r.open_question}"])
        return "\n".join(lines)

    @classmethod
    def from_bot_states(cls, bot_states: List[BotState],
                        epsilon: float = DEFAULT_EPSILON) -> "SwarmMetrics":
        """Compute SwarmMetrics from BotState snapshots. Pure function."""
        n = len(bot_states)
        if n == 0:
            return cls()

        cx = sum(b.position[0] for b in bot_states) / n
        cy = sum(b.position[1] for b in bot_states) / n
        cz = sum(b.position[2] for b in bot_states) / n
        centroid = (cx, cy, cz)

        sum_sq = 0.0
        for b in bot_states:
            dx = b.position[0] - cx
            dy = b.position[1] - cy
            dz = b.position[2] - cz
            sum_sq += dx * dx + dy * dy + dz * dz
        dispersion = math.sqrt(sum_sq / n)

        speeds = [b.speed() for b in bot_states]
        mean_speed = sum(speeds) / n
        max_speed = max(speeds)

        phase_histogram: Dict[str, int] = {}
        for b in bot_states:
            key = b.phase.value
            phase_histogram[key] = phase_histogram.get(key, 0) + 1

        overlaps = 0
        for i, a in enumerate(bot_states):
            for j in range(i + 1, n):
                b = bot_states[j]
                dx = a.position[0] - b.position[0]
                dy = a.position[1] - b.position[1]
                dz = a.position[2] - b.position[2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist <= (a.influence_radius + b.influence_radius):
                    overlaps += 1

        isolated = 0
        for i, a in enumerate(bot_states):
            connected = False
            for j, b in enumerate(bot_states):
                if i == j:
                    continue
                dx = a.position[0] - b.position[0]
                dy = a.position[1] - b.position[1]
                dz = a.position[2] - b.position[2]
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist <= (a.influence_radius + b.influence_radius):
                    connected = True
                    break
            if not connected:
                isolated += 1

        nfx = sum(b.velocity[0] for b in bot_states) / n
        nfy = sum(b.velocity[1] for b in bot_states) / n
        nfz = sum(b.velocity[2] for b in bot_states) / n
        net_flow = (nfx, nfy, nfz)
        flow_magnitude = math.sqrt(nfx * nfx + nfy * nfy + nfz * nfz)
        kinetic_energy_proxy = sum(s * s for s in speeds) / n

        return cls(
            bot_count=n,
            centroid=centroid,
            dispersion=dispersion,
            mean_speed=mean_speed,
            max_speed=max_speed,
            phase_histogram=phase_histogram,
            influence_overlaps=overlaps,
            isolated_bots=isolated,
            net_flow=net_flow,
            flow_magnitude=flow_magnitude,
            kinetic_energy_proxy=kinetic_energy_proxy,
            reading=read_swarm([b.velocity for b in bot_states], epsilon),
        )


@dataclass
class SpatialLog:
    """
    Structured log entry capturing spatial Flow-Core events.

    SwarmMetrics are computed automatically from bot_states at construction.
    """
    event_type: str
    bot_states: List[BotState]
    spatial_context: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    metrics: Optional[SwarmMetrics] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if self.metrics is None and self.bot_states:
            self.metrics = SwarmMetrics.from_bot_states(self.bot_states)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "event_type": self.event_type,
            "bot_states": [b.to_dict() for b in self.bot_states],
            "spatial_context": self.spatial_context,
            "notes": self.notes,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpatialLog":
        data = data.copy()
        data["bot_states"] = [BotState.from_dict(b) for b in data["bot_states"]]
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        # Metrics are derived from bot_states, so they are recomputed on load
        # rather than trusted from the rounded values stored in the file.
        data.pop("metrics", None)
        return cls(**data)

    def to_markdown(self) -> str:
        lines = [
            f"### Spatial Log `{self.log_id[:8]}`",
            f"**Event**: `{self.event_type}`  ",
            f"**Recorded**: {self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "#### Bot Swarm Snapshot",
            "",
            "| Bot ID | Phase | Position (x,y,z) | Velocity | Radius | Flow |",
            "|--------|-------|------------------|----------|--------|------|",
        ]
        for bot in self.bot_states:
            pos = f"({bot.position[0]:.2f}, {bot.position[1]:.2f}, {bot.position[2]:.2f})"
            vel = f"({bot.velocity[0]:.2f}, {bot.velocity[1]:.2f}, {bot.velocity[2]:.2f})"
            lines.append(
                f"| `{bot.bot_id[:12]}` | {bot.phase.value} | {pos} | {vel} | {bot.influence_radius:.2f} | {bot_glyph(bot.velocity)} |"
            )

        if self.metrics:
            lines.append("")
            lines.append(self.metrics.to_markdown())

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
    """A ready-to-post Landing Board entry."""
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
