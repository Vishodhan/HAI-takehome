"""Tests for the parts that do not need the API.

Run with `python test_pipeline.py`. No key needed, no tokens spent.
"""

import random
import tempfile
from pathlib import Path

import story_categories as categories
from main import parse_story
from story_history import StoryHistory, StoryRecord


def test_category_keywords_are_unique():
    """A keyword in two categories would make a request ambiguous."""
    keys = [c.key for c in categories.CATEGORIES]
    assert len(keys) == len(set(keys)), "duplicate category key"

    owner = {}
    for category in categories.CATEGORIES:
        for keyword in category.keywords:
            assert keyword not in owner, (
                f"{keyword!r} is claimed by both {owner[keyword]} and {category.key}"
            )
            owner[keyword] = category.key


def test_a_named_category_beats_the_rotation():
    """If the child asks for cats, they get cats, even if last night was cats."""
    choice = categories.choose_category("a story about my two cats", ["animal_friends"])
    assert choice.category.key == "animal_friends"
    assert choice.from_request

    choice = categories.choose_category("something with dinosaurs please", [])
    assert choice.category.key == "long_ago_creatures"


def test_rotation_skips_the_last_three():
    recent = ["animal_friends", "tiny_worlds", "under_water"]
    drawn = {
        categories.choose_category("surprise me", recent, random.Random(seed)).category.key
        for seed in range(300)
    }
    assert not drawn & set(recent), f"picked a recent category: {drawn & set(recent)}"
    assert len(drawn) > 1, "not actually shuffling"


def test_a_vague_request_still_gets_a_category():
    choice = categories.choose_category("anything you like", [])
    assert not choice.from_request


def test_parser_handles_every_separator_the_model_writes():
    """The metadata block must never end up in the story a child hears."""
    meta = '{"given_elements": ["Alice"], "arc": "small quest"}'
    replies = {
        "exact": f"The Lost Bell\n\nPara one.\n\nPara two.\n\n---META---\n{meta}",
        "bare dashes": f"The Lost Bell\n\nPara one.\n\n---\n```json\n{meta}\n```",
        "spaced": f"The Lost Bell\n\nPara one.\n\n--- META ---\n{meta}",
        "fence only": f"The Lost Bell\n\nPara one.\n\n```json\n{meta}\n```",
        "bare json": f"The Lost Bell\n\nPara one.\n\n{meta}",
        "no metadata": "The Lost Bell\n\nPara one.\n\nPara two.",
        # A dashed scene break inside the story must not cut it short.
        "scene break": f"The Lost Bell\n\nOne.\n\n---\n\nTwo.\n\n---META---\n{meta}",
    }

    for name, reply in replies.items():
        story = parse_story(reply)
        assert story["title"] == "The Lost Bell", f"{name}: title not found"
        assert "{" not in story["story"], f"{name}: metadata leaked into the story"

    assert "Two." in parse_story(replies["scene break"])["story"]


def test_parser_strips_title_decoration():
    for decorated in ("**The Lost Bell**", "# The Lost Bell", "TITLE: The Lost Bell"):
        assert parse_story(f"{decorated}\n\nPara one.")["title"] == "The Lost Bell"


def test_parser_passes_a_refusal_through():
    assert "refusal" in parse_story('{"refusal": "Shall we try something cosy?"}')


def test_history_round_trip():
    with tempfile.TemporaryDirectory() as folder:
        history = StoryHistory(Path(folder) / "history.json")
        assert history.recent_categories(3) == [], "missing file should read as empty"

        for key in ["animal_friends", "tiny_worlds", "under_water", "night_garden"]:
            history.append(StoryRecord.create("a request", key, "A Title", "PASS"))

        assert history.recent_categories(3) == ["night_garden", "under_water", "tiny_worlds"]
        assert len(history.records()) == 4


def test_history_survives_a_broken_file():
    """Failing to read the log is no reason to refuse a child a story."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "history.json"
        path.write_text("{ not json", encoding="utf-8")
        assert StoryHistory(path).recent_categories(3) == []


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
