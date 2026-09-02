# Bedtime Story Teller

Original bedtime stories for ages 5 to 10, written by one agent and reviewed by
another before they reach a child. Submission for the Hippocratic AI assignment;
the original brief is preserved below.

## Run it

```bash
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env      # gitignored, never committed
python main.py                            # tell a story
python test_pipeline.py                   # 9 tests, no API key needed
```

## How it works

Plain Python picks the world the story is set in, and keeps a category from
repeating across three nights running — unless the request names one, which
always wins. The generator writes the story; the judge reviews it against a
safety gate, nine checks, and six 1-to-5 scores. If the judge asks for changes,
the story is revised once and re-judged. Only a safety failure throws a draft
away.

| File | Holds |
|---|---|
| `main.py` | Generation, revision, the loop, printed output |
| `llm_judge.py` | The judge and its verdict |
| `story_categories.py` | The 13 categories and how one gets picked |
| `story_history.py` | The JSON log that drives category rotation |
| `test_pipeline.py` | Tests that need no API key |
| `1-story-generator-prompt.md`, `2-story-judge-prompt.md` | The two agent personas |
| `bedtime-story.md` | The research the prompts are built from |

Storyteller: `gpt-3.5-turbo`, unchanged per the brief. Judge: `gpt-4o-mini`, on
the grounds that a critic wants better reading comprehension than the writer, and
the point of the pattern is that the reviewer is not the author.

**[ARCHITECTURE.md](ARCHITECTURE.md)** has the block diagram, the workflow, the
agent design pattern and why it fits, and the measured results and known limits.

---

# Hippocratic AI Coding Assignment
Welcome to the [Hippocratic AI](https://www.hippocraticai.com) coding assignment

## Instructions
The attached code is a simple python script skeleton. Your goal is to take any simple bedtime story request and use prompting to tell a story appropriate for ages 5 to 10.
- Incorporate a LLM judge to improve the quality of the story
- Provide a block diagram of the system you create that illustrates the flow of the prompts and the interaction between judge, storyteller, user, and any other components you add
- Do not change the openAI model that is being used. 
- Please use your own openAI key, but do not include it in your final submission.
- Otherwise, you may change any code you like or add any files

---

## Rules
- This assignment is open-ended
- You may use any resources you like with the following restrictions
   - They must be resources that would be available to you if you worked here (so no other humans, no closed AIs, no unlicensed code, etc.)
   - Allowed resources include but not limited to Stack overflow, random blogs, chatGPT et al
   - You have to be able to explain how the code works, even if chatGPT wrote it
- DO NOT PUSH THE API KEY TO GITHUB. OpenAI will automatically delete it

---

## What does "tell a story" mean?
It should be appropriate for ages 5-10. Other than that it's up to you. Here are some ideas to help get the brain-juices flowing!
- Use story arcs to tell better stories
- Allow the user to provide feedback or request changes
- Categorize the request and use a tailored generation strategy for each category

---

## How will I be evaluated
Good question. We want to know the following:
- The efficacy of the system you design to create a good story
- Are you comfortable using and writing a python script
- What kinds of prompting strategies and agent design strategies do you use
- Are the stories your tool creates good?
- Can you understand and deconstruct a problem
- Can you operate in an open-ended environment
- Can you surprise us

---

## Other FAQs
- How long should I spend on this? 
No more than 2-3 hours
- Can I change what the input is? 
Sure
- How long should the story be?
You decide