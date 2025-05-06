import os, json, pathlib
from braintrust import Eval, load_prompt, wrap_openai
from autoevals import Factuality
from openai import OpenAI

# ---------- 1. Braintrust-wrapped OpenAI client ------------------------------
client = wrap_openai(
    OpenAI(
        base_url="https://api.braintrust.dev/v1/proxy",
        api_key=os.environ["BRAINTRUST_API_KEY"],
    )
)

# ---------- 2. Fetch the two system prompts you created ----------------------
prompt1 = load_prompt("SOAP-gen-demo", "system1-1463")  # ← matches your slug
prompt2 = load_prompt("SOAP-gen-demo", "system2-r376")

# ---------- 3. Helper: turn ANY prompt into a task function ------------------
def make_task(prompt):
    """
    Returns a callable(example_dict) -> str so Eval can run it row-by-row.
    Works because `prompt.build(...)` produces the exact kwargs that
    `client.chat.completions.create` expects.
    """
    def task(transcript: str):
        """Run the prompt on the dataset transcript and return the model output."""
        messages_kwargs = prompt.build(input=transcript)
        response = client.chat.completions.create(**messages_kwargs)
        return response.choices[0].message.content
    return task

# ---------- 4. Load the JSONL dataset correctly ------------------------------
def load_dataset(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

dataset_path = pathlib.Path("../data/soap_dataset_complete.jsonl")

# ---------- 5. First experiment (prompt1) ------------------------------------
Eval(
    "SOAP-gen-demo",                        # project
    data=lambda: load_dataset(dataset_path),
    task=make_task(prompt1),                # pass a callable, not the result
    scores=[Factuality()],
    experiment_name="system1-baseline",
)

# ---------- 6. Second experiment (prompt2) -----------------------------------
Eval(
    "SOAP-gen-demo",
    data=lambda: load_dataset(dataset_path),
    task=make_task(prompt2),
    scores=[Factuality()],
    experiment_name="system2-baseline",
)