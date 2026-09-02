"""Bedtime story teller: writes a story, has a judge review it, prints both.

Run it, type what you want a story about, and it prints the story with the
judge's report. See ARCHITECTURE.md for how the pieces fit together.

Before submitting the assignment, describe here in a few sentences what you
would have built next if you spent 2 more hours on this project:

    Best-of-N sampling. The judge already scores stories on a comparable scale,
    so writing three and shipping the best would help more than another revision
    round: revision can only repair a draft, sampling can replace it. I would
    also add a handful of fixed requests (vague, specific, unsafe, and one
    carrying a prompt injection) with expected verdicts, so prompt edits could
    be measured instead of eyeballed. Third, the judge is trusted on its own
    word; I would feed it deliberately broken stories to check it catches them.
"""

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from llm_judge import Verdict, judge_story
from story_categories import NO_REPEAT_WINDOW, CategoryChoice, choose_category
from story_history import StoryHistory, StoryRecord

load_dotenv(override=True)

STORY_MODEL = "gpt-3.5-turbo"
STORY_PROMPT = Path(__file__).with_name("1-story-generator-prompt.md")
LENGTH = "300 to 500 words"
META = "---META---"

# Shorter than this means the model returned nothing usable, not a short story.
MIN_STORY_WORDS = 100

BLOCKED = ("I could not find a way to tell that one tonight. "
           "Please try again")
TRY_AGAIN = "Story couldn't be generated. Please try again."

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# How the model marks the end of the story. It writes "---META---", or plain
# "---", or a ```json fence, or just the JSON on its own line. Tried in order,
# most specific first, taking the last match so a mid-story scene break made of
# dashes does not cut the story short.
_SEPARATORS = (
    re.compile(r"^[ \t]*-*[ \t]*META[ \t]*-*[ \t]*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^[ \t]*-{3,}[ \t]*$", re.MULTILINE),
    re.compile(r"^[ \t]*```[ \t]*json", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^[ \t]*\{", re.MULTILINE),
)


def parse_story(text: str) -> dict:
    """Split the model's reply into the title, the story, and its metadata."""
    text = text.strip()
    if text.startswith("{") or text.startswith("```json"):
        try:
            return json.loads(re.sub(r"```(?:json)?", "", text))  # a refusal
        except json.JSONDecodeError:
            return {}  # empty or cut-off reply, so there is no story to read

    prose, meta = text, ""
    for pattern in _SEPARATORS:
        if matches := list(pattern.finditer(text)):
            cut = matches[-1].start()
            prose, meta = text[:cut].strip(), text[cut:]
            break

    lines = prose.split("\n")
    title = lines[0].strip().removeprefix("TITLE:").strip(" #*_\"")
    body = "\n".join(lines[1:]).strip()
    if len(title) > 80:  # no title line, so that was the opening sentence
        title, body = "Tonight's Story", prose

    story = {"title": title, "story": body}
    start, end = meta.find("{"), meta.rfind("}")
    if start != -1 and end > start:
        try:
            extra = json.loads(meta[start : end + 1])
        except json.JSONDecodeError:
            extra = {}  # metadata is a bonus, not worth losing a good story over
        story.update({k: v for k, v in extra.items() if k not in story})
    return story


def ask_generator(payload: dict, reminder: str) -> dict:
    """Send a request to the generator and return the story it wrote."""
    response = _client.responses.create(
        model=STORY_MODEL,
        instructions=STORY_PROMPT.read_text(encoding="utf-8"),
        input=[{"role": "user", "content": f"{json.dumps(payload)}\n\n{reminder}"}],
        stream=False,
        max_output_tokens=3000,
        temperature=0.9,
    )
    return parse_story(response.output_text)


def generate_story(request: str, choice: CategoryChoice) -> dict:
    """Write a new story for this request."""
    category = {"name": choice.category.name, "description": choice.category.description}
    return ask_generator(
        {"mode": "write", "request": request, "assigned_category": category},
        f"Write the FULL story now: {LENGTH} in eight to eleven paragraphs. Title "
        f"on the first line, then the story, then the {META} block.",
    )


def revise_story(story: dict, fixes: list[dict]) -> dict:
    """Apply the judge's fixes and return the new version."""
    return ask_generator(
        {"mode": "revise", "story": story, "fixes": fixes},
        f"Apply the fixes and return the COMPLETE revised story, {LENGTH}, in the "
        f"same format: title, story, then the {META} block. Do not return anything "
        "shorter than the draft above.",
    )


def tell_story(request: str, choice: CategoryChoice, recent: list[str]):
    """Write a story, judge it, and revise it once if the judge asks for changes.

    Returns the story and its verdict. If nothing safe could be written, the
    verdict is None and the story holds a refusal to show instead.
    """
    for attempt in (1, 2):
        story = generate_story(request, choice)
        if "refusal" in story:
            return story, None
        if len(story.get("story", "").split()) < MIN_STORY_WORDS:
            log("the generator came back empty")
            return {"refusal": TRY_AGAIN}, None

        verdict = judge_story(story, choice, recent)
        log(f"draft {attempt}: {verdict.verdict} (mean {verdict.mean_score:.1f})")

        if verdict.blocked:
            log("blocked on safety, starting over")
            continue

        if not verdict.passed and verdict.fixes:
            log(f"revising: {len(verdict.fixes)} fix(es)")
            revised = revise_story(story, verdict.fixes)
            second = judge_story(revised, choice, recent) if "refusal" not in revised else None
            if second and not second.blocked:
                log(f"after revision: {second.verdict}")
                story, verdict = revised, second

        return story, verdict

    return {"refusal": BLOCKED}, None


def log(message: str) -> None:
    """Print progress to stderr, so it stays out of the story."""
    print(f"  ... {message}", file=sys.stderr)


def print_result(
    story: dict, verdict: Verdict, choice: CategoryChoice, recent: list[str]
) -> None:
    """Print the story, then what the judge thought of it."""
    title = story.get("title", "Untitled")
    print(f"\n{title}\n{'=' * len(title)}\n")
    print(story.get("story", ""))

    print("\n" + "-" * 60)
    print("JUDGE REPORT")
    print("-" * 60)
    print(f"Category : {choice.category.name}"
          f" ({'asked for' if choice.from_request else 'rotated in'})")
    print(f"Recent   : {', '.join(recent) if recent else 'none yet'}")
    print(f"Verdict  : {verdict.verdict}   mean score {verdict.mean_score:.1f}/5")

    if verdict.checks:
        print("Checks   : " + "  ".join(f"{k}={v}" for k, v in verdict.checks.items()))
    if verdict.scores:
        print("Scores   : " + "  ".join(f"{k} {v}" for k, v in verdict.scores.items()))
    for fix in [] if verdict.passed else verdict.fixes:
        print(f"  - {fix.get('issue', '')} ({fix.get('where', '')})")
    if verdict.note:
        print(f"Note     : {verdict.note}")


def main() -> None:
    # Windows consoles cannot print em-dashes without this.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    history = StoryHistory()
    recent = history.recent_categories(NO_REPEAT_WINDOW)

    request = input("What kind of story do you want to hear? ").strip() or "anything you like"
    choice = choose_category(request, recent)
    if not request or choice is None:
        print(f"\n{TRY_AGAIN}")
        return
    log(f"category: {choice.category.name}")

    try:
        story, verdict = tell_story(request, choice, recent)
    except OpenAIError as error:
        log(f"{type(error).__name__}: {error}")
        print(f"\n{TRY_AGAIN}")
        return

    if verdict is None:
        print(f"\n{story['refusal']}")
        return

    print_result(story, verdict, choice, recent)
    history.append(
        StoryRecord.create(request, choice.category.key, story["title"], verdict.verdict)
    )


if __name__ == "__main__":
    main()
