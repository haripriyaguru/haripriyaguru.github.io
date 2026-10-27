Title: Structured Outputs: How to Make an LLM Return Clean JSON Every Time
Date: 2026-10-27
Category: Tutorial
Tags: GenAI, LLM, structured-outputs, JSON, Pydantic, FastAPI, Python
Slug: structured-outputs-how-to-make-llm-return-clean-json

## The Bug That Taught Me This

The first time I built something that fed LLM output into other code, it worked beautifully for about a day. Then one response came back as:

```
Sure! Here's the JSON you asked for:

{"category": "billing", "priority": 2}

Let me know if you need anything else!
```

My code called `json.loads()` on that, and the whole pipeline crashed. The model had done what I asked, technically. It just added friendly text around the JSON, which a human would love and a parser hates.

That's the core problem structured outputs solve: **making LLM responses reliable enough for programs to consume, not just people to read.**

## Why Free-Form Text Breaks Software

Chat-style models are trained to be conversational. When your code expects strict data, several things can go wrong:

- **Extra text around the JSON** ("Sure! Here you go...")
- **Markdown code fences** wrapped around the output
- **Invalid JSON:** trailing commas, single quotes, missing brackets
- **Wrong field names or types:** `"priority": "high"` when you expected a number
- **Missing fields,** or extra ones you never asked for
- **Truncated output** when the response hits a length limit mid-object

Any of these can crash a parser or, worse, silently put bad data into your system.

## The Reliability Ladder

There are several ways to get structured data from an LLM. They range from fragile to robust, and it helps to know the whole ladder.

### Level 1: Just Ask Nicely (Prompt-Only)

```
Return your answer as JSON with keys "category" and "priority". Return only JSON.
```

This works surprisingly often, especially with strong models, and it's fine for quick experiments. But it's a request, not a guarantee. At scale, you'll eventually see the failure modes above.

### Level 2: JSON Mode

Many providers offer a "JSON mode" that forces the model to produce syntactically valid JSON. For example, with OpenAI's API:

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Classify this ticket as JSON: 'I was charged twice'"}],
    response_format={"type": "json_object"},
)
```

This fixes broken syntax and stray text. But note the limit: it guarantees **valid JSON**, not **the JSON you wanted**. The keys, types, and structure can still be wrong.

### Level 3: Schema-Constrained Outputs

The strongest option is giving the provider a **JSON Schema** and having the system constrain the model's generation to match it. With OpenAI's structured outputs, it looks like this:

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Classify this ticket: 'I was charged twice'"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "ticket",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["billing", "technical", "other"]},
                    "priority": {"type": "integer"},
                    "summary": {"type": "string"},
                },
                "required": ["category", "priority", "summary"],
                "additionalProperties": False,
            },
        },
    },
)
```

Here, the output is guaranteed to follow the schema: right keys, right types, and `category` limited to your allowed values. The official SDK also offers helpers that accept a Pydantic model directly instead of hand-written JSON Schema. Method names and options evolve, so check your provider's current docs for the exact syntax.

### Level 4: Tool Calling as a Structured Output Trick

As covered in the earlier post on function calling, a tool's parameters are defined by a JSON Schema, and the model returns arguments matching it. You can use that deliberately: define a "tool" whose only purpose is to receive your structured data, and force the model to call it. With Claude's API, for instance, you define a tool with an `input_schema` and set `tool_choice` to require that specific tool. The tool's input is then your structured result, and you never actually execute anything.

Some providers also offer dedicated structured-output features, so check what your provider supports before choosing a workaround.

### Level 5: Local Models

If you run models locally, such as with Ollama (covered in an earlier post), structured output is often supported by passing a JSON Schema in the request's `format` field, which constrains generation in a similar way. Support depends on your tool and version, so confirm in its docs.

## The Safety Net: Validate Everything With Pydantic

Even with schema-constrained output, **always validate on your side.** It protects you if you switch providers, use a model without strict support, or hit an unexpected edge case. If you've read the FastAPI tutorials on this blog, you already know the tool for this: **Pydantic**.

```python
from typing import Literal
from pydantic import BaseModel, Field, ValidationError

class Ticket(BaseModel):
    category: Literal["billing", "technical", "other"]
    priority: int = Field(ge=1, le=5)
    summary: str
```

This one class does three jobs:

- Defines the **shape** you expect
- **Validates** incoming data (types, allowed values, ranges)
- Can generate the JSON Schema for you, using `Ticket.model_json_schema()`, so your schema and your validation never drift apart

## Add a Retry Loop With Error Feedback

When validation fails, a powerful trick is to send the error back to the model and ask it to fix its own output:

```python
import re

def strip_fences(text: str) -> str:
    """Remove markdown code fences if the model added them."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text

def extract_ticket(user_text: str, max_retries: int = 2) -> Ticket:
    base_prompt = (
        "Classify this support message. Return ONLY JSON with keys "
        '"category" (billing, technical, or other), "priority" (1-5), and "summary".\n\n'
        f"Message: {user_text}"
    )
    prompt = base_prompt

    for _ in range(max_retries + 1):
        raw = call_llm(prompt)  # your LLM call, returns a string
        try:
            return Ticket.model_validate_json(strip_fences(raw))
        except ValidationError as e:
            prompt = (
                f"{base_prompt}\n\nYour previous reply was invalid:\n{raw}\n"
                f"Validation errors:\n{e}\n\nReturn ONLY the corrected JSON."
            )

    raise ValueError("Model failed to produce valid output after retries")
```

This pattern has a few good qualities:

- **It works with any model**, including ones without native structured output support
- **The error message gives the model something concrete to fix,** which echoes the lesson from the earlier post on agents repeating the same mistake: specific feedback beats a blind retry
- **A retry limit prevents infinite loops** and runaway costs

## Using the Same Model in FastAPI

Because FastAPI is built on Pydantic, the same class can serve double duty: validate the LLM's output and define your API's response.

```python
from fastapi import FastAPI

app = FastAPI()

@app.post("/classify", response_model=Ticket)
async def classify(message: str):
    return extract_ticket(message)
```

Now your API docs at `/docs` show the exact response shape, and clients can rely on it. One definition, used end to end.

## Design Tips for Better Schemas

How you design the schema affects output quality as much as how you enforce it:

- **Keep schemas simple.** Deeply nested, sprawling structures raise the chance of errors and can hit provider limits.
- **Use enums for fixed choices.** `"billing" | "technical" | "other"` is far more reliable than free text.
- **Write field descriptions.** The model reads them, so "priority: 1 is lowest, 5 is most urgent" helps.
- **Allow "I don't know."** Make fields optional or add an `"unknown"` option. If the schema forces an answer, the model may invent one.
- **Consider a short reasoning field first.** For harder tasks, letting the model write a brief explanation before the final fields can improve accuracy.
- **Use low temperature** for extraction and classification, where you want consistency over creativity.
- **Set generous output limits** so long JSON doesn't get cut off halfway.

## Remember: Valid Is Not the Same as Correct

This is the most important caveat. Structured output guarantees the **shape** of the answer, not its **truth**. A perfectly valid JSON object can still contain a wrong category, a made-up date, or an invented name. This connects to the earlier posts on hallucinations: the model can fill every field confidently and still be wrong.

So structure solves a parsing problem, not an accuracy problem. For accuracy, you still need grounding in real data, sensible checks (is this date plausible? does this ID exist?), and an eval set to measure how often the contents are actually right.

## Quick Checklist

- Don't rely on "please return JSON" alone for anything important
- Use schema-constrained output when your provider supports it
- Define your schema with Pydantic, and validate every response anyway
- Strip code fences and handle parsing errors gracefully
- Retry with the error message, with a hard retry limit
- Prefer enums, simple structures, and clear field descriptions
- Allow unknown or null values instead of forcing guesses
- Test the contents with an eval set, since valid JSON can still be wrong

## Closing Thought

Getting clean JSON from an LLM is less about finding the perfect prompt and more about layering protections: ask clearly, constrain generation where you can, validate everything, and recover gracefully when something slips through. Once you do, the model stops being a chatty text generator and becomes a dependable component your other code can build on, which is exactly what you need before anything LLM-powered goes into production.