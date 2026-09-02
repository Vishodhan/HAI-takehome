# Architecture and Workflow

A bedtime story teller for ages 5 to 10. One agent writes the story, a second
agent reviews it, and a small amount of plain Python decides what world the story
is set in. The user gets the story plus the judge's report.

## Block diagram

```
                    ┌──────────────────────────────────┐
                    │  USER                            │
                    │  "a story about Alice and Bob"   │
                    └────────────────┬─────────────────┘
                                     │ request (treated as data, not instruction)
                                     ▼
┌────────────────────┐     ┌───────────────────────────────┐
│ story_history.json │────▶│  CATEGORY PICKER              │
│ last 3 categories  │     │  story_categories.py          │
└────────────────────┘     │  plain Python, no LLM         │
          ▲                │                               │
          │                │  request names one? use it    │
          │                │  else shuffle the 13, minus   │
          │                │       the last 3 used         │
          │                └───────────────┬───────────────┘
          │                                │ category
          │                                ▼
          │      ┌──────────────────────────────────────────────┐
          │      │  STORY GENERATOR        gpt-3.5-turbo  T=0.9 │
          │      │  main.py + 1-story-generator-prompt.md       │
          │      │  out: title + prose ---META--- {arc, ...}    │
          │      │       or {"refusal": "..."}                  │
          │      └───────────────────┬──────────────────────────┘
          │                          │ story
          │                          ▼
          │      ┌──────────────────────────────────────────────┐
          │      │  STORY JUDGE            gpt-4o-mini    T=0.0 │
          │      │  llm_judge.py + 2-story-judge-prompt.md      │
          │      │  safety gate (blocks) + 9 checks + 6 scores  │
          │      └───────────────────┬──────────────────────────┘
          │                          │
          │        ┌─────────────────┼──────────────────┐
          │        ▼                 ▼                  ▼
          │      BLOCK            REVISE               PASS
          │   (safety only)         │                   │
          │        │                │ fixes             │
          │        │                ▼                   │
          │        │        revise once, judge again    │
          │        │                └───────────────────┤
          │        ▼                                    │
          │   regenerate once, else refuse warmly       │
          │                                             ▼
          └──── append record ──── STORY + REPORT ──▶ USER
```

## Files

| File | Holds |
|---|---|
| [main.py](main.py) | Generation, revision, the loop, and the printed output |
| [llm_judge.py](llm_judge.py) | The judge and its verdict |
| [story_categories.py](story_categories.py) | The 13 categories and how one gets picked |
| [story_history.py](story_history.py) | Reading and appending the JSON log |
| [test_pipeline.py](test_pipeline.py) | 9 tests that need no API key |
| [1-story-generator-prompt.md](1-story-generator-prompt.md) | Generator persona and rules |
| [2-story-judge-prompt.md](2-story-judge-prompt.md) | Judge persona and rubric |

`main.py` and `llm_judge.py` each build their own OpenAI client. That is two
duplicated lines, and it buys a clean split: no shared module, no circular
import, and each agent's model and temperature sit next to the call that uses it.

## Workflow

1. **Pick a category.** Read the last three categories from `story_history.json`.
   If the request names one ("dinosaurs", "under the sea"), use it. Otherwise
   shuffle the rest and take one.
2. **Write.** The generator returns a title and prose, then a `---META---` block
   with the metadata the judge uses. An unsafe request returns a refusal instead.
3. **Judge.** The judge returns a verdict, nine pass/fail checks, six 1-to-5
   scores, and up to three fixes.
4. **Revise once.** If the verdict is not PASS, send the fixes back and re-judge.
   If the judge blocks on safety, throw the draft away and generate once more.
5. **Print and record.** Story, then report, then one line appended to history.

## Design decisions worth knowing

**The story comes back as prose, not inside JSON.** Asking gpt-3.5-turbo to put
the story in a JSON string field roughly halved its length — 231 words versus 438
for the same request — and it stopped using paragraphs. The metadata is small, so
it still arrives as JSON after a separator.

**The separator match is deliberately loose.** The model writes `---META---`, or
plain `---`, or just opens a fenced JSON block. Matching only the exact string
dumped the raw metadata into the story a child would hear. `parse_story` matches
the shape and takes the *last* match, so a dashed scene break mid-story does not
truncate it.

**BLOCK means unsafe, nothing else.** The judge would report safety passing and
still label the whole review BLOCK because some formatting check failed, which
threw away perfectly safe stories. `llm_judge.py` downgrades that to REVISE
unless safety actually failed.

**The category picker is not an agent.** Rotation is set over the last
three stories. 

**Length is a prompt instruction, not machinery.** The generator prompt asks for
300 to 500 words and the judge checks it by eye.

## Recommended agent design pattern

**Evaluator–Optimizer** (also called Reflection or Generator–Critic), with a
plain-code router in front.

In [Anthropic's taxonomy](https://www.anthropic.com/engineering/building-effective-agents)
of five workflow patterns — prompt chaining, routing, parallelization,
orchestrator–workers, evaluator–optimizer — this is the one that fits, for the
two reasons that post gives:

1. **Clear evaluation criteria already exist.** [bedtime-story.md](bedtime-story.md)
   is a rubric: length bands, cast limits, tension calibration, safety rules. The
   criteria predate the code.
2. **Iterative refinement measurably helps.** Articulated feedback improves the
   draft, which is exactly the signal this pattern needs.

Two details matter in how it is applied. The critic is a **separate agent** with
its own persona, model, and a colder temperature — a model grading its own work
in its own context is a weak reviewer, which is why the pattern is drawn as a
[reflect-refine loop between two roles](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html).
And the router is **not** an agent, because the routing rule is deterministic and
stateful; routing is an LLM job only when the decision needs reading comprehension.

### Why not the others

| Pattern | Why it loses here |
|---|---|
| Prompt chaining | No quality loop, and the critic is the whole point |
| Routing (LLM-based) | The rule is deterministic. An LLM adds latency, cost, and a chance of inventing a category |
| Parallelization / best-of-N | A genuine upgrade — the judge already scores comparably, so sample 3 and ship the best. Costs 3× per story, so it is future work |
| Orchestrator–workers | Its advantage is unpredictable subtasks. Here they are fixed: write, judge, revise |
| Autonomous ReAct agent | No tools and no open-ended environment. Autonomy buys nondeterminism for nothing |

Reflection loops plateau and can regress, so the loop revises once rather than
looping until it is happy.

## Models

`gpt-3.5-turbo` for the generator, unchanged, per the assignment brief. The judge
runs `gpt-4o-mini`: a critic wants better reading comprehension than the writer
needs, and the point of the pattern is that the reviewer is not the author.
Temperatures differ by role — 0.9 for inventing, 0.0 so the same story gets the
same verdict twice.

## Measured behaviour and limits

Across a 5-request batch on the current build, all five reached PASS on the first
draft with mean scores of 3.8 to 4.2, and categories rotated correctly across
runs. Notably the PASS rate *rose* when the rigid pass/fail gates were replaced
with this lighter check list: the stricter rubric had been provoking the judge
into manufacturing faults to look thorough.

- **Stories run short.** gpt-3.5-turbo writes roughly 260 to 440 words whatever
  it is asked for, which is 2 to 4 minutes read aloud against the 5 to 10 the
  research recommends. That ceiling belongs to the fixed model, not the design.
  The output window is not the cause: 400 words is about 13% of the model's
  4,096-token cap.
- **The judge is not audited.** It is trusted on its own word for everything
  except the BLOCK correction. Feeding it deliberately broken stories to confirm
  it catches them is the next thing worth building.
- **Scores cluster at 3.8 to 4.2**, so the rubric does not discriminate strongly
  at the top end.

## Running it

```bash
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env      # .env is gitignored
python main.py                            # tell a story
python test_pipeline.py                   # 9 tests, no API key needed
```

`story_history.json` holds the category rotation; delete it to reset.

Sources: [Building Effective AI Agents, Anthropic](https://www.anthropic.com/engineering/building-effective-agents) ·
[Evaluator reflect-refine loop patterns, AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/evaluator-reflect-refine-loop-patterns.html) ·
[Zero to One: Learning Agentic Patterns](https://www.philschmid.de/agentic-pattern)
