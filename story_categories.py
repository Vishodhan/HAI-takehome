"""The list of story worlds, and the rule for picking one."""

import random
import re
from dataclasses import dataclass

# A category has to sit out this many stories before it can be used again.
NO_REPEAT_WINDOW = 3


@dataclass(frozen=True)
class StoryCategory:
    """One world a story can be set in."""

    key: str
    name: str
    description: str
    keywords: tuple[str, ...]


CATEGORIES: tuple[StoryCategory, ...] = (
    StoryCategory(
        "animal_friends",
        "Animal Friends",
        "Animals with small ordinary problems, told at their own scale. A child "
        "gives an animal sympathy instantly, so a big feeling can be carried by a "
        "hedgehog without ever becoming frightening.",
        ("animal", "cat", "kitten", "dog", "puppy", "rabbit", "bunny", "fox",
         "bear", "mouse", "hedgehog", "owl", "bird", "horse", "pet", "duck"),
    ),
    StoryCategory(
        "tiny_worlds",
        "Tiny Worlds",
        "Everything smaller than a cupped hand: a town under a floorboard, the gap "
        "behind the radiator. Scale is instant wonder, and a bottle cap becomes a "
        "bathtub.",
        ("tiny", "miniature", "thimble", "ant", "beetle", "bug", "insect",
         "snail", "crumb", "dollhouse"),
    ),
    StoryCategory(
        "friendly_magic",
        "Friendly Magic",
        "Small domestic magic with rules: a spell that only works on Tuesdays, a "
        "wand best at making tea. Magic with a rule beats magic without one, "
        "because the child can work out the answer first.",
        ("magic", "magical", "wizard", "witch", "fairy", "spell", "unicorn",
         "dragon", "enchanted", "wand", "potion"),
    ),
    StoryCategory(
        "workshop_and_making",
        "Workshop and Making",
        "Something gets built, mended, or baked. Competence is thrilling, and any "
        "child who has built anything knows the feeling of the last piece going in.",
        ("build", "building", "make", "making", "mend", "fix", "repair",
         "workshop", "invent", "inventor", "bake", "baking"),
    ),
    StoryCategory(
        "under_water",
        "Under Water",
        "Ponds, tide pools, and the slow deep, where creatures drift and sounds "
        "arrive muffled. Water is already the sensory register of falling asleep.",
        ("water", "underwater", "sea", "ocean", "fish", "whale", "dolphin",
         "octopus", "turtle", "crab", "river", "pond", "lake", "mermaid"),
    ),
    StoryCategory(
        "sky_and_weather",
        "Sky and Weather",
        "Clouds, wind, and rain as characters: a small cloud that cannot rain yet. "
        "Weather is the biggest thing a child can see from a window, and giving it "
        "feelings makes it companionable.",
        ("sky", "cloud", "rain", "rainy", "wind", "windy", "storm", "snow",
         "fog", "rainbow", "thunder", "weather", "kite"),
    ),
    StoryCategory(
        "stars_and_space",
        "Stars and Space",
        "Night sky, moons, and quiet enormous distances, with invented mechanics "
        "rather than false astronomy. Slow and huge and quiet is the point.",
        ("star", "space", "moon", "planet", "rocket", "astronaut", "galaxy",
         "comet", "alien", "telescope"),
    ),
    StoryCategory(
        "kitchen_and_table",
        "Kitchen and Table",
        "Food and where it comes from: a soup that needs one more thing, a jar "
        "nobody can open. Warm, loud, and full of small solvable problems.",
        ("kitchen", "cook", "cooking", "food", "soup", "bread", "cake", "pie",
         "market", "jam", "honey", "picnic", "tea"),
    ),
    StoryCategory(
        "words_and_wordplay",
        "Words and Wordplay",
        "Language as the material: a library that reshelves itself, a shop selling "
        "only names. Wordplay is the rare joke a five and a ten year old both get.",
        ("book", "library", "word", "letter", "name", "poem", "rhyme",
         "alphabet", "riddle", "joke", "reading"),
    ),
    StoryCategory(
        "small_journeys",
        "Small Journeys",
        "A short trip by modest transport: a rowing boat, the last bus, a footpath "
        "that takes longer than expected. A destination pulls the story forward "
        "while the tension stays low.",
        ("journey", "trip", "travel", "boat", "bus", "bicycle", "bike", "walk",
         "path", "map", "road", "ferry", "sail"),
    ),
    StoryCategory(
        "long_ago_creatures",
        "Long-Ago Creatures",
        "Enormous gentle animals from a long time ago, slow and curious rather "
        "than fearsome. Making the giant gentle keeps the size thrilling and takes "
        "the teeth out of it.",
        ("dinosaur", "dino", "mammoth", "fossil", "prehistoric", "triceratops",
         "stegosaurus", "giant"),
    ),
    StoryCategory(
        "night_garden",
        "The Night Garden",
        "The garden after dark, seen from a lit window or with a grown-up nearby: "
        "moths, snails, and the night shift at work. It answers what a child "
        "actually wonders at bedtime, and answers it warmly.",
        ("moth", "firefly", "glowworm", "moonlight", "dusk", "nocturnal",
         "garden", "hedge"),
    ),
)


@dataclass(frozen=True)
class CategoryChoice:
    """The category picked for a story, and whether the user asked for it."""

    category: StoryCategory
    from_request: bool


def match_requested_category(request: str) -> StoryCategory | None:
    """Find the category the request asks for, or None if it names none."""
    words = re.findall(r"[a-z]+", request.lower())
    # Also try a singular form, so "cats" matches the "cat" keyword.
    tokens = set(words) | {w[:-1] for w in words if w.endswith("s") and len(w) > 3}

    best, best_hits = None, 0
    for category in CATEGORIES:
        hits = len(tokens.intersection(category.keywords))
        if hits > best_hits:
            best, best_hits = category, hits
    return best


def choose_category(
    request: str, recent_keys: list[str], rng: random.Random | None = None
) -> CategoryChoice:
    """Pick a category, avoiding recent ones unless the user asked for one.

    A request that names a category always wins, even if it was used last night.
    Otherwise the categories the recent stories did not use are shuffled and one
    is taken.
    """
    requested = match_requested_category(request)
    if requested is not None:
        return CategoryChoice(requested, from_request=True)

    pool = [c for c in CATEGORIES if c.key not in recent_keys] or list(CATEGORIES)
    rng = rng or random.Random()
    return CategoryChoice(rng.choice(pool), from_request=False)
