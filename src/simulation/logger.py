"""GameLogger — JSONL writer with flat round_end schema.

Each call to log() appends exactly one JSON line to output_dir/game.jsonl.
The round_end schema is the canonical field contract: use "vp" not
"victory_points" — downstream analysis and slice verification grep for "vp".
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GameLogger:
    """Append-only JSONL logger for a single game run.

    Args:
        game_id:    Unique identifier for this game run (injected into every line).
        output_dir: Directory where game.jsonl will be written.
                    Created automatically if it does not exist.
    """

    def __init__(self, game_id: str, output_dir: Path) -> None:
        self.game_id = game_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.output_dir / "game.jsonl"
        # line_buffering=True ensures each log() call is immediately readable
        # on disk — critical for crash-resume and real-time jq inspection.
        self._file = open(self._path, "a", encoding="utf-8", buffering=1)  # noqa: WPS515

    # ------------------------------------------------------------------
    # Core write methods
    # ------------------------------------------------------------------

    def log(self, event: str, **fields: Any) -> None:
        """Append one JSON line: {ts, event, game_id, **fields}.

        Args:
            event:   Event name string (e.g. "round_start", "round_end").
            **fields: Arbitrary key/value pairs merged into the record.
        """
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "game_id": self.game_id,
            **fields,
        }
        self._file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def flush(self) -> None:
        """Flush Python buffer and fsync to disk.

        Call after every round to ensure crash-resume can read the last
        committed state without data loss.
        """
        self._file.flush()
        os.fsync(self._file.fileno())

    def close(self) -> None:
        """Flush, fsync, and close the underlying file handle."""
        self.flush()
        self._file.close()

    # ------------------------------------------------------------------
    # Domain helpers
    # ------------------------------------------------------------------

    def log_round_end(
        self,
        round_num: int,
        agents: list[dict[str, Any]],
    ) -> None:
        """Emit one round_end line per agent.

        Each line contains the flat fields required by the analysis layer:
          game_id, model_family, round, agent_id, vp

        The field name is "vp" — NOT "victory_points".  This is the
        canonical contract; grep targets and downstream code depend on it.

        Args:
            round_num: Current round number (1-indexed).
            agents:    List of agent state dicts, each must have:
                         - agent_id  (str)
                         - model_family (str)
                         - vp  (int)  — current victory-point total
        """
        for agent in agents:
            self.log(
                "round_end",
                model_family=agent["model_family"],
                round=round_num,
                agent_id=agent["agent_id"],
                vp=agent["vp"],
            )

    # ------------------------------------------------------------------
    # Context-manager support (optional but handy in scripts)
    # ------------------------------------------------------------------

    def __enter__(self) -> "GameLogger":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
