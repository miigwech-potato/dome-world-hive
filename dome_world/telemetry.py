"""
Dome-World Telemetry Store

Local, file-backed persistence for spatial logs and bot-swarm states.

Design notes (Passive Architecture):
- Storage is strictly append-only for SpatialLog entries. This mirrors
  the immutable nature of The Landing Board and prevents accidental
  rewriting of swarm history.
- BotState snapshots may be overwritten (they are projections, not
  historical records). Only the SpatialLog stream is treated as
  canonical timeline.
- All paths are relative to a configurable data directory so the module
  remains self-contained and testable offline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from .models import BotState, SpatialLog, Observation

logger = logging.getLogger(__name__)


class TelemetryStore:
    """
    Lightweight local store for Dome-World telemetry.

    Directory layout (created on first use):
        <data_dir>/
            logs/           # one JSON file per SpatialLog
            states/         # latest BotState per bot_id
            observations/   # rendered Observation Markdown + JSON
    """

    def __init__(self, data_dir: str | Path = "./dome_data"):
        self.data_dir = Path(data_dir)
        self.logs_dir = self.data_dir / "logs"
        self.states_dir = self.data_dir / "states"
        self.obs_dir = self.data_dir / "observations"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in (self.logs_dir, self.states_dir, self.obs_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # SpatialLog persistence (append-only)
    # ------------------------------------------------------------------

    def write_log(self, log: SpatialLog) -> Path:
        """
        Persist a SpatialLog as an immutable JSON file.

        Passive principle: once written, a log is never modified.
        Filenames include the log_id to guarantee uniqueness.
        """
        path = self.logs_dir / f"{log.log_id}.json"
        if path.exists():
            raise FileExistsError(
                f"Log {log.log_id} already exists — refusing to overwrite "
                "(append-only / passive observation invariant)."
            )
        with path.open("w", encoding="utf-8") as f:
            json.dump(log.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info("Wrote SpatialLog %s → %s", log.log_id[:8], path)
        return path

    def read_log(self, log_id: str) -> SpatialLog:
        """Load a previously recorded SpatialLog by ID."""
        path = self.logs_dir / f"{log_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"No SpatialLog found for id={log_id}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return SpatialLog.from_dict(data)

    def list_logs(self) -> List[str]:
        """Return all known log_ids (sorted by filename, which is NOT time order)."""
        return sorted(p.stem for p in self.logs_dir.glob("*.json"))

    def logs_in_order(self) -> List[SpatialLog]:
        """Return every SpatialLog sorted by when it was recorded."""
        logs = [self.read_log(log_id) for log_id in self.list_logs()]
        return sorted(logs, key=lambda log: log.created_at)

    # ------------------------------------------------------------------
    # BotState snapshots (latest-wins)
    # ------------------------------------------------------------------

    def write_state(self, state: BotState) -> Path:
        """
        Store the latest known state for a bot.

        Unlike SpatialLogs, states are allowed to be overwritten because
        they represent a current projection, not historical fact.
        """
        path = self.states_dir / f"{state.bot_id}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
        logger.debug("Updated BotState for %s", state.bot_id)
        return path

    def read_state(self, bot_id: str) -> Optional[BotState]:
        """Return the latest BotState or None if unknown."""
        path = self.states_dir / f"{bot_id}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return BotState.from_dict(data)

    def list_bots(self) -> List[str]:
        """Return all bot_ids that have a recorded state."""
        return sorted(p.stem for p in self.states_dir.glob("*.json"))

    # ------------------------------------------------------------------
    # Observation helpers
    # ------------------------------------------------------------------

    def write_observation(self, obs: Observation) -> Path:
        """
        Persist both Markdown and JSON forms of an Observation.
        Useful for offline review before posting to The Landing Board.
        """
        base = self.obs_dir / f"{obs.created_at.strftime('%Y%m%dT%H%M%S')}_{obs.source_log_id or 'manual'}"
        md_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")

        md_path.write_text(obs.body_markdown, encoding="utf-8")
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(obs.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info("Wrote Observation → %s", md_path)
        return md_path

    def create_observation_from_log(self, log: SpatialLog, title: Optional[str] = None) -> Observation:
        """
        Convenience: turn a SpatialLog into a ready-to-post Observation.
        """
        if title is None:
            title = f"[Dome-World] {log.event_type} — {log.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
        return Observation(
            title=title,
            body_markdown=log.to_markdown(),
            source_log_id=log.log_id,
        )
