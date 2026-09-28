"""
Flow-Core notation for swarm movement.

This module reads BotState snapshots and writes what it sees in Flow-Core
glyphs. It only uses the marks whose meaning has been set by the author of
the notation:

    上      rise (upward flow, +z)
    下      descent (downward flow, -z)
    出      release (the swarm spreading outward between two readings)
    𝄐      rest (no movement)
    米      pattern-flow; 米(上//下) is usable flow produced by the pair
    //      two opposites that belong to the same loop and happen together
    -       sequence, in the order the movement happened
    ·       coexistence, two states side by side
    ？      open question: that side of the pair has not been observed

How the notation predicts:
    A // pair commits the reader to both sides. If a swarm shows 上 and no
    下, the reading is 上//？下: descent is expected somewhere in the loop
    but was not observed in this snapshot. The ？ marks where to look next.
    If both sides are present and the vertical flow cancels out while energy
    is still moving, the reading is 米(上//下): a working loop, not stillness.

à and hõt//cōl are not used here. The swarm data carries no temperature,
and à has no settled gloss yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

RISE = "上"
DESCENT = "下"
RELEASE = "出"
REST = "𝄐"
PATTERN = "米"
PAIR = "//"
SEQ = "-"
COEXIST = " · "
QUERY = "？"

# Below this speed (Flow-Core units) a bot counts as at rest, and below this
# vertical speed a bot counts as moving level rather than up or down.
DEFAULT_EPSILON = 0.05

# The loop counts as balanced (米) when the net vertical flow is no more than
# this fraction of the average vertical flow, whichever way it goes.
BALANCE_TOLERANCE = 0.2

# 出 is written when RMS dispersion grows by more than this fraction.
RELEASE_THRESHOLD = 0.05


def bot_glyph(velocity: Sequence[float], epsilon: float = DEFAULT_EPSILON) -> str:
    """Glyph for a single bot: 上, 下, 𝄐, or '' for level movement."""
    vx, vy, vz = velocity
    speed = (vx * vx + vy * vy + vz * vz) ** 0.5
    if speed < epsilon:
        return REST
    if vz > epsilon:
        return RISE
    if vz < -epsilon:
        return DESCENT
    return ""


@dataclass
class SwarmReading:
    """One snapshot of the swarm, written in Flow-Core notation."""
    rising: int
    descending: int
    resting: int
    level: int
    net_vertical: float
    notation: str
    open_question: Optional[str]

    def to_dict(self) -> dict:
        return {
            "notation": self.notation,
            "rising": self.rising,
            "descending": self.descending,
            "resting": self.resting,
            "level": self.level,
            "net_vertical": round(self.net_vertical, 4),
            "open_question": self.open_question,
        }


def read_swarm(velocities: List[Sequence[float]],
               epsilon: float = DEFAULT_EPSILON) -> SwarmReading:
    """Write the swarm's vertical movement as a Flow-Core reading."""
    glyphs = [bot_glyph(v, epsilon) for v in velocities]
    rising = glyphs.count(RISE)
    descending = glyphs.count(DESCENT)
    resting = glyphs.count(REST)
    level = glyphs.count("")

    n = len(velocities)
    net_vertical = sum(v[2] for v in velocities) / n if n else 0.0
    moving_vz = [abs(v[2]) for v, g in zip(velocities, glyphs) if g in (RISE, DESCENT)]
    mean_vertical = sum(moving_vz) / len(moving_vz) if moving_vz else 0.0

    open_question: Optional[str] = None
    if n == 0 or resting == n:
        core = REST
    elif rising and descending:
        if abs(net_vertical) <= BALANCE_TOLERANCE * mean_vertical:
            core = f"{PATTERN}({RISE}{PAIR}{DESCENT})"
        else:
            core = f"{RISE}{PAIR}{DESCENT}"
    elif rising:
        core = f"{RISE}{PAIR}{QUERY}{DESCENT}"
        open_question = "Descent expected elsewhere in the loop; not observed in this snapshot."
    elif descending:
        core = f"{QUERY}{RISE}{PAIR}{DESCENT}"
        open_question = "Rise expected elsewhere in the loop; not observed in this snapshot."
    else:
        core = ""  # level movement only; no vertical glyph applies

    parts = [p for p in (core, REST if resting and core != REST else "") if p]
    notation = COEXIST.join(parts)

    return SwarmReading(
        rising=rising,
        descending=descending,
        resting=resting,
        level=level,
        net_vertical=net_vertical,
        notation=notation,
        open_question=open_question,
    )


def released(previous_dispersion: float, current_dispersion: float,
             threshold: float = RELEASE_THRESHOLD) -> bool:
    """True when the swarm spread outward (出) between two readings."""
    if previous_dispersion <= 0:
        return current_dispersion > 0
    return (current_dispersion - previous_dispersion) / previous_dispersion > threshold


def chain(readings: List[str]) -> str:
    """Join readings in order with '-', collapsing repeats of the same state."""
    out: List[str] = []
    for r in readings:
        if r and (not out or out[-1] != r):
            out.append(r)
    return SEQ.join(out)
