Title: Prompt Versioning: Treating Prompts Like Code
Date: 2026-10-31
Category: Tutorial
Tags: GenAI, LLM, prompt-engineering, versioning, Git, production, Python
Slug: prompt-versioning-treating-prompts-like-code

## The Day Nobody Knew Why It Got Worse

Here's a scenario that happens on almost every LLM project eventually. The app was giving good answers on Monday. By Thursday, users are complaining that responses feel off. Someone says, "I think I tweaked the prompt a bit last week." Someone else says, "I also changed it to fix a formatting issue." Nobody remembers the exact wording of the old version, so nobody can go back.

The code has a full history in Git. The prompt, which controls the app's behavior just as much, lives in a string somewhere that anyone has edited at any time. This post is about fixing that by treating prompts the way we already treat code.

## Why Prompts Deserve the Same Care as Code

A prompt isn't just text. It's **logic written in natural language**. Changing a single sentence can change how the app behaves for every user, which is exactly what a code change does. Yet prompts often get less discipline than a one-line bug fix.

Without versioning, you run into predictable problems:

- **No history.** You can't see what changed, when, or why.
- **No rollback.** When a change makes things worse, you can't quickly return to the last good version.
- **No reproducibility.** You can't explain why last week's output was different from today's.
- **Silent edits.** Someone "improves" the prompt live and nobody reviews it.
- **Unclear blame.** When quality drops, you can't tell whether the cause was the prompt, the model, or the retrieval step.

This ties directly to the earlier post on why prompts work in testing and fail in production. Part of the fix is knowing exactly which prompt was running when something went wrong.

## Step 1: Get Prompts Out of Your Code Strings

The first habit is simple: stop burying prompts inside Python strings scattered through your app. Move them into their own files.

```
prompts/
  active.json
  CHANGELOG.md
  support_answer/
    v1.txt
    v2.txt
    v3.txt
  summarize_ticket/
    v1.txt
```

Each prompt gets a name and numbered versions. A template file might look like this:

```
You are a customer support assistant for Acme.

Answer the question using ONLY the context below.
If the answer is not in the context, say you don't know.

Context:
$context

Question:
$question
```

Placeholders like `$context` and `$question` are filled in at runtime. Now prompts can be read, reviewed, and diffed as normal text files.

## Step 2: Load Them With a Small Helper

Here's a minimal loader that keeps the name and version together with the text:

```python
import json
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Optional

PROMPT_DIR = Path("prompts")

@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    template: str

    def render(self, **values) -> str:
        # substitute() raises an error if a placeholder is missing,
        # which is what you want: fail loudly, not silently
        return Template(self.template).substitute(**values)

def load_prompt(name: str, version: Optional[str] = None) -> Prompt:
    if version is None:
        active = json.loads((PROMPT_DIR / "active.json").read_text())
        version = active[name]
    template = (PROMPT_DIR / name / f"{version}.txt").read_text()
    return Prompt(name=name, version=version, template=template)
```

And `active.json` simply records which version is live:

```json
{
  "support_answer": "v3",
  "summarize_ticket": "v1"
}
```

Using it looks like this:

```python
prompt = load_prompt("support_answer")
text = prompt.render(context=retrieved_text, question=user_question)
reply = call_llm(text)
```

A practical gotcha: if your prompt contains literal curly braces (for example, a JSON example), Python's `.format()` will break on them. That's why this loader uses `string.Template` with `$placeholders`, which doesn't care about braces.

## Step 3: Never Edit a Published Version

This rule keeps the system trustworthy: **versions are immutable.** Once `v3.txt` is in use, you don't change it. If you want to tweak it, you create `v4.txt`.

Why this matters:

- Old logs that say "v3" always refer to the exact same text
- You can compare any two versions with a normal diff
- Rolling back is just pointing `active.json` back to the previous version

Git already gives you history on top of this, but immutable version files make the connection between a log entry and a prompt unambiguous, even months later.

## Step 4: Record Which Version Produced Each Output

A version number is only useful if you can trace outputs back to it. Include it in your logs:

```python
import logging

logger = logging.getLogger("llm")

reply = call_llm(text)
logger.info(
    "llm_call",
    extra={
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
        "model": MODEL_NAME,
        "temperature": 0.2,
    },
)
```

Notice that the log records the **model and settings** too. A prompt's behavior depends on the model reading it, so the real unit you want to track is the combination of prompt version, model, and sampling settings. If a provider updates a model, or you change temperature, that's effectively a change to the system, even if the prompt text stayed identical. This is also why pinning to a specific model version, when your provider allows it, is a good habit.

Later, when a user reports a bad answer, you can look up exactly what was running.

## Step 5: Test Before You Switch

Versioning pairs naturally with the eval set from the earlier post on evaluating LLM apps. The workflow becomes:

1. Create the new version file (`v4.txt`)
2. Run your eval set against `v3` and `v4`
3. Compare pass rates, and look at which individual cases changed
4. Check side effects too: output length, cost, latency
5. Only if it's genuinely better, update `active.json`

This turns prompt changes from guesses into evidence. It also protects you from the classic trap where a fix for one case quietly breaks three others.

## Step 6: Keep a Short Changelog

Diffs show *what* changed, but not *why*. A tiny changelog captures the reasoning, which is the part you'll forget:

```
## support_answer v3 (2027-04-20)
- Added: "If the answer is not in the context, say you don't know."
- Why: eval case refund-7 was inventing a refund policy
- Eval: 78% -> 86% pass rate, average output length unchanged

## support_answer v2 (2027-04-10)
- Shortened instructions to reduce token usage
- Eval: 77% -> 78%, cost down about 12%
```

Future you (and teammates) will be grateful, especially when deciding whether it's safe to undo an old change.

## Step 7: Roll Out Carefully and Roll Back Fast

Since `active.json` controls what's live, deployment and rollback become tiny operations:

- **Deploy:** change `"support_answer": "v3"` to `"v4"`
- **Roll back:** change it back to `"v3"`

For higher-stakes apps, you can go further:

- **Canary release:** send a small percentage of traffic to the new version first
- **A/B testing:** run two versions side by side and compare real-world results
- **Separate environments:** let dev and staging use newer versions than production

Watch real usage after any change. Your eval set can't cover everything, as the earlier posts on production failures made clear.

## Do You Need a Prompt Management Tool?

There are dedicated prompt-management platforms that offer version history, editing UIs, and A/B testing. They can be worthwhile when:

- Non-engineers (product managers, domain experts) edit prompts often
- You manage many prompts across many apps
- You want built-in experiments and analytics

But for a solo developer or small team, **Git plus a folder of text files is a perfectly good start.** It's free, familiar, reviewable, and portable. You can always adopt a dedicated tool later, and your prompts will already be organized.

## Common Mistakes

- **Prompts hardcoded across the codebase,** so nobody can find them all
- **Editing a live prompt in a dashboard** with no history or review
- **No link between outputs and prompt versions,** so debugging is guesswork
- **Changing prompt, model, and retrieval settings all at once,** so you can't tell what helped
- **Skipping evals** because the change "looked small"
- **Putting secrets or private data in prompt files** (API keys belong in environment variables, as covered in the earlier post on FastAPI secrets)
- **Treating a model upgrade as "no change,"** when it can shift behavior as much as a prompt edit

## Quick Checklist

- Store each prompt in its own versioned file, outside application code
- Use placeholders, and fail loudly when one is missing
- Never edit a published version; create a new one
- Log prompt name, version, model, and settings on every call
- Run your eval set before switching versions
- Keep a short changelog explaining why each change was made
- Make rollback a one-line change
- Start with Git; adopt a dedicated tool only when you outgrow it

## Closing Thought

A prompt is code that happens to be written in English, and it deserves the same habits we've relied on for years: version history, review, testing, and the ability to undo a bad change quickly. None of this is complicated. It's a folder, a few conventions, and the discipline to follow them. But it turns "I think I tweaked the prompt last week" into "version 3 shipped on the 20th, here's why, and here's how to roll it back."