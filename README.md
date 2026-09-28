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
├── models.py            # BotState, SpatialLog, Observation, SwarmPhase
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
