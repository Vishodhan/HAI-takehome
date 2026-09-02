"""Keeps a JSON log of stories told, so categories can rotate between runs."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

HISTORY_PATH = Path(__file__).with_name("story_history.json")


@dataclass(frozen=True)
class StoryRecord:
    """One told story, as it is stored."""

    timestamp: str
    request: str
    category: str
    title: str
    verdict: str

    @staticmethod
    def create(request: str, category: str, title: str, verdict: str) -> "StoryRecord":
        return StoryRecord(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            request=request,
            category=category,
            title=title,
            verdict=verdict,
        )


class StoryHistory:
    """The log of told stories, oldest first."""

    def __init__(self, path: Path = HISTORY_PATH):
        self.path = path

    def records(self) -> list[dict]:
        """Read every stored story. A missing or broken file reads as empty."""
        if not self.path.exists():
            return []
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return loaded if isinstance(loaded, list) else []

    def recent_categories(self, count: int) -> list[str]:
        """Categories of the last few stories, newest first."""
        recent = self.records()[-count:] if count > 0 else []
        return [r["category"] for r in reversed(recent) if "category" in r]

    def append(self, record: StoryRecord) -> None:
        """Add one story to the log."""
        entries = self.records()
        entries.append(asdict(record))
        self.path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
