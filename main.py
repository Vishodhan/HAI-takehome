import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

"""

def call_model(prompt: str, instructions: str, max_tokens=3000, temperature=0.1) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.responses.create(
        model="gpt-3.5-turbo",
        instructions=instructions,
        input=[{"role": "user", "content": prompt}],
        stream=False,
        max_output_tokens=max_tokens,
        temperature=temperature,
        
    )

    return resp.output_text  # type: ignore

example_requests = "A story about a girl named Alice and her best friend Bob, who happens to be a cat."


def main():

    user_input = input("What kind of story do you want to hear? ")
    #a cat and a dog playing with a young girl in a park full of butterflies and flowers
    with open("prompt.txt", "r") as file:
        promptxt = file.read()
    response = call_model(prompt=user_input,instructions=promptxt)
    print(response)


if __name__ == "__main__":
    main()
