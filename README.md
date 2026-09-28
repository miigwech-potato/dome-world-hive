# Dome-World Hive

Clean, modular Python package for **bot-swarm telemetry** and **GitHub Landing Board** integration.

## Architecture (Passive Observation Layer)

| Concept              | Role                                                                 |
|----------------------|----------------------------------------------------------------------|
| `BotState`           | Momentary, non-authoritative snapshot of a swarm participant         |
| `SpatialLog`         | Append-only Flow-Core spatial event (locality + continuity)          |
| `Observation`        | Human-readable Markdown ready for The Landing Board                  |
| `TelemetryStore`     | Local file-backed persistence (logs are immutable)                   |
| `GitHubLandingBoard` | Pure publisher — never feeds control signals back into the swarm     |

Bot-swarm states map to passive architectural principles:

- **Observation over prescription** — telemetry never issues commands.
- **Append-only history** — SpatialLogs cannot be rewritten.
- **Decoupled sink** — The Landing Board is an optional observation target; local operation continues even if GitHub is unreachable.

## Flow-Core Notation

Each log is read into Flow-Core glyphs (`dome_world/notation.py`).

| Mark | Meaning in this package |
|------|-------------------------|
| 上 | rise: a bot moving upward |
| 下 | descent: a bot moving downward |
| 𝄐 | rest: a bot not moving |
| 米(上//下) | pattern-flow: rise and descent both present and cancelling out, while energy is still moving |
| 出 | release: the swarm spread outward between two logs |
| `//` | two opposites in the same loop, happening together |
| `-` | sequence, in the order the movement happened |
| `·` | coexistence, two states side by side |
| ？ | open question: that side of the pair was not observed |

**Describing.** Every bot in the snapshot table gets a glyph, and the swarm gets one reading, such as `米(上//下) · 𝄐`.

**Predicting.** A `//` pair commits the reader to both sides. If the swarm shows only 上, the reading is `上//？下`: descent is expected somewhere in the loop and was not seen here, so the ？ says where to look next. `trace` joins all logs into one chain (for example `𝄐-上//？下-出-米(上//下)`) and projects where the centroid goes next if the current flow holds.

à and hõt//cōl are not used yet. The swarm data carries no temperature, and à has no settled gloss.

## Quick Start

```bash
# Install dependency
pip install -r requirements.txt

# End-to-end synthetic demo (no network)
python -m dome_world demo --dry-run --bots 5

# Record a log from synthetic bots
python -m dome_world log --event swarm-pulse --bots 3 --notes "Morning calibration"

# List what has been recorded
python -m dome_world list

# Read every log in time order as one Flow-Core chain
python -m dome_world trace

# Run the tests
python -m unittest discover -s tests

# Post an existing log (dry-run)
python -m dome_world post --log-id <uuid> --dry-run \
    --owner miigwech-potato --repo dome-world-hive --issue 1

# Real post (requires GITHUB_TOKEN)
export GITHUB_TOKEN=ghp_...
python -m dome_world post --log-id <uuid> \
    --owner miigwech-potato --repo dome-world-hive --issue 1
```

## Module Layout

```
dome_world/
├── __init__.py          # Public API exports
├── __main__.py          # python -m dome_world entry point
├── models.py            # BotState, SpatialLog, Observation, SwarmPhase, SwarmMetrics
├── notation.py          # Flow-Core glyph readings (上 下 出 𝄐 米 // - · ？)
├── telemetry.py         # TelemetryStore (local read/write)
├── github_client.py     # GitHubLandingBoard (requests-based)
└── cli.py               # argparse CLI + demo commands
```

## Programmatic Use

```python
from dome_world import TelemetryStore, BotState, SpatialLog, SwarmPhase
from dome_world import GitHubLandingBoard

store = TelemetryStore("./dome_data")

state = BotState(
    bot_id="alpha-01",
    phase=SwarmPhase.OBSERVING,
    position=(10.5, -3.2, 1.0),
)
store.write_state(state)

log = SpatialLog(
    event_type="sector-scan",
    bot_states=[state],
    notes="Passive sweep of alpha-sector",
)
store.write_log(log)

obs = store.create_observation_from_log(log)

board = GitHubLandingBoard(
    owner="miigwech-potato",
    repo="dome-world-hive",
    issue_number=1,
)
board.post_observation(obs, dry_run=True)  # or dry_run=False with token
```

## Design Notes

- **No hard dependencies on IDEs or MCP hosts** — pure CLI + importable library.
- **Token never stored** — supplied via `GITHUB_TOKEN` env var or constructor.
- **Dry-run everywhere** — safe local testing before any network call.
- **Heavily commented** — every mapping from bot-swarm state → passive principle is explained in the source.
