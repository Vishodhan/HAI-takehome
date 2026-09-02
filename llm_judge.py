"""The judge agent: reads a finished story and decides whether it can be told."""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from story_categories import CategoryChoice

load_dotenv(override=True)

JUDGE_MODEL = "gpt-4o-mini"
JUDGE_PROMPT = Path(__file__).with_name("2-story-judge-prompt.md")

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@dataclass
class Verdict:
    """What the judge decided about one story."""

    verdict: str
    safety: str = "pass"
    checks: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    fixes: list = field(default_factory=list)
    note: str | None = None

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    @property
    def blocked(self) -> bool:
        return self.verdict == "BLOCK"

    @property
    def mean_score(self) -> float:
        values = [v for v in self.scores.values() if isinstance(v, (int, float))]
        return sum(values) / len(values) if values else 0.0


def _parse_json(text: str) -> dict:
    """Pull the JSON object out of the judge's reply, fenced or not."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    body = fenced.group(1) if fenced else text
    start, end = body.find("{"), body.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"No JSON in judge reply: {text[:200]!r}")
    return json.loads(body[start : end + 1])


def judge_story(
    story: dict, choice: CategoryChoice, recent_categories: list[str]
) -> Verdict:
    """Send a story to the judge and return its verdict."""
    payload = {
        "story": story,
        "assigned_category": {
            "name": choice.category.name,
            "description": choice.category.description,
        },
        "category_locked_by_user": choice.from_request,
        "recent_categories": recent_categories,
    }

    response = _client.responses.create(
        model=JUDGE_MODEL,
        instructions=JUDGE_PROMPT.read_text(encoding="utf-8"),
        input=[{"role": "user", "content": json.dumps(payload)}],
        stream=False,
        max_output_tokens=1500,
        temperature=0.0,
    )
    data = _parse_json(response.output_text)

    verdict = str(data.get("verdict", "REVISE")).upper()
    safety = str(data.get("safety", "pass")).lower()

    # The judge sometimes says BLOCK for a formatting problem. Only a safety
    # failure should throw a story away.
    if verdict == "BLOCK" and safety != "fail":
        verdict = "REVISE"

    return Verdict(
        verdict=verdict,
        safety=safety,
        checks=data.get("checks") or {},
        scores=data.get("scores") or {},
        fixes=data.get("fixes") or [],
        note=data.get("caregiver_note"),
    )
